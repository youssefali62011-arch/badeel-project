"""Downloading outside data sources into data/raw/ (never committed to Git).

Every file is saved unchanged, next to a SOURCE.json that records where it
came from, its licence and the date, so each cleaning step can be repeated
and the paper can cite exactly what was used.

The addresses are settings, not constants in the code, because sources move:
    BADEEL_DDINTER_URL   folder that holds ddinter_downloads_code_<X>.csv
    BADEEL_OPENFDA_URL   openFDA download index (download.json)
    BADEEL_DRUGCENTRAL_URL   DrugCentral database dump (.pgdump, about 1.4 GB)
"""
import json
import os
import urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW_DIR = os.path.join(ROOT, "data", "raw")

DDINTER_URL = "https://ddinter2.scbdd.com/static/media/download/"
# DDInter publishes one file per ATC first-level code.
DDINTER_CODES = ["A", "B", "D", "H", "L", "M", "P", "R", "S", "V"]
DDINTER_LICENCE = ("DDInter (Xiong et al., Nucleic Acids Research). Reported as CC BY-NC-SA 4.0: "
                   "check the licence on the DDInter website before publishing derived data.")

OPENFDA_URL = "https://api.fda.gov/download.json"
OPENFDA_LICENCE = "openFDA drug labels: public domain (CC0), U.S. Food and Drug Administration."

DRUGCENTRAL_URL = ("https://unmtid-dbs.net/download/DrugCentral/2027/db_dump/"
                   "Drugcentral_2026-09-25.pgdump")
DRUGCENTRAL_LICENCE = "DrugCentral (University of New Mexico): CC BY-SA 4.0."

USER_AGENT = "Badeel-academic-project/1.0"


def _today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def download(url, dest, log=print):
    """Save url to dest. Skips the download when dest already exists."""
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        log(f"  already downloaded: {os.path.relpath(dest, ROOT)}")
        return dest
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    log(f"  downloading {url}")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    tmp = dest + ".part"
    with urllib.request.urlopen(req, timeout=120) as resp, open(tmp, "wb") as out:
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            out.write(chunk)
    os.replace(tmp, dest)
    return dest


def _write_source(folder, name, urls, licence):
    with open(os.path.join(folder, "SOURCE.json"), "w", encoding="utf-8") as f:
        json.dump({"source": name, "downloaded_on": _today(), "urls": urls,
                   "licence": licence}, f, indent=2)


def fetch_ddinter(base_url=None, raw_dir=RAW_DIR, log=print):
    """Download all DDInter files. Returns the list of local paths."""
    base = (base_url or os.environ.get("BADEEL_DDINTER_URL") or DDINTER_URL).rstrip("/") + "/"
    folder = os.path.join(raw_dir, "ddinter", _today())
    urls = [f"{base}ddinter_downloads_code_{c}.csv" for c in DDINTER_CODES]
    paths = [download(u, os.path.join(folder, u.rsplit("/", 1)[1]), log) for u in urls]
    _write_source(folder, "DDInter", urls, DDINTER_LICENCE)
    return paths


def fetch_openfda_labels(index_url=None, raw_dir=RAW_DIR, log=print):
    """Download every partition of the openFDA drug label dataset (zipped JSON)."""
    index_url = index_url or os.environ.get("BADEEL_OPENFDA_URL") or OPENFDA_URL
    folder = os.path.join(raw_dir, "openfda_labels", _today())
    index_path = download(index_url, os.path.join(folder, "download.json"), log)
    with open(index_path, encoding="utf-8") as f:
        index = json.load(f)
    parts = index["results"]["drug"]["label"]["partitions"]
    urls = [p["file"] for p in parts]
    log(f"  openFDA drug labels: {len(urls)} files")
    paths = [download(u, os.path.join(folder, u.rsplit("/", 1)[1]), log) for u in urls]
    _write_source(folder, "openFDA drug labels", [index_url] + urls, OPENFDA_LICENCE)
    return paths


def fetch_drugcentral(url=None, raw_dir=RAW_DIR, log=print):
    """Download the DrugCentral database dump (one file, about 1.4 GB)."""
    url = url or os.environ.get("BADEEL_DRUGCENTRAL_URL") or DRUGCENTRAL_URL
    folder = os.path.join(raw_dir, "drugcentral", _today())
    path = download(url, os.path.join(folder, url.rsplit("/", 1)[1]), log)
    _write_source(folder, "DrugCentral", [url], DRUGCENTRAL_LICENCE)
    return [path]


def fetch_ismp(raw_dir=RAW_DIR, log=print):
    """ISMP List of Confused Drug Names (PDF, 2015 edition)."""
    from .lasa import ISMP_LICENCE, ISMP_URL
    folder = os.path.join(raw_dir, "ismp")
    path = download(ISMP_URL, os.path.join(folder, "ismp_confused_drug_names_2015.pdf"), log)
    _write_source(folder, "ISMP List of Confused Drug Names", [ISMP_URL], ISMP_LICENCE)
    return path


def fetch_sider(raw_dir=RAW_DIR, log=print):
    """SIDER 4.1 side effects: drug_names.tsv and meddra_freq.tsv.gz. Returns the folder."""
    from .side_effects import BASE_URL, FILES, LICENCE
    folder = os.path.join(raw_dir, "sider")
    urls = [BASE_URL + f for f in FILES]
    for u in urls:
        download(u, os.path.join(folder, u.rsplit("/", 1)[1]), log)
    _write_source(folder, "SIDER 4.1", urls, LICENCE)
    return folder


def fetch_eda_otc(raw_dir=RAW_DIR, log=print):
    """EDA list of medicines sold without a prescription (PDF, January 2026)."""
    from .eda import EDA_OTC_URL
    folder = os.path.join(raw_dir, "eda")
    path = download(EDA_OTC_URL, os.path.join(folder, "otc-list-5-1-2026.pdf"), log)
    _write_source(folder, "Egyptian Drug Authority OTC list", [EDA_OTC_URL],
                  "Egyptian Drug Authority, public document.")
    return path
