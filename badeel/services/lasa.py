"""Look-alike / sound-alike (LASA) names: names that are easily confused.

Two sources:
- ISMP's List of Confused Drug Names (U.S., 2015 edition, PDF): pairs that
  caused real medication errors. Brand names and generic names.
- Pairs found in Badeel's own drug list: Egyptian brand names that differ by
  one or two letters but contain different active ingredients. No public
  list of these exists for the Egyptian market.

The drug page warns when the product's brand or ingredient is in a pair and
the other name is also sold in Egypt.
"""
import re
import shutil
import subprocess
from collections import defaultdict

from .. import db
from .normalize import moiety_key, norm_text

ISMP_URL = ("https://www.ismp.org/sites/default/files/attachments/2017-11/"
            "confuseddrugnames%2802.2015%29.pdf")
ISMP_LICENCE = "ISMP List of Confused Drug Names (February 2015), Institute for Safe Medication Practices."


def key(name):
    """'aMILoride' and 'Allegra (fexofenadine)' -> 'amiloride', 'allegra'."""
    t = norm_text(re.sub(r"\([^)]*\)", " ", name or ""))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9؀-ۿ+ -]", " ", t)).strip()


def brand(trade_name):
    """Brand part of an Egyptian trade name: letters before the first digit."""
    t = norm_text(trade_name).replace("®", " ")
    t = re.split(r"\d", t, maxsplit=1)[0]
    t = re.sub(r"\([^)]*\)", " ", t)
    return re.sub(r"\s+", " ", re.sub(r"[^a-z؀-ۿ ]+", " ", t)).strip()


# ------------------------------------------------------------ ISMP list
def parse_ismp_text(text):
    """Pairs from `pdftotext -layout` output of the ISMP list (two pairs per line)."""
    pairs, started = set(), False
    for line in text.splitlines():
        if "Drug Name" in line and "Confused" in line:
            started = True
            continue
        if not started or not line.strip() or line.lstrip().startswith(("*", "Institute", "©", "Updated", "www.")):
            continue
        parts = [p for p in re.split(r"\s{2,}", line.strip()) if p]
        if len(parts) >= 4:
            found = [(parts[0], parts[1]), (parts[2], parts[3])]
        elif len(parts) in (2, 3):
            found = [(parts[0], parts[1])]
        else:
            continue
        for a, b in found:
            ka, kb = key(a), key(b)
            if ka and kb and ka != kb and len(ka) < 60 and len(kb) < 60:
                pairs.add((ka, kb))
    return pairs


def read_ismp_pdf(path):
    exe = shutil.which("pdftotext")
    if not exe:
        raise RuntimeError("pdftotext was not found (package poppler-utils).")
    out = subprocess.run([exe, "-layout", path, "-"], check=True, capture_output=True)
    return parse_ismp_text(out.stdout.decode("utf-8", errors="replace"))


# ------------------------------------------------------------ pairs in the Egyptian list
def _edits(a, b, limit=2):
    """Levenshtein distance, stopping early above limit."""
    if abs(len(a) - len(b)) > limit:
        return limit + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        best = cur[0]
        for j, cb in enumerate(b, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb))
            best = min(best, cur[j])
        if best > limit:
            return limit + 1
        prev = cur
    return prev[-1]


def find_local_pairs(rows, min_len=5):
    """Egyptian brands that differ by one letter (two for long names) but share no ingredient.

    rows: [(trade_name, ingredient_key)]. Brands of the same family
    ("panadol" / "panadol extra") are left out because they share a first word.
    """
    ingredients = defaultdict(set)
    for trade, ing in rows:
        b = brand(trade)
        if len(b.replace(" ", "")) >= min_len and re.match(r"[a-z]", b):
            ingredients[b] |= {moiety_key(x) for x in ing.split("|") if x}
    brands = sorted(ingredients)
    buckets = defaultdict(list)
    for b in brands:
        buckets[b[0]].append(b)
    pairs = set()
    for group in buckets.values():
        for i, a in enumerate(group):
            for b in group[i + 1:]:
                if a.split()[0] == b.split()[0]:
                    continue                                 # same brand family
                limit = 1 if max(len(a), len(b)) < 8 else 2
                if _edits(a, b, limit) <= limit and not (ingredients[a] & ingredients[b]):
                    pairs.add((a, b))
    return pairs


# ------------------------------------------------------------ loading and lookup
def load(ismp_pairs, local_pairs):
    db.execute("DELETE FROM lasa_pairs")
    rows = [(a, b, "ISMP") for a, b in ismp_pairs] + [(b, a, "ISMP") for a, b in ismp_pairs]
    rows += [(a, b, "Badeel") for a, b in local_pairs] + [(b, a, "Badeel") for a, b in local_pairs]
    db.get_db().executemany("INSERT OR IGNORE INTO lasa_pairs VALUES (?, ?, ?)", rows)
    db.set_setting("lasa_loaded", db.now())
    db.commit()
    return {"ismp": len(ismp_pairs), "local": len(local_pairs)}


def for_drug(drug):
    """Confusable names for this product that are also sold in Egypt.

    Returns [{'mine', 'other', 'source', 'drug_id' (a product with the other name or None)}].
    """
    mine = {brand(drug["trade_name"])}
    mine |= {moiety_key(x) for x in drug["ingredient_key"].split("|") if x}
    mine.discard("")
    if not mine:
        return []
    marks = ",".join("?" * len(mine))
    rows = db.query(f"SELECT name_a, name_b, source FROM lasa_pairs WHERE name_a IN ({marks})", tuple(mine))
    out, seen = [], set()
    for r in rows:
        if r["name_b"] in seen:
            continue
        seen.add(r["name_b"])
        other = db.one("SELECT id, trade_name FROM drugs WHERE lower(trade_name) LIKE ? "
                       "AND ingredient_key != ? ORDER BY id LIMIT 1",
                       (r["name_b"] + " %", drug["ingredient_key"]))
        if not other:                       # the confused name as an ingredient
            other = db.one("SELECT d.id, d.trade_name FROM drugs d JOIN drug_ingredients di ON di.drug_id = d.id "
                           "JOIN ingredients i ON i.id = di.ingredient_id WHERE i.name = ? LIMIT 1", (r["name_b"],))
        if other or r["source"] == "Badeel":
            out.append({"mine": r["name_a"], "other": r["name_b"], "source": r["source"],
                        "drug_id": other["id"] if other else None})
    return out[:6]
