"""Common side effects from SIDER 4.1 (side effects mined from drug labels, CC BY-SA 4.0).

meddra_freq.tsv.gz gives, per drug and side effect (MedDRA preferred term),
how often it happened in the label's trials. Badeel keeps, per ingredient,
the side effects with a known frequency (excluding placebo rows) and shows
the most frequent ones. A few common terms have Arabic names; the others are
shown in English.
"""
import collections
import csv
import gzip
import io
import os

from .. import db
from .normalize import moiety_key

BASE_URL = "https://sideeffects.embl.de/media/download/"
FILES = ["drug_names.tsv", "meddra_freq.tsv.gz"]
LICENCE = "SIDER 4.1 (Kuhn et al., Nucleic Acids Research 2016): CC BY-SA 4.0."

# Arabic names for common MedDRA terms (written by the project; to be reviewed by a pharmacist).
ARABIC = {
    "Nausea": "غثيان", "Vomiting": "ترجيع", "Diarrhoea": "إسهال", "Constipation": "إمساك",
    "Headache": "صداع", "Dizziness": "دوخة", "Somnolence": "نعاس", "Fatigue": "إرهاق",
    "Insomnia": "أرق", "Rash": "طفح جلدي", "Pruritus": "حكة", "Dry mouth": "جفاف الفم",
    "Abdominal pain": "ألم في البطن", "Abdominal pain upper": "ألم أعلى البطن", "Dyspepsia": "عسر هضم",
    "Flatulence": "غازات", "Decreased appetite": "قلة الشهية", "Anorexia": "فقدان الشهية",
    "Oedema peripheral": "تورم الرجلين", "Hypertension": "ارتفاع الضغط", "Hypotension": "انخفاض الضغط",
    "Palpitations": "خفقان", "Tachycardia": "سرعة ضربات القلب", "Cough": "كحة", "Dyspnoea": "ضيق تنفس",
    "Back pain": "ألم في الظهر", "Arthralgia": "ألم في المفاصل", "Myalgia": "ألم في العضلات",
    "Asthenia": "ضعف عام", "Anxiety": "قلق", "Depression": "اكتئاب", "Tremor": "رعشة",
    "Vision blurred": "زغللة", "Sweating increased": "عرق زيادة", "Hyperhidrosis": "عرق زيادة",
    "Weight increased": "زيادة الوزن", "Weight decreased": "نقص الوزن", "Pyrexia": "سخونية",
    "Upper respiratory tract infection": "التهاب الجهاز التنفسي العلوي", "Nasopharyngitis": "زكام",
    "Urinary tract infection": "التهاب المسالك البولية", "Sinusitis": "التهاب الجيوب الأنفية",
    "Flushing": "احمرار الوش", "Hot flush": "هبات سخونة", "Muscle spasms": "تقلصات عضلية",
    "Pain in extremity": "ألم في الأطراف", "Paraesthesia": "تنميل", "Anaemia": "أنيميا",
    "Gastrooesophageal reflux disease": "ارتجاع المريء", "Influenza": "إنفلونزا", "Pharyngitis": "التهاب الحلق",
    "Agitation": "عصبية", "Confusion": "تشويش", "Sedation": "تهدئة ونعاس", "Alopecia": "تساقط الشعر",
}
# Effects that matter for driving or work with machines.
DROWSY = {"Somnolence", "Dizziness", "Sedation", "Vision blurred", "Fatigue", "Asthenia", "Confusion"}


def _read(path):
    if path.endswith(".gz"):
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as f:
            return f.read()
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def estimate(lo, hi):
    """A single rate for sorting. Exact rates ("5%") have lo == hi; word
    categories are wide ranges ("common" = 1% to 100%), so their lower end,
    the only part the leaflet guarantees, is used."""
    return hi if hi - lo <= 0.1 else lo


def label(lo, hi):
    """'9%', '<1%', or '≥1%' for a word category such as 'common'."""
    if hi - lo > 0.1:
        return f"≥{lo * 100:.0f}%" if lo >= 0.01 else "<1%"
    return f"{hi * 100:.0f}%" if hi >= 0.01 else "<1%"


def load_sider(folder):
    """Load from a folder holding drug_names.tsv and meddra_freq.tsv.gz."""
    names = {}
    for row in csv.reader(io.StringIO(_read(os.path.join(folder, "drug_names.tsv"))), delimiter="\t"):
        if len(row) >= 2:
            names[row[0]] = moiety_key(row[1])
    best = {}
    for row in csv.reader(io.StringIO(_read(os.path.join(folder, "meddra_freq.tsv.gz"))), delimiter="\t"):
        if len(row) < 10 or row[3] == "placebo" or row[7] != "PT":
            continue
        ing = names.get(row[0])
        if not ing:
            continue
        try:
            lo, hi = float(row[5]), float(row[6])
        except ValueError:
            continue
        if hi <= 0:                                   # "0%": not seen in that trial
            continue
        k = (ing, row[9])
        if k not in best or estimate(lo, hi) > estimate(*best[k]):
            best[k] = (lo, hi)
    db.execute("DELETE FROM ingredient_side_effects")
    db.get_db().executemany(
        "INSERT INTO ingredient_side_effects (ingredient, effect, freq_lower, freq_upper, source) "
        "VALUES (?, ?, ?, ?, 'SIDER')", [(i, e, lo, hi) for (i, e), (lo, hi) in best.items()])
    db.set_setting("side_effects_loaded", db.now())
    db.commit()
    return {"rows": len(best), "ingredients": len({i for i, _ in best})}


def for_drug(drug, limit=8):
    """Most frequent side effects of the product's ingredients.

    Returns [{'effect', 'ar', 'percent', 'drowsy'}], most frequent first.
    """
    from .rxnorm import aliases
    own = sorted(aliases({moiety_key(x) for x in drug["ingredient_key"].split("|") if x}))
    if not own:
        return []
    marks = ",".join("?" * len(own))
    best = {}
    for r in db.query(f"SELECT effect, freq_lower AS lo, freq_upper AS hi FROM ingredient_side_effects "
                      f"WHERE ingredient IN ({marks})", own):
        if r["effect"] not in best or estimate(r["lo"], r["hi"]) > estimate(*best[r["effect"]]):
            best[r["effect"]] = (r["lo"], r["hi"])
    top = sorted(best.items(), key=lambda kv: (-estimate(*kv[1]), kv[0]))[:limit]
    return [{"effect": e, "ar": ARABIC.get(e), "percent": label(lo, hi), "drowsy": e in DROWSY}
            for e, (lo, hi) in top]
