"""RxNorm (U.S. National Library of Medicine) through the free RxNav API.

1. Ingredient names: each Badeel ingredient is looked up once; when RxNorm
   knows it, its official ingredient name and RxCUI are stored. The official
   name is then also used to match outside sources (interactions, diseases,
   side effects), which use U.S. names.
2. Combination strengths: many Egyptian combination products give only a
   total ("AUGMENTIN 1 GM"), so they can never get an exact alternative.
   RxNorm's clinical drugs for the same ingredients and form are searched for
   a split that adds up to that total (875 mg + 125 mg = 1000 mg). The split
   is only a proposal: a pharmacist approves or rejects it.

RxNav terms of service: free, no key, at most 20 requests per second.
"""
import json
import re
import time
import urllib.parse
import urllib.request

from .. import db
from .normalize import canon_form, canon_strength, composition_keys, fmt_strength, moiety_key

API = "https://rxnav.nlm.nih.gov/REST/"
USER_AGENT = "Badeel-academic-project/1.0"
DELAY = 0.08                                  # about 12 requests per second, under the limit


def _get(path, params=None, opener=None):
    url = API + path + (("?" + urllib.parse.urlencode(params)) if params else "")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with (opener or urllib.request.urlopen)(req, timeout=30) as r:
        data = json.load(r)
    time.sleep(DELAY)
    return data


# ------------------------------------------------------------ 1. ingredient names
def lookup_ingredient(name, get=_get):
    """(rxcui, official ingredient name) or (None, None)."""
    ids = (get("rxcui.json", {"name": name, "search": 2}).get("idGroup") or {}).get("rxnormId") or []
    if not ids:
        return None, None
    rxcui = ids[0]
    props = (get(f"rxcui/{rxcui}/properties.json").get("properties")) or {}
    if props.get("tty") in ("IN", "MIN"):
        return rxcui, props.get("name")
    for group in (get(f"rxcui/{rxcui}/related.json", {"tty": "IN"}).get("relatedGroup") or {}).get("conceptGroup") or []:
        for c in group.get("conceptProperties") or []:
            return c["rxcui"], c["name"]
    return rxcui, props.get("name")


def map_ingredients(limit=None, get=_get, log=print, workers=4):
    """Look up every ingredient of the drug list that was not checked yet.

    A few lookups run at the same time (each waits DELAY after a request), which
    stays under RxNav's limit of 20 requests a second. Results are written by
    this thread only, so SQLite is never used from two threads.
    """
    from concurrent.futures import ThreadPoolExecutor
    have = {r["ingredient"] for r in db.query("SELECT ingredient FROM ingredient_rxnorm")}
    names = sorted({moiety_key(r["name"]) for r in db.query("SELECT name FROM ingredients")} - have - {""})
    if limit:
        names = names[:limit]

    def one(name):
        try:
            return name, lookup_ingredient(name, get), None
        except Exception as e:                                    # network error: try again next run
            return name, (None, None), e

    found = done = 0
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        for name, (rxcui, rx_name), error in pool.map(one, names):
            if error:
                log(f"  not checked: {name}: {error}")
                continue
            done += 1
            found += bool(rx_name)
            db.execute("INSERT OR REPLACE INTO ingredient_rxnorm (ingredient, rxcui, rx_name, checked_at) VALUES (?, ?, ?, ?)",
                       (name, rxcui, rx_name, db.now()))
            if done % 200 == 0:
                db.commit()
                log(f"  {done:,} of {len(names):,} checked, {found:,} found")
    db.commit()
    return {"checked": done, "found": found}


def aliases(moieties):
    """The moiety names plus their RxNorm names (as moiety keys), for matching outside sources."""
    moieties = set(moieties)
    if not moieties:
        return moieties
    marks = ",".join("?" * len(moieties))
    for r in db.query(f"SELECT rx_name FROM ingredient_rxnorm WHERE ingredient IN ({marks}) AND rx_name IS NOT NULL",
                      tuple(moieties)):
        moieties.add(moiety_key(r["rx_name"]))
    return moieties


# ------------------------------------------------------------ 2. combination strengths
_PART = re.compile(r"^(?P<name>.+?)\s+(?P<num>\d+(?:\.\d+)?)\s+(?P<unit>MG|MCG|G|UNT|MEQ)(?:/(?P<den>\d*\.?\d*)\s*(?P<dunit>ML|ACTUAT|HR))?$", re.I)


def parse_clinical_drug(name):
    """'amoxicillin 875 MG / clavulanate 125 MG Oral Tablet' ->
    ([('amoxicillin', 875.0, 'mg'), ('clavulanic acid', 125.0, 'mg')], 'tablet')."""
    m = re.search(r"\s(Oral|Injectable|Topical|Chewable|Extended|Delayed|Disintegrating|Ophthalmic|Otic|Nasal|Rectal|Vaginal|Inhalant|Buccal|Sublingual|Transdermal|Prefilled|Cutaneous|Mucosal)\b.*$", name)
    form_text = m.group(0).strip() if m else ""
    body = name[:m.start()] if m else name
    parts = []
    for piece in body.split(" / "):
        p = _PART.match(piece.strip())
        if not p:
            return None, None
        value, unit = canon_strength(p["num"], p["unit"].lower().replace("unt", "iu"),
                                     p["den"] or None, (p["dunit"] or "").lower() or None)
        parts.append((moiety_key(p["name"]), value, unit))
    return parts, canon_form(form_text).split(" (")[0]


