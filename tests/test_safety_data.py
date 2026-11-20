"""Tests for look-alike names (ISMP + Egyptian brands), side effects (SIDER),
RxNorm names and combination strengths, and the symptom explorer.

The small files below follow the real formats, but the rows are made up for
the tests: they are not medical facts.
"""
import gzip
import json
import os
import re

from badeel import db
from badeel.services import conditions, importer, lasa, rxnorm, side_effects, symptoms

try:
    from tests.test_app import Base
    from tests.test_conditions import DUMP_TEXT
except ImportError:
    from test_app import Base
    from test_conditions import DUMP_TEXT

PHARMACIST = "pharm@test.local"

ISMP_TEXT = """
            ISMP's List of Confused Drug Names
Drug Name              Confused Drug Name          Drug Name            Confused Drug Name
Brufen                 Brofen*                     aMILoride            amLODIPine
Panadol                Pamelor
* Brand name only in Canada
"""


def fake_rxnav(table):
    """A stand-in for the RxNav API: answers from a dict keyed by path."""
    calls = []

    def get(path, params=None):
        calls.append((path, params))
        if path == "rxcui.json":
            ids = table.get(("name", params["name"]))
            return {"idGroup": {"rxnormId": [ids]} if ids else {}}
        return table.get(path, {})
    get.calls = calls
    return get


class LasaTests(Base):
    def test_parse_ismp(self):
        pairs = lasa.parse_ismp_text(ISMP_TEXT)
        self.assertIn(("amiloride", "amlodipine"), pairs)
        self.assertIn(("panadol", "pamelor"), pairs)
        self.assertIn(("brufen", "brofen"), pairs)            # the * mark is removed

    def test_edit_distance(self):
        self.assertEqual(lasa._edits("cipramax", "cipromax"), 1)
        self.assertGreater(lasa._edits("panadol", "brufen"), 2)

    def test_local_pairs(self):
        rows = [("CIPRAMAX 500MG 10 TAB", "ciprofloxacin"), ("CIPROMAX 20MG 14 TAB", "omeprazole"),
                ("CIPROMEX 250MG", "ciprofloxacin"),            # same ingredient: not a risk
                ("PANADOL 500MG", "paracetamol"), ("PANADOL EXTRA", "caffeine|paracetamol")]
        pairs = lasa.find_local_pairs(rows)
        self.assertIn(("cipramax", "cipromax"), pairs)
        self.assertNotIn(("cipramax", "cipromex"), pairs)
        self.assertFalse(any("panadol" in a and "panadol" in b for a, b in pairs))

    def test_drug_page_warning(self):
        with self.app.app_context():
            lasa.load(lasa.parse_ismp_text(ISMP_TEXT), set())
            found = lasa.for_drug(self.drug("Panadol 500"))
            self.assertEqual(found, [])                         # Pamelor is not sold in this list
            lasa.load(set(), {("panadol", "brufen")})
            found = lasa.for_drug(self.drug("Panadol 500"))
            self.assertEqual(found[0]["other"], "brufen")
            self.assertIsNotNone(found[0]["drug_id"])
        page = self.client.get(f"/drug/{self.drug('Panadol 500')['id']}").get_data(as_text=True)
        self.assertIn('id="lasa"', page)


