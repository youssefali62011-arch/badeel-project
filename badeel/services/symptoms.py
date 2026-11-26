"""Symptom explorer: active ingredients listed as treating what the patient feels.

This is information, not a prescription. For the symptoms the patient ticks,
it lists the active ingredients that DrugCentral gives as
treating them, with:
- ingredients on the EDA's list of medicines sold without a prescription first;
- products sold in Egypt that contain them, cheapest first;
- warnings from the patient's own data (conditions, allergies, saved
  medicines) and from the questions on the page (pregnancy, breastfeeding,
  child);
- danger signs: when one is ticked, no medicine is shown, only "see a doctor now".
Symptoms are not stored.
"""
import csv
import math
import os
import re

from .. import db
from . import conditions, interactions
from .normalize import DATA_DIR, moiety_key


def _csv(name):
    path = os.path.join(DATA_DIR, name)
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


SYMPTOMS = {r["key"]: {**r, "concepts": [c.strip() for c in r["concepts"].split(";") if c.strip()],
                       "forms": {f.strip() for f in r.get("forms", "").split(";") if f.strip()}}
            for r in _csv("symptoms.csv")}

# Which dosage forms a patient would use for a symptom (column "forms" in symptoms.csv).
# Injections and products without a known form are never suggested.
FORM_GROUPS = {
    "oral": {"tablet", "capsule", "syrup", "sachet", "suspension", "oral drops", "chewable tablet", "effervescent",
             "sublingual tablet", "oral solution", "orodispersible tablet", "orodispersible film", "lozenge"},
    "rectal": {"suppository"},
    "skin": {"cream", "gel", "lotion", "ointment", "spray", "shampoo"},
    "eye": {"eye drops", "eye ointment"},
    "nose": {"nasal spray", "nasal drops"},
    "mouth": {"lozenge", "gel", "mouthwash", "oral gel", "spray"},
}
# Names that are fillers or salts in combination products, not the medicine itself.
NOT_A_MEDICINE = {"sodium", "potassium", "citric acid", "water", "sucrose", "glucose", "lactose", "alcohol",
                  "ethanol", "sorbitol", "tartaric acid", "sodium bicarbonate", "sodium lactate", "dextrose"}


_WITHDRAWN = re.compile(r"cancel|illegal|withdraw|stopped", re.I)


def _forms_for(keys):
    out = set()
    for k in keys:
        for group in SYMPTOMS[k]["forms"] or {"oral"}:
            out |= FORM_GROUPS.get(group, set())
    return out
RED_FLAGS = {r["key"]: r for r in _csv("red_flags.csv")}
AREAS = [("general", "General", "عام"), ("head", "Head and teeth", "الراس والسنان"),
         ("breathing", "Nose, throat and chest", "الأنف والزور والصدر"), ("allergy", "Allergy", "حساسية"),
         ("stomach", "Stomach and bowels", "المعدة والبطن"), ("body", "Body", "الجسم"),
         ("skin", "Skin, mouth and eyes", "الجلد والبق والعين")]


# ------------------------------------------------------------ OTC ingredients (EDA list)
def load_otc(eda_products):
    """eda_products: output of eda.read_otc_list(). Stores the ingredient names found in it."""
    names = set()
    for p in eda_products:
        text = re.sub(r"\d.*?(mg|g|mcg|ml|%|iu)\b", " ", p["active"], flags=re.I)
        for part in re.split(r"[/+,;]|\band\b|\bequivalent to\b", text, flags=re.I):
            part = re.sub(r"\(.*?\)|[^A-Za-z -]", " ", part).strip()
            words = part.split()
            for k in range(min(3, len(words)), 0, -1):          # 'Paracetamol microfined' -> 'paracetamol'
                m = moiety_key(" ".join(words[:k]))
                if m and len(m) > 3:
                    names.add(m)
                    break
    present = {moiety_key(r["name"]) for r in db.query("SELECT name FROM ingredients")}
    names &= present
    db.execute("DELETE FROM otc_ingredients")
    db.get_db().executemany("INSERT INTO otc_ingredients VALUES (?, 'EDA OTC list 2026')", [(n,) for n in sorted(names)])
    db.commit()
    return len(names)


