"""Command-line tasks.

    python manage.py setup                first-time setup (start_windows.bat runs this)
    python manage.py init                 create the database + load demo data
    python manage.py create-admin         create an admin account (asks for a password)
    python manage.py demo-users           create / show the demo patient and pharmacist
    python manage.py reset-demo           wipe everything except admins, reload demo data
    python manage.py peek-users           show what is really stored for each user
    python manage.py train-model          train the search ranking model
    python manage.py audit-sample         print random products to check strength/form by hand
    python manage.py import-csv FILE      import drugs from a CSV file
    python manage.py import-csv FILE --replace    delete current drugs first
    python manage.py collect-data         download DDInter + openFDA leaflets and load them
    python manage.py collect-data --source ddinter    only one source (ddinter | labels | drugcentral |
                                                       ismp | sider | otc | rxnorm)
    python manage.py load-lasa [PDF]      look-alike names: ISMP list + similar Egyptian brands
    python manage.py load-side-effects DIR   SIDER 4.1 folder (drug_names.tsv, meddra_freq.tsv.gz)
    python manage.py load-otc [PDF]       ingredients on the EDA list of medicines without a prescription
    python manage.py rxnorm-map [--limit N]   look up the RxNorm name of every ingredient (internet)
    python manage.py rxnorm-combos        propose strengths for combination products (pharmacist approves)
    python manage.py load-interactions FILE...        load DDInter CSV files downloaded by hand
    python manage.py load-labels FILE...              load openFDA label files downloaded by hand
    python manage.py load-conditions FILE             load the DrugCentral dump downloaded by hand
    python manage.py enrichment-report    coverage numbers (saved in docs/results/)
    python manage.py export-dataset DIR   write the enriched data as CSV files
    python manage.py import-enrichment DIR   load interactions, conditions and leaflets from those files
    python manage.py install-model FILE   use a search model trained elsewhere (search_model.json)
    python manage.py send-reminders       send medicine reminders that are due (run every 5 minutes)
    python manage.py send-reminders --loop 300    keep running, checking every 300 seconds
"""
import argparse
import getpass
import os
import secrets
import sys

from flask import current_app

from badeel import create_app, db, security
from badeel.services import conditions, eda, lasa, rxnorm, side_effects, symptoms, coverage, export, importer, reminders, interactions, labels, ranker, search, sources

ROOT = os.path.dirname(os.path.abspath(__file__))

# Accounts used to rehearse and present. Their passwords are generated on
# each machine and kept in instance/demo_accounts.txt, which is not in Git.
DEMO_ACCOUNTS = [
    ("patient", "Demo Patient", "patient@badeel.demo"),
    ("pharmacist", "Demo Pharmacist", "pharmacist@badeel.demo"),
]


def _accounts_file():
    return os.path.join(os.path.dirname(current_app.config["DATABASE"]), "demo_accounts.txt")


def _load_sample():
    with open(os.path.join(ROOT, "data", "sample_drugs.csv"), "rb") as f:
        report = importer.import_csv(f.read())
    db.set_setting("demo_data", "1")
    db.commit()
    return report


def cmd_init(_args):
    if db.one("SELECT COUNT(*) AS n FROM drugs")["n"]:
        print("Database already has drugs. Nothing changed.")
        return
    report = _load_sample()
    print(f"Database ready. Demo drugs loaded: {report['added']} "
          f"(skipped {report['skipped']}).")


def cmd_create_admin(args):
    email = (args.email or input("Admin e-mail: ")).strip().lower()
    name = (args.name or input("Admin name: ")).strip()
    # The password is typed here (hidden) or read from an environment variable.
    # It is never written in the code or in Git.
    password = os.environ.get("BADEEL_ADMIN_PASSWORD")
    if not password:
        print("Type the password. Nothing appears while you type: that is normal.")
        password = getpass.getpass("Password: ")
        if getpass.getpass("Repeat password: ") != password:
            sys.exit("The two passwords do not match. Run the command again.")
    if not security.EMAIL_RE.match(email):
        sys.exit("Invalid e-mail.")
    problem = security.password_problem(password, email, name)
    if problem:
        sys.exit("Password rejected: " + security.password_message(problem, lambda en, ar: en))
    if db.one("SELECT 1 FROM users WHERE email = ?", (email,)):
        db.execute("UPDATE users SET password_hash = ?, role = 'admin', status = 'active', "
                   "failed_logins = 0, locked_until = NULL WHERE email = ?",
                   (security.hash_password(password), email))
        print("Existing account updated: it is now an active admin with the new password.")
    else:
        db.execute("INSERT INTO users (name, email, password_hash, role, status, created_at) "
                   "VALUES (?, ?, ?, 'admin', 'active', ?)",
                   (name or "Admin", email, security.hash_password(password), db.now()))
        print("Admin account created.")
    db.commit()