def _total(trade_name):
    """The single strength written in an Egyptian trade name: 'AUGMENTIN 1 GM' -> (1000, 'mg')."""
    from .normalize import STRENGTH_RE
    found = list(STRENGTH_RE.finditer(trade_name or ""))
    if len(found) != 1:
        return None
    try:
        return canon_strength(*found[0].groups())
    except (ValueError, ZeroDivisionError):
        return None


def suggest_combinations(get=_get, log=print, max_groups=None):
    """Create pending proposals for combination products that only show a total strength."""
    rows = db.query("SELECT d.id, d.trade_name, d.form, d.ingredient_key FROM drugs d "
                    "WHERE d.strength_known = 0 AND d.ingredient_key LIKE '%|%'")
    groups = {}
    for d in rows:
        total = _total(d["trade_name"])
        if total:
            key = (d["ingredient_key"], d["form"].split(" (")[0], total)
            groups.setdefault(key, []).append(d)
    rx = {r["ingredient"]: r["rxcui"] for r in db.query(
        "SELECT ingredient, rxcui FROM ingredient_rxnorm WHERE rx_name IS NOT NULL")}
    cache, made, checked = {}, 0, 0
    for (ing_key, form, (total, unit)), drugs in list(groups.items())[:max_groups]:
        moieties = [moiety_key(x) for x in ing_key.split("|")]
        if not all(m in rx for m in moieties):
            continue
        checked += 1
        first = rx[moieties[0]]
        if first not in cache:
            try:
                data = get(f"rxcui/{first}/related.json", {"tty": "SCD"})
            except Exception as e:
                log(f"  stopped: {e}")
                break
            cache[first] = [c["name"] for g in (data.get("relatedGroup") or {}).get("conceptGroup") or []
                            for c in g.get("conceptProperties") or []]
        target = set(moieties)
        for scd in cache[first]:
            parts, scd_form = parse_clinical_drug(scd)
            if not parts or {p[0] for p in parts} != target or scd_form != form:
                continue
            if any(p[2] != unit for p in parts):
                continue
            if abs(sum(p[1] for p in parts) - total) > max(0.5, total * 0.01):
                continue
            proposal = json.dumps([{"ingredient": p[0], "value": p[1], "unit": p[2]} for p in parts], sort_keys=True)
            for d in drugs:
                cur = db.execute("INSERT OR IGNORE INTO combo_suggestions (drug_id, proposal, evidence, created_at) "
                                 "VALUES (?, ?, ?, ?)", (d["id"], proposal, scd, db.now()))
                made += cur.rowcount
    db.commit()
    return {"product_groups": len(groups), "groups_checked": checked, "proposals": made}


def approve(suggestion_id, user_id):
    """Write the approved strengths on the product, so it can get exact alternatives."""
    s = db.one("SELECT * FROM combo_suggestions WHERE id = ? AND status = 'pending'", (suggestion_id,))
    if not s:
        return False
    proposal = {p["ingredient"]: p for p in json.loads(s["proposal"])}
    ings = db.query("SELECT di.ingredient_id, i.name FROM drug_ingredients di JOIN ingredients i ON i.id = di.ingredient_id "
                    "WHERE di.drug_id = ?", (s["drug_id"],))
    items = []
    for r in ings:
        p = proposal.get(moiety_key(r["name"]))
        if not p:
            return False                                    # the product changed since the proposal
        text = fmt_strength(p["value"], p["unit"])
        db.execute("UPDATE drug_ingredients SET strength_value = ?, strength_unit = ?, strength_text = ? "
                   "WHERE drug_id = ? AND ingredient_id = ?", (p["value"], p["unit"], text, s["drug_id"], r["ingredient_id"]))
        items.append({"name": r["name"], "value": p["value"], "unit": p["unit"], "text": text})
    ing_key, comp_key, known = composition_keys(items)
    display = " + ".join(i["text"].replace("mg", " mg").replace("  ", " ") for i in sorted(items, key=lambda x: x["name"]))
    db.execute("UPDATE drugs SET composition_key = ?, strength_known = ?, strength_display = ?, updated_at = ? WHERE id = ?",
               (comp_key, int(known), display, db.now(), s["drug_id"]))
    db.execute("UPDATE combo_suggestions SET status = 'approved', reviewed_by = ?, reviewed_at = ? WHERE id = ?",
               (user_id, db.now(), suggestion_id))
    db.execute("UPDATE combo_suggestions SET status = 'rejected', reviewed_by = ?, reviewed_at = ? "
               "WHERE drug_id = ? AND status = 'pending'", (user_id, db.now(), s["drug_id"]))
    db.bump_data_version()
    db.commit()
    return True


def reject(suggestion_id, user_id):
    db.execute("UPDATE combo_suggestions SET status = 'rejected', reviewed_by = ?, reviewed_at = ? "
               "WHERE id = ? AND status = 'pending'", (user_id, db.now(), suggestion_id))
    db.commit()
