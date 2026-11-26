# Outside data sources

Added by `python manage.py collect-data`. Files are downloaded unchanged into
`data/raw/<source>/<date>/` with a `SOURCE.json` (address, licence, date).
`data/raw/` is not committed to Git: the files are large and some licences do
not allow re-publishing them.

| Source | What Badeel takes from it | Licence | Table |
|---|---|---|---|
| DDInter 2.0 (https://ddinter2.scbdd.com/) | Drug-drug interactions with severity (Major, Moderate, Minor, Unknown) | Reported as CC BY-NC-SA 4.0: confirm on the DDInter site before publishing derived data | `drug_interactions` |
| openFDA drug labels (index: https://api.fda.gov/download.json) | U.S. package leaflets: indications, dosage, children, older adults, pregnancy, breastfeeding, contraindications, warnings | Public domain (CC0) | `ingredient_labels` |

## Matching

Both sources are matched on the active ingredient, not on the trade name,
with `normalize.moiety_key`: salts and hydrates are removed only for this
match (`diclofenac sodium` and `diclofenac potassium` -> `diclofenac`). A
combination product only gets a leaflet written for exactly the same set of
ingredients.

## Safety

The leaflet is a U.S. leaflet, in English. The drug page says so and says
that Badeel does not choose doses. The children note (`pediatric_note`) is
read by fixed sentence rules (`labels.pediatric_note`); when no rule matches,
nothing is shown, which does not mean the medicine is safe for children. The
precision of these rules on real leaflets still has to be measured.

## If the download is blocked

Download the files in a browser and load them by hand:

    python manage.py load-interactions data/raw/ddinter/*.csv
    python manage.py load-labels data/raw/openfda_labels/*.json.zip
    python manage.py enrichment-report

Re-run both `load-` commands after importing a new drug list: the leaflets
kept are the ones that match the products in the database.

## DrugCentral (diseases)

| Source | What Badeel takes from it | Licence | Table |
|---|---|---|---|
| DrugCentral (https://drugcentral.org/download) | For each active ingredient: diseases it treats (indication) and conditions listed as contraindications | CC BY-SA 4.0 | `ingredient_conditions` |

The dump is a PostgreSQL archive; Badeel reads the two tables it needs
(`omop_relationship`, `synonyms`) with `pg_restore`, so no PostgreSQL server
is needed, only the PostgreSQL 16 client tools.

Patients tick simple groups from `data/patient_conditions.csv` ("Liver
disease"), and each group covers several DrugCentral terms. The Arabic labels
in that file were written by the project and should be reviewed by a
pharmacist.

**Known limitation.** DrugCentral attaches contraindications to an
ingredient from many leaflets, including combination products. For example
it lists 85 conditions for ibuprofen, among them "Agoraphobia" and "Suicidal
thoughts", which most likely come from combinations with other medicines.
The drug page therefore says "contraindications or cautions" and explains
this. The precision of these warnings must be measured on a sample reviewed
by a pharmacist before the paper reports them.

## Safety data: look-alike names, side effects, RxNorm, OTC list

| Source | What Badeel takes from it | Licence | Table |
|---|---|---|---|
| ISMP List of Confused Drug Names, February 2015 (https://www.ismp.org) | Pairs of names that caused real medication errors (U.S. brands and generics) | © ISMP; used for academic, non-commercial work with attribution | `lasa_pairs` (source `ISMP`) |
| Badeel's own drug list | Egyptian brand names that differ by one letter (two for names of 8+ letters) and share no active ingredient, e.g. CIPRAMAX / CIPROMAX | Project data | `lasa_pairs` (source `Badeel`) |
| SIDER 4.1 (http://sideeffects.embl.de) | Side effects with the rate seen in the leaflet's clinical trials (MedDRA preferred terms, placebo rows left out) | CC BY-SA 4.0 | `ingredient_side_effects` |
| RxNorm through the RxNav API (https://lhncbc.nlm.nih.gov/RxNav/) | The U.S. official name of each ingredient (paracetamol → acetaminophen), used to match the other sources; strengths of combination products | Free, no key, at most 20 requests a second. RxNorm is produced by the U.S. National Library of Medicine | `ingredient_rxnorm`, `combo_suggestions` |
| Egyptian Drug Authority OTC list, January 2026 | Ingredients that can be sold without a prescription; the symptom explorer lists them first | Public document | `otc_ingredients` |

    python manage.py collect-data --source ismp     # or: load-lasa PDF
    python manage.py collect-data --source sider    # or: load-side-effects DIR
    python manage.py collect-data --source otc      # or: load-otc PDF
    python manage.py collect-data --source rxnorm   # about 10 minutes the first time

**Combination strengths are proposals.** RxNorm is searched for a product
with the same ingredients and form whose strengths add up to the total in the
Egyptian trade name ("AUGMENTIN 1 GM" → 875 mg + 125 mg). Nothing changes
until a pharmacist approves it on *Pharmacist → Combination strengths*.

**Known limitations.**
- The ISMP list is from the U.S. (2015). The Egyptian pairs are found by
  spelling only; sound-alike pairs in Arabic are not covered.
- SIDER was built in 2015 from U.S. leaflets; newer medicines are missing.
  The rate shown is the highest rate reported in a trial, not the risk for
  one patient.
- The symptom explorer is information to take to a pharmacist or doctor,
  not a prescription. When a danger sign is ticked it shows no medicine.
  The symptoms and their DrugCentral terms (`data/symptoms.csv`,
  `data/red_flags.csv`) were written by the project and must be reviewed by
  a pharmacist.