def cmd_demo_users(_args):
    path = _accounts_file()
    missing = [a for a in DEMO_ACCOUNTS
               if not db.one("SELECT 1 FROM users WHERE email = ?", (a[2],))]
    if os.path.exists(path) and not missing:
        with open(path, encoding="utf-8") as f:
            print(f.read().rstrip())
        return
    lines = ["Demo accounts (for rehearsal and presentation only):"]
    for role, name, email in DEMO_ACCOUNTS:
        password = f"{role.capitalize()}-demo-{secrets.randbelow(900000) + 100000}"
        if db.one("SELECT 1 FROM users WHERE email = ?", (email,)):
            db.execute("UPDATE users SET password_hash = ?, role = ?, status = 'active', "
                       "failed_logins = 0, locked_until = NULL WHERE email = ?",
                       (security.hash_password(password), role, email))
        else:
            db.execute("INSERT INTO users (name, email, password_hash, role, status, created_at) "
                       "VALUES (?, ?, ?, ?, 'active', ?)",
                       (name, email, security.hash_password(password), role, db.now()))
        lines.append(f"  {role:<11} {email:<24} {password}")
    db.commit()
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


def cmd_setup(_args):
    """Safe to run every time: only does what is still missing."""
    if not db.one("SELECT COUNT(*) AS n FROM drugs")["n"]:
        cmd_init(None)
    if not db.one("SELECT 1 FROM users WHERE role = 'admin' AND status = 'active'"):
        print("\nCreate the admin account (you will use it to log in as admin).")
        cmd_create_admin(argparse.Namespace(email=None, name=None))
    if not ranker.model_info(os.path.dirname(current_app.config["DATABASE"])):
        print("\nFirst run: training the search model...")
        cmd_train_model(None)
    print()
    cmd_demo_users(None)
    print("Admin: the e-mail and password you chose. Forgot it? Run: "
          "python manage.py create-admin")


def cmd_train_model(_args):
    print("Training the search model. With the full Egyptian list this takes 5 to 20 minutes;"
          " a line is printed after each of the 5 folds.", flush=True)
    data = search.train_model(log=lambda m: print(m, flush=True))
    cv = data["cv"]
    print(f"Search model trained on {data['drugs']} drugs in {data['seconds']} s. "
          f"Cross-validated top-1: model {cv['model']['all']['top1']:.1%}, "
          f"without model {cv['baseline']['all']['top1']:.1%}.")


def cmd_audit_sample(args):
    """Random products with what was read from them, to check by hand."""
    import random
    rows = db.query("SELECT trade_name, ingredients_display, strength_display, form, "
                    "pack_count, strength_known FROM drugs")
    random.seed(args.seed)
    print("no | trade name | ingredients | strength read | form read | pack | matchable")
    for i, r in enumerate(random.sample(rows, min(args.n, len(rows))), 1):
        print(f"{i:3} | {r['trade_name']} | {r['ingredients_display']} | "
              f"{r['strength_display'] or '-'} | {r['form']} | {r['pack_count'] or '-'} | "
              f"{'yes' if r['strength_known'] else 'no'}")


def cmd_reset_demo(args):
    if db.get_setting("demo_data") != "1":
        print("WARNING: this database holds data you imported yourself. "
              "Reset replaces it with the demo drugs.")
    if not args.yes and input("Type RESET to delete all data except admin accounts: ") != "RESET":
        sys.exit("Cancelled.")
    for table in ("favorites", "search_history", "security_events", "audit_log",
                  "drug_ingredients", "drugs", "ingredients"):
        db.execute(f"DELETE FROM {table}")
    db.execute("DELETE FROM users WHERE role != 'admin'")
    db.execute("UPDATE users SET failed_logins = 0, locked_until = NULL")
    report = _load_sample()
    if os.path.exists(_accounts_file()):
        os.remove(_accounts_file())
    print(f"Reset done. Demo drugs: {report['added']}.")
    cmd_train_model(None)
    print()
    cmd_demo_users(None)


def cmd_peek_users(_args):
    """Shows the raw database values: proof that nothing sensitive is readable."""
    rows = db.query("SELECT email, role, status, password_hash, allergies_enc FROM users")
    for r in rows:
        print(f"{r['email']}  ({r['role']}, {r['status']})")
        print(f"   password_hash : {r['password_hash'][:70]}...")
        enc = r["allergies_enc"]
        print(f"   allergies_enc : {(enc[:70] + '...') if enc else '(empty)'}")
        if enc:
            print(f"   decrypted     : {security.decrypt(enc)}   <- only the app, with the key, can do this")
    if not rows:
        print("No users.")


