"""Drug-drug interactions (from DDInter).

DDInter files have one interaction per row:
    DDInterID_A, Drug_A, DDInterID_B, Drug_B, Level
where Level is Major, Moderate, Minor or Unknown. Names are matched to Badeel
ingredients with normalize.moiety_key, so "Diclofenac" in DDInter matches
"diclofenac sodium" and "diclofenac potassium" in the drug list.
"""
import csv
import io

from .. import db
from .normalize import moiety_key

SEVERITY_ORDER = {"major": 3, "moderate": 2, "minor": 1, "unknown": 0}

SEVERITY_LABELS = {
    "major": ("Major", "خطير"),
    "moderate": ("Moderate", "متوسط"),
    "minor": ("Minor", "بسيط"),
    "unknown": ("Severity not stated", "درجة الخطورة غير محددة"),
}


def _column(fields, *names):
    lower = {f.strip().lower(): f for f in fields or []}
    for n in names:
        if n in lower:
            return lower[n]
    return None


def parse_ddinter(text):
    """Yield (moiety_a, moiety_b, severity) for every usable row."""
    reader = csv.DictReader(io.StringIO(text))
    col_a = _column(reader.fieldnames, "drug_a", "drug a", "drug1", "drug_1")
    col_b = _column(reader.fieldnames, "drug_b", "drug b", "drug2", "drug_2")
    col_level = _column(reader.fieldnames, "level", "severity")
    if not (col_a and col_b and col_level):
        raise ValueError(f"Not a DDInter file: columns are {reader.fieldnames}")
    for row in reader:
        a, b = moiety_key(row[col_a]), moiety_key(row[col_b])
        level = (row[col_level] or "").strip().lower()
        if not a or not b or a == b:
            continue
        yield a, b, level if level in SEVERITY_ORDER else "unknown"


def load_ddinter(paths, replace=True):
    """Load DDInter CSV files. When two rows give the same pair, the higher
    severity wins. Returns a small report used by the coverage table."""
    pairs, rows_read = {}, 0
    for path in paths:
        with open(path, encoding="utf-8-sig", errors="replace") as f:
            for a, b, level in parse_ddinter(f.read()):
                rows_read += 1
                key = (a, b) if a < b else (b, a)
                if SEVERITY_ORDER[level] >= SEVERITY_ORDER.get(pairs.get(key), -1):
                    pairs[key] = level
    if replace:
        db.execute("DELETE FROM drug_interactions WHERE source = 'DDInter'")
    db.get_db().executemany(
        "INSERT INTO drug_interactions (ingredient_a, ingredient_b, severity, source) "
        "VALUES (?, ?, ?, 'DDInter') ON CONFLICT(ingredient_a, ingredient_b) "
        "DO UPDATE SET severity = excluded.severity, source = excluded.source",
        [(a, b, s) for (a, b), s in pairs.items()])
    db.set_setting("interactions_loaded", db.now())
    db.commit()
    return {"rows_read": rows_read, "pairs": len(pairs)}


def between(moieties_1, moieties_2):
    """Interactions between two groups of ingredients, most severe first."""
    m1, m2 = set(moieties_1), set(moieties_2)
    if not m1 or not m2:
        return []
    marks1, marks2 = ",".join("?" * len(m1)), ",".join("?" * len(m2))
    rows = db.query(
        f"SELECT ingredient_a, ingredient_b, severity FROM drug_interactions "
        f"WHERE (ingredient_a IN ({marks1}) AND ingredient_b IN ({marks2})) "
        f"   OR (ingredient_a IN ({marks2}) AND ingredient_b IN ({marks1}))",
        (*m1, *m2, *m2, *m1))
    found = []
    for r in rows:
        a, b = (r["ingredient_a"], r["ingredient_b"]) if r["ingredient_a"] in m1 \
            else (r["ingredient_b"], r["ingredient_a"])
        found.append({"own": a, "other": b, "severity": r["severity"]})
    return sorted(found, key=lambda x: -SEVERITY_ORDER[x["severity"]])


def drug_moieties(drug):
    from .rxnorm import aliases                 # RxNorm names match the U.S. names in DDInter
    return aliases({moiety_key(n) for n in drug["ingredient_key"].split("|") if n})


def with_saved_medicines(drug, user_id):
    """Interactions between this product and each medicine the patient saved."""
    own = drug_moieties(drug)
    saved = db.query("SELECT d.* FROM favorites f JOIN drugs d ON d.id = f.drug_id "
                     "WHERE f.user_id = ? AND d.id != ?", (user_id, drug["id"]))
    warnings = []
    for other in saved:
        hits = between(own, drug_moieties(other))
        if hits:
            warnings.append({"drug": other, "interactions": hits,
                             "severity": hits[0]["severity"]})
    return sorted(warnings, key=lambda w: -SEVERITY_ORDER[w["severity"]])


def count_for(drug):
    """How many interactions are recorded for this product's ingredients."""
    own = drug_moieties(drug)
    if not own:
        return 0
    marks = ",".join("?" * len(own))
    return db.one(f"SELECT COUNT(*) AS n FROM drug_interactions "
                  f"WHERE ingredient_a IN ({marks}) OR ingredient_b IN ({marks})",
                  (*own, *own))["n"]
