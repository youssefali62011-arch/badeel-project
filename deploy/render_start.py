"""Runs before the web server on Render (see render.yaml).

The disk is empty the first time, so this loads everything the site needs.
Each later start (a deploy, a restart) finds the data and skips it, so the
accounts, the saved medicines and the security log are kept.
"""
import os
import sqlite3
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTANCE = os.environ.get("BADEEL_INSTANCE", os.path.join(ROOT, "instance"))
DB = os.path.join(INSTANCE, "badeel.db")


def manage(*args):
    print("+ manage.py", " ".join(args), flush=True)
    subprocess.run([sys.executable, os.path.join(ROOT, "manage.py"), *args], cwd=ROOT, check=True)


def count(sql):
    if not os.path.exists(DB):
        return 0
    con = sqlite3.connect(DB)
    try:
        return con.execute(sql).fetchone()[0]
    except sqlite3.OperationalError:        # table not created yet
        return 0
    finally:
        con.close()


def main():
    os.makedirs(INSTANCE, exist_ok=True)
    if not count("SELECT COUNT(*) FROM drugs"):
        manage("import-csv", "data/egypt/egyptian-drugs.csv", "--replace")
    if not count("SELECT COUNT(*) FROM drug_interactions"):
        manage("import-enrichment", "dataset")
    if not os.path.exists(os.path.join(INSTANCE, "search_model.json")):
        manage("install-model", "deploy/search_model.json")
    if not count("SELECT COUNT(*) FROM users WHERE role = 'admin' AND status = 'active'"):
        email = os.environ.get("BADEEL_ADMIN_EMAIL")
        if email and os.environ.get("BADEEL_ADMIN_PASSWORD"):
            manage("create-admin", "--email", email, "--name", "Admin")
        else:
            print("No admin yet: set BADEEL_ADMIN_EMAIL and BADEEL_ADMIN_PASSWORD "
                  "in Render (Environment) and redeploy.", flush=True)
    print("Badeel is ready.", flush=True)


if __name__ == "__main__":
    main()