def cmd_import(args):
    with open(args.file, "rb") as f:
        report = importer.import_csv(f.read(), replace=args.replace)
    if report["fatal"]:
        sys.exit("Import failed: " + report["fatal"])
    if args.replace:
        db.set_setting("demo_data", "0")
        db.commit()
    print(f"Added {report['added']}, updated {report['updated']}, skipped {report['skipped']}.")
    for line, name, error in report["errors"]:
        print(f"  line {line} ({name}): {error}")


def _load_interactions(paths):
    r = interactions.load_ddinter(paths)
    print(f"DDInter: {r['rows_read']:,} rows read, {r['pairs']:,} interaction pairs stored.")


def _load_labels(paths):
    r = labels.load_openfda(paths)
    print(f"openFDA: {r['leaflets_read']:,} leaflets read, "
          f"{r['ingredient_sets']:,} ingredient sets of the drug list have a leaflet.")


def _load_conditions(paths):
    r = conditions.load_drugcentral(paths)
    print(f"DrugCentral: {r['relations']:,} ingredient-disease rows for {r['ingredients']:,} "
          f"ingredient names and {r['conditions']:,} diseases.")


def cmd_load_conditions(args):
    _load_conditions(args.files)


def cmd_load_lasa(args):
    pdf = args.pdf or sources.fetch_ismp()
    ismp = lasa.read_ismp_pdf(pdf)
    local = lasa.find_local_pairs([(r["trade_name"], r["ingredient_key"])
                                   for r in db.query("SELECT trade_name, ingredient_key FROM drugs")])
    r = lasa.load(ismp, local)
    print(f"Look-alike names: {r['ismp']:,} ISMP pairs, {r['local']:,} similar Egyptian brand pairs.")


def cmd_load_side_effects(args):
    r = side_effects.load_sider(args.dir or sources.fetch_sider())
    print(f"SIDER: {r['rows']:,} side effects with a frequency, for {r['ingredients']:,} ingredient names.")


def cmd_load_otc(args):
    n = symptoms.load_otc(eda.read_otc_list(args.pdf or sources.fetch_eda_otc()))
    print(f"EDA OTC list: {n:,} ingredients of the drug list can be sold without a prescription.")


def cmd_rxnorm_map(args):
    r = rxnorm.map_ingredients(limit=args.limit)
    print(f"RxNorm: {r['checked']:,} ingredient names checked, {r['found']:,} found.")


def cmd_rxnorm_combos(_args):
    r = rxnorm.suggest_combinations()
    print(f"RxNorm: {r['product_groups']:,} combination groups show only a total strength, "
          f"{r['groups_checked']:,} checked, {r['proposals']:,} proposals waiting for a pharmacist.")


def cmd_collect_data(args):
    """Download the outside sources into data/raw/ and load them."""
    if args.source in ("all", "ddinter"):
        print("DDInter (drug-drug interactions)")
        _load_interactions(sources.fetch_ddinter())
    if args.source in ("all", "labels"):
        print("openFDA drug labels (package leaflets). About 13 large files: this takes a while.")
        _load_labels(sources.fetch_openfda_labels())
    if args.source in ("all", "drugcentral"):
        print("DrugCentral (what each ingredient treats and must not be used with). About 1.4 GB.")
        _load_conditions(sources.fetch_drugcentral())
    if args.source in ("all", "ismp"):
        print("ISMP list of confused drug names, and similar Egyptian brands")
        args.pdf = None
        cmd_load_lasa(args)
    if args.source in ("all", "sider"):
        print("SIDER 4.1 (side effects)")
        args.dir = None
        cmd_load_side_effects(args)
    if args.source in ("all", "otc"):
        print("EDA list of medicines sold without a prescription")
        args.pdf = None
        cmd_load_otc(args)
    if args.source in ("all", "rxnorm"):
        print("RxNorm names (about 12 lookups a second: about 15 minutes the first time)")
        args.limit = None
        cmd_rxnorm_map(args)
        cmd_rxnorm_combos(args)
    cmd_enrichment_report(args)


def cmd_load_interactions(args):
    _load_interactions(args.files)


def cmd_load_labels(args):
    _load_labels(args.files)


def cmd_enrichment_report(_args):
    text = coverage.as_text(coverage.report())
    print("\n" + text)
    out = os.path.join(ROOT, "docs", "results", "enrichment_report.txt")
    with open(out, "w", encoding="utf-8") as f:
        f.write(text + "\n")
    print(f"\nSaved to {os.path.relpath(out, ROOT)}")


def cmd_import_enrichment(args):
    counts = export.import_enrichment(args.dir)
    print(f"Loaded {counts['interactions']:,} interactions, {counts['conditions']:,} disease rows "
          f"and {counts['leaflets']:,} leaflets from {args.dir}.")