class SideEffectTests(Base):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        folder = os.path.join(cls.tmp, "sider")
        os.makedirs(folder)
        with open(os.path.join(folder, "drug_names.tsv"), "w") as f:
            f.write("CID100003672\tibuprofen\nCID100000001\tsomething else\n")
        rows = [  # stitch flat, stitch stereo, umls label, placebo, freq text, low, high, level, umls, term
            ["CID100003672", "CID000003672", "C1", "", "5%", "0.05", "0.05", "PT", "C2", "Nausea"],
            ["CID100003672", "CID000003672", "C1", "", "1-9%", "0.01", "0.09", "PT", "C2", "Nausea"],
            ["CID100003672", "CID000003672", "C1", "placebo", "30%", "0.3", "0.3", "PT", "C3", "Headache"],
            ["CID100003672", "CID000003672", "C1", "", "2%", "0.02", "0.02", "LLT", "C4", "Sick"],
            ["CID100003672", "CID000003672", "C1", "", "3%", "0.03", "0.03", "PT", "C5", "Dizziness"],
            ["CID100003672", "CID000003672", "C1", "", "0.5%", "0.005", "0.005", "PT", "C6", "Tinnitus"],
            ["CID100003672", "CID000003672", "C1", "", "common", "0.01", "1", "PT", "C7", "Rash"],
            ["CID100003672", "CID000003672", "C1", "", "0%", "0", "0", "PT", "C8", "Amnesia"],
        ]
        with gzip.open(os.path.join(folder, "meddra_freq.tsv.gz"), "wt") as f:
            f.write("\n".join("\t".join(r) for r in rows) + "\n")
        with cls.app.app_context():
            cls.report = side_effects.load_sider(folder)

    def test_load_and_show(self):
        # placebo and lower-level terms are skipped; the higher Nausea rate wins
        # "0%" rows are skipped; "common" (1% to 100%) counts as at least 1%, not 100%
        self.assertEqual(self.report, {"rows": 4, "ingredients": 1})
        with self.app.app_context():
            found = side_effects.for_drug(self.drug("Brufen 400"))
        self.assertEqual([e["effect"] for e in found], ["Nausea", "Dizziness", "Rash", "Tinnitus"])
        self.assertEqual(found[0]["percent"], "9%")
        self.assertEqual(found[0]["ar"], "غثيان")
        self.assertEqual(found[2]["percent"], "≥1%")
        self.assertEqual(found[3]["percent"], "<1%")
        self.assertTrue(found[1]["drowsy"])
        page = self.client.get(f"/drug/{self.drug('Brufen 400')['id']}").get_data(as_text=True)
        self.assertIn('id="h-side"', page)
        self.assertIn("غثيان", page)