# ------------------------------------------------------------ the recommendation
def explore(symptom_keys, user=None, pregnant=False, breastfeeding=False, child=False, limit=10):
    keys = [k for k in symptom_keys if k in SYMPTOMS]
    if not keys:
        return []
    concept_to_keys = {}
    for k in keys:
        for c in SYMPTOMS[k]["concepts"]:
            concept_to_keys.setdefault(c, set()).add(k)
    marks = ",".join("?" * len(concept_to_keys))
    rows = db.query(f"SELECT ingredient, condition FROM ingredient_conditions WHERE relation = 'indication' "
                    f"AND condition IN ({marks})", tuple(concept_to_keys))
    covers = {}
    for r in rows:
        covers.setdefault(r["ingredient"], set()).update(concept_to_keys[r["condition"]])

    # products sold in Egypt with these ingredients
    by_moiety = {}
    for r in db.query("SELECT id, name FROM ingredients"):
        m = moiety_key(r["name"])
        if m in covers:
            by_moiety.setdefault(m, []).append(r["id"])
    otc = {r["ingredient"] for r in db.query("SELECT ingredient FROM otc_ingredients")}

    # the patient's own data
    groups = conditions.user_groups(user) if user else []
    from .. import security
    allergies = set()
    saved = []
    if user:
        allergies = {moiety_key(a) for a in security.decrypt(user["allergies_enc"]).replace("،", ",").split(",") if a.strip()}
        saved = db.query("SELECT d.* FROM favorites f JOIN drugs d ON d.id = f.drug_id WHERE f.user_id = ?", (user["id"],))
    extra = (["Pregnancy, function"] if pregnant else []) + (["Breastfeeding (mother)"] if breastfeeding else [])

    results = []
    for ing, ids in by_moiety.items():
        if ing in NOT_A_MEDICINE:
            continue
        allowed = _forms_for(covers[ing])
        marks2 = ",".join("?" * len(ids))
        products = [d for d in db.query(
            f"SELECT DISTINCT d.* FROM drugs d JOIN drug_ingredients di ON di.drug_id = d.id "
            f"WHERE di.ingredient_id IN ({marks2}) ORDER BY (d.ingredient_key LIKE '%|%'), "
            f"(d.availability = 'shortage'), (d.price IS NULL), d.price", tuple(ids))
            if d["form"].split(" (")[0] in allowed and not _WITHDRAWN.search(d["trade_name"] or "")]
        if not products:
            continue
        alone = any("|" not in d["ingredient_key"] for d in products)
        contra = {r["condition"] for r in db.query(
            "SELECT condition FROM ingredient_conditions WHERE ingredient = ? AND relation = 'contraindication'", (ing,))}
        warnings = []
        for key in groups:
            hit = [c for c in conditions.GROUPS[key]["concepts"] if c in contra]
            if hit:
                warnings.append(("condition", conditions.GROUPS[key]))
        for c in extra:
            if c in contra:
                warnings.append(("pregnancy" if c.startswith("Pregnancy") else "breastfeeding", None))
        if ing in allergies:
            warnings.append(("allergy", None))
        for d in saved:
            if interactions.between({ing}, interactions.drug_moieties(d)):
                warnings.append(("interaction", d))
        if child:
            label = db.one("SELECT pediatric_note, min_age_months FROM ingredient_labels WHERE ingredient_key = ?", (ing,))
            if label and label["pediatric_note"]:
                warnings.append(("child", label))
        matched = covers[ing]
        # products with this ingredient alone count more than ones where it is part of a mixture
        score = (len(matched) * 10 + (20 if ing in otc else 0) + (8 if alone else 0)
                 + math.log(1 + len(products)) - 5 * len(warnings))
        results.append({"ingredient": ing, "symptoms": [SYMPTOMS[k] for k in keys if k in matched],
                        "otc": ing in otc, "products": products[:3], "product_count": len(products), "alone": alone,
                        "warnings": warnings, "score": score})
    results.sort(key=lambda r: (-r["score"], r["ingredient"]))
    return results[:limit]


def red_flags_ticked(keys):
    return [RED_FLAGS[k] for k in keys if k in RED_FLAGS]