def cmd_install_model(args):
    import json
    with open(args.file, encoding="utf-8") as f:
        data = json.load(f)                   # plain numbers only: never a pickle (no code can run)
    try:
        if data.get("features") != ranker.FEATURES:
            raise ValueError("trained with another feature set")
        ranker.Model(data)
    except (ValueError, KeyError, TypeError, AttributeError) as e:
        sys.exit(f"This file is not a usable Badeel search model: {e}")
    dest = os.path.join(os.path.dirname(current_app.config["DATABASE"]), "search_model.json")
    # the model learned typing mistakes, not this list: mark it as matching the current data
    data["data_version"] = db.get_setting("data_version", "0")
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(data, f)
    print(f"Search model installed ({data.get('drugs', '?')} drugs, trained {data.get('trained_at', '?')}).")


def cmd_send_reminders(args):
    import time
    if not reminders.push_available():
        sys.exit("pywebpush is not installed: pip install -r requirements.txt")
    contact = os.environ.get("BADEEL_PUSH_CONTACT", "mailto:admin@badeel.invalid")
    while True:
        reminders.send_due(contact=contact)
        if not args.loop:
            break
        time.sleep(max(60, args.loop))


def cmd_export_dataset(args):
    counts = export.export(args.dir, os.path.join(ROOT, "data", "patient_conditions.csv"))
    for name, n in counts.items():
        size = os.path.getsize(os.path.join(args.dir, name)) / 1e6
        print(f"  {name:<30} {n:>9,} rows  {size:6.1f} MB")


def main():
    parser = argparse.ArgumentParser(description="Badeel management commands")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("setup").set_defaults(func=cmd_setup)
    sub.add_parser("init").set_defaults(func=cmd_init)
    p = sub.add_parser("create-admin")
    p.add_argument("--email")
    p.add_argument("--name")
    p.set_defaults(func=cmd_create_admin)
    sub.add_parser("demo-users").set_defaults(func=cmd_demo_users)
    p = sub.add_parser("reset-demo")
    p.add_argument("--yes", action="store_true")
    p.set_defaults(func=cmd_reset_demo)
    sub.add_parser("peek-users").set_defaults(func=cmd_peek_users)
    sub.add_parser("train-model").set_defaults(func=cmd_train_model)
    p = sub.add_parser("audit-sample")
    p.add_argument("--n", type=int, default=100)
    p.add_argument("--seed", type=int, default=1)
    p.set_defaults(func=cmd_audit_sample)
    p = sub.add_parser("import-csv")
    p.add_argument("file")
    p.add_argument("--replace", action="store_true")
    p.set_defaults(func=cmd_import)
    p = sub.add_parser("collect-data")
    p.add_argument("--source", choices=["all", "ddinter", "labels", "drugcentral", "ismp", "sider", "otc", "rxnorm"], default="all")
    p.set_defaults(func=cmd_collect_data)
    p = sub.add_parser("load-interactions")
    p.add_argument("files", nargs="+")
    p.set_defaults(func=cmd_load_interactions)
    p = sub.add_parser("load-labels")
    p.add_argument("files", nargs="+")
    p.set_defaults(func=cmd_load_labels)
    p = sub.add_parser("load-conditions")
    p.add_argument("files", nargs="+")
    p.set_defaults(func=cmd_load_conditions)
    p = sub.add_parser("send-reminders")
    p.add_argument("--loop", type=int, default=0)
    p.set_defaults(func=cmd_send_reminders)
    p = sub.add_parser("import-enrichment")
    p.add_argument("dir")
    p.set_defaults(func=cmd_import_enrichment)
    p = sub.add_parser("install-model")
    p.add_argument("file")
    p.set_defaults(func=cmd_install_model)
    p = sub.add_parser("export-dataset")
    p.add_argument("dir")
    p.set_defaults(func=cmd_export_dataset)
    p = sub.add_parser("load-lasa")
    p.add_argument("pdf", nargs="?")
    p.set_defaults(func=cmd_load_lasa)
    p = sub.add_parser("load-side-effects")
    p.add_argument("dir", nargs="?")
    p.set_defaults(func=cmd_load_side_effects)
    p = sub.add_parser("load-otc")
    p.add_argument("pdf", nargs="?")
    p.set_defaults(func=cmd_load_otc)
    p = sub.add_parser("rxnorm-map")
    p.add_argument("--limit", type=int)
    p.set_defaults(func=cmd_rxnorm_map)
    sub.add_parser("rxnorm-combos").set_defaults(func=cmd_rxnorm_combos)
    sub.add_parser("enrichment-report").set_defaults(func=cmd_enrichment_report)
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        args.func(args)


if __name__ == "__main__":
    main()