class RxNormTests(Base):
    def test_lookup_ingredient(self):
        get = fake_rxnav({("name", "paracetamol"): "161",
                          "rxcui/161/properties.json": {"properties": {"tty": "IN", "name": "acetaminophen"}}})
        self.assertEqual(rxnorm.lookup_ingredient("paracetamol", get), ("161", "acetaminophen"))
        self.assertEqual(rxnorm.lookup_ingredient("unknownium", get), (None, None))

    def test_salt_goes_to_its_ingredient(self):
        get = fake_rxnav({("name", "x salt"): "9",
                          "rxcui/9/properties.json": {"properties": {"tty": "PIN", "name": "x hydrochloride"}},
                          "rxcui/9/related.json": {"relatedGroup": {"conceptGroup": [
                              {"conceptProperties": [{"rxcui": "8", "name": "x"}]}]}}})
        self.assertEqual(rxnorm.lookup_ingredient("x salt", get), ("8", "x"))

    def test_parse_clinical_drug(self):
        parts, form = rxnorm.parse_clinical_drug("amoxicillin 875 MG / clavulanate 125 MG Oral Tablet")
        self.assertEqual([(p[1], p[2]) for p in parts], [(875.0, "mg"), (125.0, "mg")])
        self.assertTrue(form)
        self.assertEqual(rxnorm.parse_clinical_drug("something odd Oral Tablet"), (None, None))

    def test_aliases_join_outside_names(self):
        with self.app.app_context():
            db.execute("INSERT OR REPLACE INTO ingredient_rxnorm VALUES ('mesalazine', '52582', 'mesalamine', ?)",
                       (db.now(),))
            db.commit()
            self.assertEqual(rxnorm.aliases({"mesalazine"}), {"mesalazine", "mesalamine"})
            db.execute("DELETE FROM ingredient_rxnorm")
            db.commit()

    def test_combination_proposal_and_approval(self):
        csv_text = ("trade_name,active_ingredients,form,price\n"
                    "Testmentin 1 g,Amoxicillin + Clavulanic acid,Tablets,150\n").encode()
        with self.app.app_context():
            importer.import_csv(csv_text)
            d = self.drug("Testmentin 1 g")
            self.assertEqual(d["strength_known"], 0)
            amox, clav = sorted(m for m in d["ingredient_key"].split("|"))
            form = d["form"].split(" (")[0]
            db.execute("INSERT OR REPLACE INTO ingredient_rxnorm VALUES (?, '723', 'amoxicillin', ?)", (amox, db.now()))
            db.execute("INSERT OR REPLACE INTO ingredient_rxnorm VALUES (?, '48203', 'clavulanate', ?)", (clav, db.now()))
            db.commit()
            scd = f"{amox} 875 MG / {clav} 125 MG Oral Tablet"
            get = fake_rxnav({"rxcui/723/related.json": {"relatedGroup": {"conceptGroup": [{"conceptProperties": [
                {"rxcui": "1", "name": scd},
                {"rxcui": "2", "name": f"{amox} 500 MG / {clav} 125 MG Oral Tablet"}]}]}}})
            parts, scd_form = rxnorm.parse_clinical_drug(scd)
            self.assertEqual(scd_form, form)
            r = rxnorm.suggest_combinations(get=get, log=lambda *_: None)
            self.assertGreaterEqual(r["proposals"], 1)
            s = db.one("SELECT * FROM combo_suggestions WHERE drug_id = ?", (d["id"],))
            self.assertEqual(s["evidence"], scd)                # only the split that adds up to 1000 mg
            sid = s["id"]

        self.assertNotEqual(self.client.get("/pharmacist/combinations").status_code, 200)   # not logged in
        self.login(PHARMACIST)
        self.assertIn("Testmentin", self.client.get("/pharmacist/combinations").get_data(as_text=True))
        with self.app.app_context():
            self.assertTrue(rxnorm.approve(sid, None))
            d = self.drug("Testmentin 1 g")
            self.assertEqual(d["strength_known"], 1)
            match = self.drug("Augmentin 1 g")
            self.assertEqual(d["composition_key"], match["composition_key"])   # now an exact alternative
            self.assertFalse(rxnorm.approve(sid, None))          # already done


class SymptomTests(Base):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        dump = os.path.join(cls.tmp, "drugcentral_extract.sql")
        with open(dump, "w", encoding="utf-8") as f:
            f.write(DUMP_TEXT)
        with cls.app.app_context():
            conditions.load_drugcentral([dump])
            db.execute("INSERT OR REPLACE INTO otc_ingredients VALUES ('ibuprofen', 'test')")
            db.commit()

    def test_data_files(self):
        self.assertGreaterEqual(len(symptoms.SYMPTOMS), 25)
        self.assertGreaterEqual(len(symptoms.RED_FLAGS), 8)
        areas = {a[0] for a in symptoms.AREAS}
        self.assertTrue(all(s["area"] in areas for s in symptoms.SYMPTOMS.values()))

    def test_explore(self):
        with self.app.app_context():
            found = symptoms.explore(["pain"])
            self.assertEqual(found[0]["ingredient"], "ibuprofen")
            self.assertTrue(found[0]["otc"])
            prices = [p["price"] for p in found[0]["products"]]
            self.assertEqual(prices, sorted(prices))
            self.assertEqual(symptoms.explore(["no_such_symptom"]), [])

    def test_pages(self):
        page = self.client.get("/symptoms").get_data(as_text=True)
        self.assertIn('name="s"', page)
        page = self.client.get("/symptoms?s=pain").get_data(as_text=True)
        self.assertIn("Brufen", page)
        # a danger sign stops the list: only "see a doctor"
        page = self.client.get("/symptoms?s=pain&rf=chest_pain").get_data(as_text=True)
        self.assertIn("risk-banner", page)
        self.assertNotIn("Brufen", page)
        self.assertIsNone(re.search(r"<style|style=", page))
