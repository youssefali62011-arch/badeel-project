"""Which diseases an ingredient treats, and with which diseases it must not be used.

Source: DrugCentral (CC BY-SA 4.0), table omop_relationship:
    struct_id, relationship_name ('indication' | 'contraindication' |
    'off-label use' ...), concept_name ('Peptic ulcer', ...), umls_cui
joined with the synonyms table to get every name of the ingredient.

Patients do not choose from DrugCentral's 4,000 medical terms. They tick
simple groups from data/patient_conditions.csv ("Liver disease"), and each
group covers several DrugCentral terms ("Disease of liver", "Hepatic
failure", ...).
"""
import collections
import csv
import json
import os
import shutil
import subprocess

from .. import db, security
from .normalize import DATA_DIR, moiety_key

RELATIONS = {"indication": "indication", "contraindication": "contraindication",
             "off-label use": "off_label"}


# ------------------------------------------------------- patient groups
def _load_groups():
    groups = {}
    path = os.path.join(DATA_DIR, "patient_conditions.csv")
    if os.path.exists(path):
        with open(path, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                groups[row["key"]] = {
                    "key": row["key"], "en": row["label_en"], "ar": row["label_ar"],
                    "concepts": [c.strip() for c in row["concepts"].split(";") if c.strip()],
                }
    return groups


GROUPS = _load_groups()
CONCEPT_TO_GROUP = {c: g for g in GROUPS.values() for c in g["concepts"]}


def user_groups(user):
    """Condition groups the patient saved (stored encrypted)."""
    if not user:
        return []
    try:
        keys = json.loads(security.decrypt(user["conditions_enc"]) or "[]")
    except (ValueError, KeyError, IndexError):
        return []
    return [k for k in keys if k in GROUPS]


def encrypt_groups(keys):
    keys = [k for k in dict.fromkeys(keys) if k in GROUPS]
    return security.encrypt(json.dumps(keys)) if keys else None


# ------------------------------------------------------------- loading
def parse_copy_blocks(text):
    """Rows of each table in pg_restore's data-only output (COPY ... FROM stdin)."""
    tables, current = collections.defaultdict(list), None
    for line in text.splitlines():
        if line.startswith("COPY "):
            current = line.split()[1].split(".")[-1]
            continue
        if current is None:
            continue
        if line == "\\.":
            current = None
            continue
        tables[current].append([None if v == "\\N" else
                                v.replace("\\t", "\t").replace("\\n", " ").replace("\\\\", "\\")
                                for v in line.split("\t")])
    return tables


def read_dump(path):
    """Extract the two tables from the DrugCentral .pgdump with pg_restore
    (no PostgreSQL server needed). A .sql/.txt file already extracted also works."""
    if not path.endswith(".pgdump"):
        with open(path, encoding="utf-8") as f:
            return parse_copy_blocks(f.read())
    exe = shutil.which("pg_restore")
    if not exe:
        raise RuntimeError("pg_restore was not found. Install the PostgreSQL client tools "
                           "(version 16 or newer) to read the DrugCentral dump.")
    out = subprocess.run([exe, "-a", "-t", "omop_relationship", "-t", "synonyms", "-f", "-", path],
                         check=True, capture_output=True)
    return parse_copy_blocks(out.stdout.decode("utf-8", errors="replace"))


def load_drugcentral(paths):
    """Store (ingredient, condition, relation) rows. Returns a small report."""
    tables = collections.defaultdict(list)
    for path in paths:
        for name, rows in read_dump(path).items():
            tables[name] += rows
    if not tables.get("omop_relationship") or not tables.get("synonyms"):
        raise ValueError("The DrugCentral tables omop_relationship and synonyms were not found.")

    names = collections.defaultdict(set)          # structure id -> moiety names
    for syn_id, struct_id, name, *_ in tables["synonyms"]:
        if name:
            names[struct_id].add(moiety_key(name))

    rows = set()
    for _id, struct_id, _concept_id, relation, concept, cui, *_ in tables["omop_relationship"]:
        rel = RELATIONS.get((relation or "").lower())
        if rel and concept:
            for moiety in names.get(struct_id, ()):
                rows.add((moiety, concept, rel, cui))

    db.execute("DELETE FROM ingredient_conditions WHERE source = 'DrugCentral'")
    db.get_db().executemany(
        "INSERT OR IGNORE INTO ingredient_conditions (ingredient, condition, relation, umls_cui, source) "
        "VALUES (?, ?, ?, ?, 'DrugCentral')", sorted(rows))
    db.set_setting("conditions_loaded", db.now())
    db.commit()
    return {"relations": len(rows),
            "ingredients": len({r[0] for r in rows}),
            "conditions": len({r[1] for r in rows})}


# -------------------------------------------------------------- lookup
def _moieties(drug):
    from .rxnorm import aliases
    return sorted(aliases({moiety_key(n) for n in drug["ingredient_key"].split("|") if n}))


def for_drug(drug):
    """What this product's ingredients treat and must not be used with."""
    own = _moieties(drug)
    if not own:
        return {"indication": [], "contraindication": []}
    marks = ",".join("?" * len(own))
    rows = db.query(f"SELECT DISTINCT condition, relation FROM ingredient_conditions "
                    f"WHERE ingredient IN ({marks}) AND relation IN ('indication', 'contraindication') "
                    f"ORDER BY condition", own)
    result = {"indication": [], "contraindication": []}
    for r in rows:
        result[r["relation"]].append(r["condition"])
    return result


def warnings_for(drug, group_keys):
    """Patient groups for which this product is listed as contraindicated."""
    contra = set(for_drug(drug)["contraindication"])
    found = []
    for key in group_keys:
        hits = [c for c in GROUPS[key]["concepts"] if c in contra]
        if hits:
            found.append({"group": GROUPS[key], "concepts": hits})
    return found


def products_treating(concepts, limit=200):
    """Ingredients listed as treating any of these conditions, and the products that contain them."""
    if not concepts:
        return [], []
    marks = ",".join("?" * len(concepts))
    ingredients = [r["ingredient"] for r in db.query(
        f"SELECT DISTINCT ingredient FROM ingredient_conditions "
        f"WHERE relation = 'indication' AND condition IN ({marks}) ORDER BY ingredient", concepts)]
    wanted = set(ingredients)
    ids = [r["id"] for r in db.query("SELECT id, name FROM ingredients") if moiety_key(r["name"]) in wanted]
    if not ids:
        return ingredients, []
    marks = ",".join("?" * len(ids))
    products = db.query(
        f"SELECT DISTINCT d.* FROM drugs d JOIN drug_ingredients di ON di.drug_id = d.id "
        f"WHERE di.ingredient_id IN ({marks}) ORDER BY d.trade_name LIMIT ?", (*ids, limit))
    return ingredients, products
