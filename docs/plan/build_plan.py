import html, datetime
E = html.escape

def table(head, rows, cls=""):
    h = "".join(f"<th>{c}</th>" for c in head)
    b = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<table class="{cls}"><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table>'

def st(s):
    m = {"done": ("Done", "ok"), "review": ("In review", "rev"), "todo": ("To do", "todo"),
         "stretch": ("Stretch", "str"), "doing": ("In progress", "doing")}
    t, c = m[s]
    return f'<span class="pill {c}">{t}</span>'

# ---------------------------------------------------------------- Gantt
def gantt(title, weeks, rows):
    n = len(weeks)
    head = "".join(f'<div class="gw">{w}</div>' for w in weeks)
    body = ""
    for label, track, a, b, kind in rows:
        cells = ""
        for i in range(1, n + 1):
            on = a <= i <= b
            cells += f'<div class="gc {"g-"+kind if on else ""}"></div>'
        body += f'<div class="gl"><b>{label}</b><span>{track}</span></div>{cells}'
    return (f'<div class="gantt" style="grid-template-columns: 210px repeat({n}, 1fr)">'
            f'<div class="gl gh">{title}</div>{head}{body}</div>')

s1_weeks = ["W1<br>29 Nov", "W2<br>6 Dec", "W3<br>13 Dec", "W4<br>20 Dec", "W5<br>27 Dec", "W6<br>3 Jan", "W7<br>10 Jan"]
s1_rows = [
    ("Merge open work, rebrand", "Full stack", 1, 1, "fs"),
    ("Data review: EDA, 100-sample audit", "Data science", 1, 3, "ds"),
    ("Gold set 40 → 500 pairs", "Data science + pharmacist", 2, 5, "ds"),
    ("Fill 2,308 missing rows, combos", "Data science", 2, 4, "ds"),
    ("Cabinet checker, market analytics", "Data science + full stack", 3, 5, "ds"),
    ("LightGBM LambdaMART vs current", "AI", 1, 3, "ai"),
    ("Arabic/Franco phonetic features", "AI", 2, 4, "ai"),
    ("OCR + voice benchmark sets", "AI", 3, 6, "ai"),
    ("Grounded assistant (stretch)", "AI", 5, 7, "str"),
    ("Hash-chained log, 2FA, blind index", "Cybersecurity", 1, 4, "cy"),
    ("Bot detection → honeypot", "Cybersecurity", 3, 5, "cy"),
    ("ZAP scan + Burp manual test", "Cybersecurity", 4, 6, "cy"),
    ("PostgreSQL, HTTPS, backups, domain", "Cybersecurity / DevOps", 2, 6, "cy"),
    ("Family profiles, emergency card", "Full stack", 4, 6, "fs"),
    ("Ethics approval for user study", "Supervisor + team", 5, 7, "pm"),
    ("Feature freeze, v1.0 release, demo", "Everyone", 7, 7, "ms"),
]
s2_weeks = [f"W{i}" for i in range(1, 21)]
s2_rows = [
    ("Final experiments (benchmarks)", "AI + Data science", 1, 4, "ai"),
    ("User study (SUS, n ≥ 30)", "Full stack + all", 2, 5, "fs"),
    ("Pharmacist validation of warnings", "Data science", 2, 5, "ds"),
    ("Dataset v2.0 with DOI", "Data science", 4, 5, "ds"),
    ("Thesis ch. 2–3 (literature, analysis)", "All tracks", 3, 7, "pm"),
    ("Thesis ch. 4–5 (design, build)", "All tracks", 6, 10, "pm"),
    ("Thesis ch. 6–7 (evaluation, conclusion)", "All tracks", 9, 12, "pm"),
    ("Paper A draft → internal review", "Paper team", 8, 13, "ms"),
    ("Paper A submission", "Paper team", 14, 14, "ms"),
    ("Paper B (dataset) — Data in Brief", "Data science", 12, 16, "str"),
    ("Bug fixes only, polish, accessibility", "Full stack + cyber", 1, 16, "cy"),
    ("Thesis full review by supervisor", "Supervisor", 13, 16, "pm"),
    ("Poster, demo video, rehearsals", "Everyone", 16, 19, "fs"),
    ("Final submission + defense", "Everyone", 19, 20, "ms"),
]

# ---------------------------------------------------------------- architecture SVG
arch = r'''
<svg viewBox="0 0 900 470" class="diagram" xmlns="http://www.w3.org/2000/svg" font-family="Inter, sans-serif">
<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="#475569"/></marker></defs>
<rect x="10" y="10" width="880" height="62" rx="10" fill="#eef6ff" stroke="#93c5fd"/>
<text x="24" y="34" font-size="13" font-weight="700" fill="#1e3a8a">Users</text>
<text x="24" y="54" font-size="11.5" fill="#334155">Patient · Pharmacist · Admin — browser or installed app (PWA), Arabic RTL / English, dark &amp; light, voice (Web Speech API), camera</text>
<rect x="10" y="96" width="880" height="160" rx="10" fill="#f8fafc" stroke="#cbd5e1"/>
<text x="24" y="118" font-size="13" font-weight="700" fill="#0f172a">Badeel web application (Flask, Jinja2, vanilla JS) — security middleware on every request</text>
<g font-size="11">
<rect x="24" y="130" width="160" height="112" rx="8" fill="#fff" stroke="#94a3b8"/><text x="34" y="150" font-weight="700">Search</text><text x="34" y="168">TF-IDF candidates</text><text x="34" y="184">12-feature learned ranker</text><text x="34" y="200">phonetic Arabic/English</text><text x="34" y="216">OCR (Tesseract) · voice</text>
<rect x="196" y="130" width="160" height="112" rx="8" fill="#fff" stroke="#94a3b8"/><text x="206" y="150" font-weight="700">Exact matching</text><text x="206" y="168">ingredient + strength</text><text x="206" y="184">+ dosage form keys</text><text x="206" y="200">price per unit, savings</text><text x="206" y="216">shortage status</text>
<rect x="368" y="130" width="160" height="112" rx="8" fill="#fff" stroke="#94a3b8"/><text x="378" y="150" font-weight="700">Safety layer</text><text x="378" y="168">interactions · allergies</text><text x="378" y="184">contraindications</text><text x="378" y="200">look-alike names</text><text x="378" y="216">side effects · symptoms</text>
<rect x="540" y="130" width="160" height="112" rx="8" fill="#fff" stroke="#94a3b8"/><text x="550" y="150" font-weight="700">Patient services</text><text x="550" y="168">saved medicines</text><text x="550" y="184">reminders, refill alerts</text><text x="550" y="200">health profile (encrypted)</text><text x="550" y="216">dashboards per role</text>
<rect x="712" y="130" width="164" height="112" rx="8" fill="#fff1f2" stroke="#fda4af"/><text x="722" y="150" font-weight="700" fill="#9f1239">Security</text><text x="722" y="168">CSP, CSRF, rate limits</text><text x="722" y="184">Argon2/strong passwords</text><text x="722" y="200">Fernet health data</text><text x="722" y="216">audit + security log, trap</text>
</g>
<rect x="10" y="280" width="430" height="80" rx="10" fill="#f0fdf4" stroke="#86efac"/>
<text x="24" y="303" font-size="13" font-weight="700" fill="#14532d">Database (SQLite now → PostgreSQL)</text>
<text x="24" y="322" font-size="11" fill="#334155">drugs, ingredients, users, favorites, reminders, audit_log,</text>
<text x="24" y="338" font-size="11" fill="#334155">drug_interactions, ingredient_conditions, ingredient_labels, lasa_pairs,</text>
<text x="24" y="354" font-size="11" fill="#334155">ingredient_side_effects, ingredient_rxnorm, otc_ingredients</text>
<rect x="460" y="280" width="430" height="80" rx="10" fill="#fefce8" stroke="#fde047"/>
<text x="474" y="303" font-size="13" font-weight="700" fill="#713f12">Offline data pipeline (manage.py collect-data)</text>
<text x="474" y="322" font-size="11" fill="#334155">download → parse → normalise names (moiety key + RxNorm)</text>
<text x="474" y="338" font-size="11" fill="#334155">→ keep only ingredients sold in Egypt → load → coverage report</text>
<text x="474" y="354" font-size="11" fill="#334155">→ export dataset (CSV + dataset card)</text>
<rect x="460" y="384" width="430" height="76" rx="10" fill="#fff" stroke="#cbd5e1" stroke-dasharray="4 3"/>
<text x="474" y="405" font-size="12" font-weight="700">Outside sources</text>
<text x="474" y="423" font-size="11" fill="#334155">Egyptian drug list · EDA OTC list · DDInter 2.0 · openFDA labels</text>
<text x="474" y="439" font-size="11" fill="#334155">DrugCentral · SIDER 4.1 · ISMP confused names · RxNorm (RxNav)</text>
<text x="474" y="455" font-size="11" fill="#334155">Later: pharmacist-reviewed gold set, real user queries, box photos</text>
<path d="M450 72 V94" stroke="#475569" stroke-width="1.6" marker-end="url(#ar)"/>
<path d="M225 256 V278" stroke="#475569" stroke-width="1.6" marker-end="url(#ar)"/>
<path d="M675 384 V362" stroke="#475569" stroke-width="1.6" marker-end="url(#ar)"/>
<path d="M460 320 H442" stroke="#475569" stroke-width="1.6" marker-end="url(#ar)"/>
</svg>'''

# ---------------------------------------------------------------- content
done_rows = [
 ["Core product", "Exact-alternative engine (same ingredient + strength + form), price per unit, shortage status, roles (patient, pharmacist, admin), Arabic/English", "22,757 products imported in 2.9 s; 9,752 products have ≥1 exact alternative; 2,072 groups (median 3, max 43)", st("done")],
 ["Search", "Spelling-tolerant search: TF-IDF candidates + 12-feature logistic-regression ranker, Arabic transliteration", "5-fold grouped CV, 18,000 queries: top-1 83.0% → 93.0%, top-3 97.3%, MRR 0.952; Arabic queries 74.1% → 86.2%", st("done")],
 ["Data enrichment", "DDInter interactions, openFDA leaflets, DrugCentral uses and contraindications", "164,839 interaction pairs (71.7% of products); leaflets for 43.7%; known use for 80.4%", st("done")],
 ["Open dataset v1.0", "6 CSV files + dataset card, licences per file", "products 22,757 · ingredients 57,932 · interactions 72,490 · conditions 32,291 · leaflets 1,007", st("done")],
 ["Official verification", "Cross-check with the EDA list of medicines sold without a prescription (Jan 2026)", "321 of 355 EDA products found; same ingredients 93.3%; same strength 86.2%; 80 rows sent to human review", st("done")],
 ["Interface", "Redesign, dark/light mode, a dashboard per role", "Merged (PR #4)", st("done")],
 ["Voice & photo search", "Web Speech API (ar-EG / en-US); Tesseract OCR, photo deleted after reading", "Merged (PR #17)", st("done")],
 ["Reminders & PWA", "Dose reminders, refill alert from pack size, installable app, push notifications", "Merged (PR #18)", st("done")],
 ["Deployment", "PythonAnywhere guide; Render blueprint with gunicorn", "Merged (PR #5, PR #21); custom domain pending (issue #6)", st("doing")],
 ["Safety data", "Look-alike names (ISMP + Egyptian pairs), SIDER side effects, RxNorm names, combination strengths, symptom explorer", "390 ISMP + 502 Egyptian pairs; side effects for 46.0%; 2,976 ingredients in RxNorm; 47 strength proposals", st("review")],
 ["Testing & security", "Unit/integration tests; automated attack suite", "132 tests pass; 65/65 attacks blocked, 35/35 detected; 239 requests/s, 95% < 114 ms", st("done")],
 ["Thesis", "Chapter 1 (introduction, problem, objectives)", "Written", st("done")],
]

sources = [
 ["Egyptian drug list", "Products, Arabic/English names, ingredients, price, form, company", "GitHub (egyptian-drug-database), ~25k rows", "Loaded", "Open"],
 ["EDA OTC list (Jan 2026)", "Official list of medicines sold without a prescription", "edaegypt.gov.eg PDF", "Loaded", "Public document"],
 ["DDInter 2.0", "Drug–drug interactions with severity", "ddinter2.scbdd.com, 10 CSV files", "Loaded", "CC BY-NC-SA 4.0 (non-commercial)"],
 ["openFDA drug labels", "Leaflet sections: dosage, warnings, children, pregnancy", "api.fda.gov bulk download", "Loaded", "Public domain"],
 ["DrugCentral", "What each ingredient treats; contraindications", "drugcentral.org PostgreSQL dump (pg_restore)", "Loaded", "CC BY-SA 4.0"],
 ["SIDER 4.1", "Side effects with trial frequencies", "sideeffects.embl.de", "Loaded (PR #19)", "CC BY-SA 4.0"],
 ["ISMP Confused Drug Names", "Look-alike / sound-alike pairs", "ismp.org (2015 PDF)", "Loaded (PR #19)", "© ISMP, attribution"],
 ["RxNorm via RxNav", "Official ingredient names, clinical drugs and strengths", "rxnav.nlm.nih.gov REST API, no key", "Loaded (PR #19)", "Free, ≤20 requests/s"],
 ["Pharmacist-reviewed gold set", "500 product pairs labelled match / no match", "Built by the team, reviewed by a pharmacist", "To build", "Project (CC0)"],
 ["Real misspelled queries", "1,000+ queries typed by people (Arabic, English, Franco)", "Dictation study (see §6)", "To build", "Project, consented"],
 ["Box photo set", "200 photos of Egyptian medicine boxes", "Taken by the team with phones", "To build", "Project"],
 ["Voice set", "100 spoken drug names, 10 speakers", "Recorded in the app with consent", "To build", "Project, consented"],
]

ai_rows = [
 ["LightGBM LambdaMART vs current ranker", "Same 12 features + 4 new; train lightgbm.LGBMRanker on the 18,000-query set; same 5-fold grouped CV; report top-1, top-3, MRR per error type", "pip lightgbm; ml/train.py", "Table with both models, ±std; McNemar test on top-1", "Mohamed Ashraf", "#15"],
 ["Arabic / Franco phonetic features", "Arabic→Latin transliteration table, Double Metaphone on both sides, Franco digits (3, 7, 2 for the letters ain, haa, hamza)", "jellyfish / metaphone", "Arabic top-1 ≥ 90% (now 86.2%)", "Mohamed Ashraf", "new"],
 ["Real-query benchmark", "Run the model on the dictation study queries (§6); compare with synthetic results", "Study data", "Top-1 on real queries reported", "Mohamed Ashraf", "new"],
 ["OCR benchmark", "200 box photos → Tesseract → search; measure product found in top-1/top-3; try image pre-processing (grayscale, threshold, deskew)", "Tesseract ara+eng, OpenCV", "Top-3 ≥ 80% on clear photos", "Mohamed Ashraf + DS", "new"],
 ["Voice benchmark", "100 recorded names → speech text → search", "Web Speech API", "Top-1 reported per language", "Mohamed Ashraf", "new"],
 ["Grounded assistant (stretch)", "Answers only from Badeel's own database (retrieve product, leaflet, interactions → fixed templates or a small LLM with citations); refuses dosing questions", "Retrieval + templates; optional LLM API", "0 answers without a source in a 100-question test", "Mohamed Ashraf", "stretch"],
]
ds_rows = [
 ["Finish EDA review", "Review the 80 flagged rows; record decision and reason", "data/verification/eda_otc_review.csv", "All 80 rows decided", "Bahaa, Abdelrahman", "#12, #13, PR #20"],
 ["100-product audit", "Random sample (seed fixed) checked against EDA site and pharmacy price", "edaegypt.gov.eg, pharmacy apps", "Error rate with 95% CI", "Mohamed Ali", "#14"],
 ["Gold set 40 → 500 pairs", "Stratified sample: single/combination, forms, near-misses (same ingredient, other strength); pharmacist labels; Cohen's κ on 100 double-labelled pairs", "Pharmacist volunteer", "500 labelled pairs, κ ≥ 0.8", "Data science team", "new"],
 ["Combination strengths", "Pharmacist reviews the 47 RxNorm proposals; extend parser for “500/125” and per-5 ml totals", "Pharmacist page (PR #19)", "Coverage of combination products ↑ (report before/after)", "Abdelrahman", "new"],
 ["2,308 rows without ingredient", "Match by brand to a second Egyptian list (Kaggle) or EDA search; manual fill for the most sold", "Kaggle Egyptian drug datasets", "≥ 50% filled, source per row", "Mohamed Ali", "new"],
 ["Medicine cabinet checker", "Patient enters 2–6 medicines: interactions between all pairs + same ingredient under two brands (double dose)", "DDInter table, ingredient keys", "Page + tests", "Bahaa + full stack", "new"],
 ["Market analytics page", "Shortage rate per class, average savings of the cheapest exact alternative, companies", "Badeel database", "Page with 4 charts", "Data science team", "new"],
 ["Dataset v2.0", "Add safety tables, gold set, query benchmark; Zenodo release for a DOI", "zenodo.org GitHub integration", "DOI cited in the paper", "Data science team", "new"],
]
cy_rows = [
 ["Manual penetration test", "Burp Suite on every page and role; OWASP WSTG checklist; report with CVSS", "Burp Community", "0 high/critical open", "Mahmoud Eid", "#9"],
 ["Automated scan", "OWASP ZAP baseline + full scan, authenticated", "ZAP", "Findings table for the paper", "Ahmed Taha", "#10"],
 ["Tamper-evident audit log", "Each row stores SHA-256(previous hash + row); a check command detects edits or deletions", "hashlib", "Test: changing one row is detected", "Youssef Ali", "new"],
 ["2FA for admin & pharmacist", "TOTP (RFC 6238) with recovery codes", "pyotp + QR", "Login needs the code; tests", "Mohamed Adel", "new"],
 ["Allergy check without decrypting", "Blind index: HMAC-SHA256(key, ingredient) stored next to the encrypted list", "hmac", "Allergy warnings work; no plaintext in RAM per page", "Ziad", "new"],
 ["Bot detection → honeypot", "Features per session (rate, path entropy, trap hits); Isolation Forest flags scrapers and sends them to trap pages", "scikit-learn", "Precision/recall on simulated bots", "Ahmed Taha", "new"],
 ["Production hardening", "PostgreSQL, HTTPS, secrets in environment, nightly backups + restore drill, custom domain", "Render, pg_dump", "Restore tested; HTTPS A on SSL Labs", "Youssef Awad, Youssef Ali", "#6, #11"],
 ["Privacy & law", "Privacy policy (AR/EN); requirements of Egypt's Personal Data Protection Law No. 151 of 2020 for health data", "Law text, Data Protection Center", "Policy page + compliance checklist", "Mohamed Adel, Ziad", "#7, #8"],
]
fs_rows = [
 ["Merge open work", "Review and merge PR #19 (safety data) and PR #20 (EDA review)", "GitHub", "Main branch green", "Toqa, Youssef Ali", "—"],
 ["Rebrand", "Choose the final name, logo and colour palette; apply site-wide with CSS tokens", "Design proposals sent", "One commit, screenshots", "Toqa + team vote", "new"],
 ["Family profiles", "Sub-profiles (father, mother, child) each with conditions, allergies, medicines; “searching for: …” switch", "Existing health profile code", "Warnings follow the chosen person", "Full stack", "new"],
 ["Emergency card", "QR card with blood type, conditions, allergies; patient can switch the link off", "qrcode library", "Card + revocable link", "Full stack + cyber", "new"],
 ["Accessibility", "Large-text mode, WCAG 2.2 AA contrast, keyboard use, screen reader labels", "axe DevTools, Lighthouse", "Lighthouse accessibility ≥ 95", "Full stack", "new"],
]

milestones = [
 ["M1", "Sun 6 Dec 2026", "Open work merged; final name and palette chosen", "PR #19, #20 merged; rebrand committed"],
 ["M2", "Sat 19 Dec 2026", "Data verified", "EDA review done; 100-sample audit with error rate; LightGBM comparison table"],
 ["M3", "Sat 2 Jan 2027", "Security & data features complete", "2FA, hash-chained log, blind index, PostgreSQL; gold set ≥ 300 pairs"],
 ["M4", "Sat 9 Jan 2027", "Security tested", "ZAP + Burp reports, 0 high/critical; backups restored once"],
 ["M5", "Thu 14 Jan 2027", "Feature freeze — v1.0 release", "All tests + attack suite green; live site with HTTPS and domain; demo to supervisor"],
 ["M6", "Sat 6 Mar 2027", "Experiments done", "Gold set 500 (κ reported); user study n ≥ 30; OCR/voice/real-query benchmarks; dataset v2.0 DOI"],
 ["M7", "Sat 3 Apr 2027", "Thesis chapters 2–5 drafted", "Reviewed by supervisor"],
 ["M8", "Sat 1 May 2027", "Thesis chapters 6–7 + paper draft", "All tables and figures generated from scripts in the repository"],
 ["M9", "Sat 15 May 2027", "Paper A submitted", "Submission confirmation"],
 ["M10", "June 2027 (official date)", "Final thesis, poster, video, defense", "Signed submission; rehearsal × 2"],
]

eval_rows = [
 ["Exact matching", "500-pair pharmacist gold set", "Precision, recall, F1; errors by cause", "P ≥ 0.98 (a wrong alternative is the worst error)"],
 ["Search (synthetic)", "18,000+ generated misspellings, grouped 5-fold CV", "Top-1, top-3, MRR per error type; model vs baseline vs LightGBM", "Done: 93.0% top-1"],
 ["Search (real)", "1,000+ queries from the dictation study", "Same metrics; synthetic vs real gap", "Top-1 ≥ 85%"],
 ["Photo / voice", "200 photos; 100 recordings", "Product in top-1 / top-3; failure causes", "Top-3 ≥ 80% (photo)"],
 ["Data accuracy", "EDA cross-check; 100-product audit", "Agreement %, error rate with 95% CI", "Done (EDA); audit pending"],
 ["Safety warnings", "200 warnings sampled, reviewed by a pharmacist", "Precision per source (DDInter, DrugCentral, SIDER, LASA)", "Report honestly; fix sources < 0.8"],
 ["Usability", "Patients, pharmacists, older adults (n ≥ 30)", "SUS score, task success, time on task", "SUS ≥ 70"],
 ["Security", "Attack suite, ZAP, Burp", "Prevention and detection rate; findings by severity", "100% / 0 high open"],
 ["Performance", "Load test, 20 users at once; 20,000-product scale test", "Requests/s, p95 latency", "Done: 239 req/s, p95 114 ms"],
]

risks = [
 ["Pharmacist not available for labels", "High", "Ask the Faculty of Pharmacy in January; split the 500 pairs into 5 short sessions; pay in co-authorship acknowledgement"],
 ["Medical harm from wrong advice", "High", "Information-only wording; danger signs stop suggestions; no dose calculator; disclaimer on every safety page; pharmacist review"],
 ["DDInter licence is non-commercial", "Medium", "Academic use only; state it in the dataset card; swap source if the project becomes a product"],
 ["Exams and Ramadan reduce time", "Medium", "Feature freeze 14 Jan; Ramadan (about 8 Feb – 9 Mar 2027) is for experiments, not new code"],
 ["Scope creep", "Medium", "Only items in this plan; new ideas go to a “later” list; stretch items are cut first"],
 ["Free hosting sleeps or loses data", "Medium", "PostgreSQL with nightly backups; restore drill; local copy for the defense"],
 ["OCR weak on Arabic boxes", "Low", "Report honestly; English side of the box is the main input; pre-processing experiment"],
 ["Paper rejected", "Low", "Target a second venue already chosen; dataset paper as a separate output"],
]

thesis = [
 ["1", "Introduction", "Problem, motivation, objectives, scope", st("done")],
 ["2", "Literature review", "Drug name matching, LASA, learned ranking, drug knowledge bases (RxNorm, DrugBank, DDInter, DrugCentral, SIDER), health app security; comparison table of 10–15 works", st("todo")],
 ["3", "Requirements & analysis", "Stakeholders, use cases per role, functional / non-functional requirements, data requirements", st("todo")],
 ["4", "System design", "Architecture, database schema, matching algorithm, ranking model, safety layer, security design, UI", st("todo")],
 ["5", "Implementation", "Data pipeline, search, matching, safety, reminders/PWA, security controls, deployment", st("todo")],
 ["6", "Testing & evaluation", "All experiments in §6 with tables, figures and error analysis", st("todo")],
 ["7", "Conclusion & future work", "Contributions, limitations, next steps", st("todo")],
]

css = """
@page { size: A4; margin: 16mm 15mm 18mm; }
* { box-sizing: border-box; }
body { font-family: Inter, 'DejaVu Sans', sans-serif; color: #0f172a; font-size: 10.2pt; line-height: 1.5; margin: 0; }
h1 { font-size: 21pt; margin: 0 0 4mm; letter-spacing: -.02em; }
h2 { font-size: 15pt; margin: 0 0 3mm; padding-bottom: 2mm; border-bottom: 2px solid #0e7490; color: #0e7490; letter-spacing: -.01em; }
h3 { break-after: avoid; page-break-after: avoid; font-size: 11.5pt; margin: 5mm 0 2mm; color: #0f172a; }
p { margin: 0 0 2.5mm; }
.page { page-break-before: always; }
.cover { height: 255mm; display: flex; flex-direction: column; justify-content: space-between; padding: 8mm 4mm; }
.brand { display: flex; align-items: center; gap: 4mm; }
.logo { width: 16mm; height: 16mm; border-radius: 4mm; background: linear-gradient(135deg,#0e7490,#6366f1); display:flex; align-items:center; justify-content:center; color:#fff; font-weight:800; font-size: 20pt; }
.cover h1 { font-size: 34pt; line-height: 1.1; margin: 0 0 4mm; }
.cover .sub { font-size: 14pt; color: #475569; max-width: 150mm; }
.meta { display: grid; grid-template-columns: 45mm 1fr; gap: 2mm 6mm; font-size: 10.5pt; }
.meta b { color: #64748b; font-weight: 600; }
.kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 3mm; margin: 4mm 0; }
.kpi { border: 1px solid #e2e8f0; border-radius: 3mm; padding: 3mm; background: #f8fafc; }
.kpi .v { font-size: 16pt; font-weight: 800; color: #0e7490; line-height: 1.1; }
.kpi .l { font-size: 8.5pt; color: #475569; }
table { width: 100%; border-collapse: collapse; margin: 2mm 0 4mm; font-size: 8.6pt; page-break-inside: auto; }
th { background: #0f172a; color: #fff; text-align: left; padding: 1.8mm 2mm; font-weight: 600; }
td { border-bottom: 1px solid #e2e8f0; padding: 1.7mm 2mm; vertical-align: top; }
tr { page-break-inside: avoid; }
tbody tr:nth-child(even) td { background: #f8fafc; }
.pill { display: inline-block; padding: .4mm 2mm; border-radius: 10mm; font-size: 7.6pt; font-weight: 700; white-space: nowrap; }
.ok { background: #dcfce7; color: #166534; } .rev { background: #dbeafe; color: #1e40af; }
.todo { background: #f1f5f9; color: #475569; } .str { background: #f3e8ff; color: #6b21a8; } .doing { background: #fef9c3; color: #854d0e; }
.box { border: 1px solid #e2e8f0; border-left: 4px solid #0e7490; background: #f0f9ff; border-radius: 2mm; padding: 3mm 4mm; margin: 3mm 0; }
.warn { border-left-color: #b45309; background: #fffbeb; }
.two { display: grid; grid-template-columns: 1fr 1fr; gap: 5mm; }
ul { margin: 0 0 3mm; padding-left: 5mm; } li { margin-bottom: 1mm; }
.diagram { width: 100%; height: auto; margin: 2mm 0; }
.gantt { display: grid; font-size: 7.6pt; border: 1px solid #e2e8f0; border-radius: 2mm; overflow: hidden; margin: 3mm 0; }
.gw { background: #0f172a; color: #fff; text-align: center; padding: 1.2mm 0; font-weight: 600; line-height: 1.2; }
.gl { padding: 1mm 2mm; border-top: 1px solid #e2e8f0; line-height: 1.2; }
.gl span { display: block; color: #64748b; font-size: 6.8pt; }
.gh { background: #0f172a; color: #fff; font-weight: 700; display: flex; align-items: center; }
.gc { border-top: 1px solid #e2e8f0; border-left: 1px dashed #eef2f7; }
.g-ai { background: #a5b4fc; } .g-ds { background: #67e8f9; } .g-cy { background: #fda4af; } .g-fs { background: #86efac; }
.g-pm { background: #fcd34d; } .g-ms { background: #0f172a; } .g-str { background: repeating-linear-gradient(45deg,#e9d5ff 0 4px,#f5f3ff 4px 8px); }
.legend { display: flex; gap: 4mm; flex-wrap: wrap; font-size: 8pt; color: #475569; }
.legend i { display: inline-block; width: 4mm; height: 3mm; border-radius: 1mm; vertical-align: -0.3mm; margin-right: 1mm; }
.small { font-size: 8.5pt; color: #475569; }
.toc li { margin-bottom: 1.4mm; }
table.bl th:nth-child(1) { width: 15%; } table.bl th:nth-child(2) { width: 31%; } table.bl th:nth-child(3) { width: 14%; }
table.bl th:nth-child(4) { width: 17%; } table.bl th:nth-child(5) { width: 13%; } table.bl th:nth-child(6) { width: 10%; }
table.bl { font-size: 8.2pt; table-layout: fixed; } table.bl td { overflow-wrap: anywhere; }
code { font-family: 'DejaVu Sans Mono', monospace; font-size: 8.3pt; background: #f1f5f9; padding: 0 1mm; border-radius: 1mm; }
"""

legend = ('<div class="legend"><span><i class="g-ai"></i>AI</span><span><i class="g-ds"></i>Data science</span>'
          '<span><i class="g-cy"></i>Cybersecurity / DevOps</span><span><i class="g-fs"></i>Full stack / UX</span>'
          '<span><i class="g-pm"></i>Writing / management</span><span><i class="g-ms"></i>Milestone</span>'
          '<span><i class="g-str"></i>Stretch</span></div>')

def backlog(rows):
    out = []
    for r in rows:
        status = st("stretch") if r[5] == "stretch" else st("todo")
        ref = "" if r[5] in ("new", "stretch", "—") else f'<br><span class="small">issue {r[5]}</span>'
        out.append([f"<b>{r[0]}</b>{ref}", r[1], r[2], r[3], r[4], status])
    return table(["Task", "How", "Data / tools", "Done when", "Owner", "Status"], out, "bl")

doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Badeel — Project Plan</title><style>{css}</style></head><body>

<section class="cover">
  <div class="brand"><div class="logo">B</div><div><b style="font-size:13pt">Badeel</b><br><span class="small">Graduation project · Egyptian Chinese University</span></div></div>
  <div>
    <h1>Project Plan<br>and Milestones</h1>
    <p class="sub">A secure, bilingual system that finds exact medicine alternatives on the Egyptian market and warns each patient about the risks that apply to them.</p>
    <div class="kpis">
      <div class="kpi"><div class="v">22,757</div><div class="l">Egyptian products, cleaned and linked</div></div>
      <div class="kpi"><div class="v">93.0%</div><div class="l">top-1 search accuracy with spelling mistakes (CV)</div></div>
      <div class="kpi"><div class="v">8</div><div class="l">open data sources linked</div></div>
      <div class="kpi"><div class="v">65 / 65</div><div class="l">simulated attacks blocked</div></div>
    </div>
  </div>
  <div class="meta">
    <b>Supervisor</b><span>Dr. Amira</span>
    <b>Teaching assistant</b><span>Eng. Toqa Hamdy</span>
    <b>Team</b><span>Youssef Ali · Mohamed Ashraf · Bahaa · Abdelrahman · Mohamed Ali · Mohamed Adel · Ziad · Mahmoud Eid · Ahmed Taha · Youssef Awad</span>
    <b>Repository</b><span>github.com/youssefali62011-arch/badeel-project</span>
    <b>Version</b><span>1.0 — 26 November 2026. Status data taken from the repository on this date.</span>
  </div>
</section>

<section class="page">
<h2>Contents</h2>
<ol class="toc">
<li>Executive summary</li><li>The project: problem, objectives, contributions</li><li>System architecture</li>
<li>Where we are: work completed</li><li>Data sources: what, where from, licence</li>
<li>Semester 1 — implementation plan (29 Nov 2026 – 14 Jan 2027)</li>
<li>Evaluation plan: how every claim will be measured</li>
<li>Semester 2 — experiments, thesis, research paper (Feb – Jun 2027)</li>
<li>Milestones and acceptance criteria</li><li>Research paper plan</li><li>Risks, ethics and law</li><li>Ways of working</li>
</ol>

<h2 style="margin-top:8mm">1. Executive summary</h2>
<p>When a medicine is out of stock in Egypt, patients and pharmacists need a product with <b>exactly</b> the same active ingredient, strength and dosage form. Brand names differ, Arabic and English spellings vary, and nothing on the box warns the patient about interactions with their other medicines.</p>
<p>Badeel already solves the core of this. It holds 22,757 Egyptian products linked to 8 open sources. Its exact-alternative engine and spelling-tolerant search work, with 93.0% top-1 accuracy on 18,000 misspelled queries. Each patient gets warnings for interactions, allergies, conditions and look-alike names. Voice search, photo search, reminders and an installable app are built. An automated attack suite blocks all 65 attacks.</p>
<p>This plan splits the remaining work into two semesters:</p>
<ul>
<li><b>Semester 1 (now – 14 Jan 2027): finish the build.</b> Verify the data with a pharmacist, strengthen the AI search, finish the advanced security features, deploy with HTTPS, then freeze features.</li>
<li><b>Semester 2 (Feb – Jun 2027): prove it and write it up.</b> Run the experiments (gold set, real queries, user study), write thesis chapters 2–7, submit a research paper, and allow only small fixes.</li>
</ul>
<div class="box"><b>The rule for both semesters:</b> every feature ships with a test and a number. Accuracy, speed, coverage and attack rate are measured by a script in the repository, so every table in the thesis and the paper can be regenerated.</div>
</section>

<section class="page">
<h2>2. The project</h2>
<h3>Problem</h3>
<ul>
<li>Medicine shortages are frequent in Egypt. Choosing an alternative by hand is slow and error-prone: the same ingredient may come at another strength or form, and salts differ (diclofenac sodium vs potassium).</li>
<li>Patients search with misspelled names, in Arabic letters for English brands ("اوجمنتين"), or in Franco.</li>
<li>Safety information is scattered across international databases that do not use Egyptian brand names.</li>
<li>Health data is sensitive, and Egypt's Personal Data Protection Law (No. 151 of 2020) treats it as sensitive data.</li>
</ul>
<h3>Objectives</h3>
<ol>
<li>Find exact alternatives (same ingredient, strength, form) with precision ≥ 0.98, verified against a pharmacist-reviewed gold set.</li>
<li>Find the intended product despite spelling mistakes in Arabic, English and Franco, and from a photo or voice.</li>
<li>Give each patient warnings that apply to them: interactions, allergies, conditions, pregnancy, look-alike names.</li>
<li>Protect health data by design: encryption, access control, tamper-evident logs, tested against real attacks.</li>
<li>Publish a cleaned, linked Egyptian drug dataset as an open benchmark.</li>
</ol>
<h3>Expected research contributions</h3>
<table><thead><tr><th>#</th><th>Contribution</th><th>Evidence planned</th></tr></thead><tbody>
<tr><td>C1</td><td>An open Egyptian drug dataset linked to RxNorm, DDInter, DrugCentral, openFDA, SIDER and ISMP, with coverage measured per source</td><td>Dataset v2.0 with DOI; coverage tables; EDA cross-check; 100-product audit</td></tr>
<tr><td>C2</td><td>A normalisation method for exact therapeutic equivalence in a noisy national list (salts, units, per-ml strengths, combination totals)</td><td>500-pair gold set: precision, recall, error analysis</td></tr>
<tr><td>C3</td><td>Bilingual, misspelling-tolerant drug search with learned ranking</td><td>Logistic regression vs LightGBM vs TF-IDF on synthetic and real queries; photo and voice benchmarks</td></tr>
<tr><td>C4</td><td>A personalised safety layer and its measured precision</td><td>200 warnings reviewed by a pharmacist; LASA evaluation</td></tr>
<tr><td>C5</td><td>Security by design for a health web app</td><td>Attack suite, ZAP and Burp results; tamper-evident log; blind index</td></tr>
</tbody></table>
</section>

<section class="page">
<h2>3. System architecture</h2>
{arch}
<div class="two">
<div><h3>Technology</h3><ul>
<li>Python 3, Flask (app factory, 7 blueprints), Jinja2, vanilla JavaScript, CSS tokens (dark/light)</li>
<li>SQLite today; PostgreSQL for production (Semester 1)</li>
<li>scikit-learn (ranker), Tesseract OCR, Web Speech API, Web Push (PWA)</li>
<li>gunicorn on Render; PythonAnywhere as a fallback</li>
</ul></div>
<div><h3>Security controls in place</h3><ul>
<li>Strict Content-Security-Policy (no inline script or style), CSRF tokens, rate limits</li>
<li>Strong passwords (≥ 15 characters), role checks on every route</li>
<li>Health data encrypted with Fernet and stored only with consent</li>
<li>Audit log that never names the medicine or condition; security log; trap pages for scanners</li>
</ul></div></div>
</section>

<section class="page">
<h2>4. Where we are: work completed</h2>
<p class="small">Status on 26 Nov 2026, from the main branch, open pull requests and <code>docs/results/</code>.</p>
{table(["Area", "What exists", "Measured result", "Status"], done_rows)}
<div class="box warn"><b>Honest limits to state in the thesis:</b>
<ul>
<li>The 40-pair matching test (100% precision and recall) is too small to claim much. The 500-pair gold set fixes this.</li>
<li>Search accuracy is so far measured on generated misspellings only.</li>
<li>DrugCentral links some ingredients to diseases that come from combination products.</li>
<li>2,308 rows of the source list have no active ingredient and are skipped.</li>
</ul></div>
</section>

<section class="page">
<h2>5. Data sources: what, where from, licence</h2>
{table(["Source", "What we take", "Where from / how", "Status", "Licence"], sources)}
<h3>How the data is joined</h3>
<p>Each source names ingredients its own way. Badeel converts every name to one <b>moiety key</b>: lower case, synonyms unified, salt words removed for matching. The key is then extended with the official <b>RxNorm</b> name (paracetamol → acetaminophen). A source row is kept only when its ingredient is sold in Egypt, which keeps the database small and fast.</p>
<p>The whole pipeline runs with <code>python manage.py collect-data</code>. Every run writes the date and licence of each source to <code>data/raw/…/SOURCE.json</code> and prints a coverage report, so the numbers in this document can be reproduced.</p>
</section>

<section class="page">
<h2>6. Semester 1 — implementation plan</h2>
<p><b>Window:</b> 29 November 2026 – 14 January 2027 (7 weeks), then exams. <b>Goal:</b> a complete, verified and secured system, frozen and deployed by <b>14 January</b>.</p>
{gantt("Semester 1", s1_weeks, s1_rows)}
{legend}
<h3>6.1 AI track — Mohamed Ashraf</h3>
{backlog(ai_rows)}
</section>

<section class="page">
<h3>6.2 Data science track — Bahaa, Abdelrahman, Mohamed Ali</h3>
{backlog(ds_rows)}
<h3>6.3 Full stack and user experience — Eng. Toqa, Youssef Ali</h3>
{backlog(fs_rows)}
</section>

<section class="page">
<h3>6.4 Cybersecurity and DevOps track — Youssef Ali, Mohamed Adel, Ziad, Mahmoud Eid, Ahmed Taha, Youssef Awad</h3>
{backlog(cy_rows)}
<h3>6.5 Supervisor and management</h3>
<ul>
<li>Dr. Amira's approval to launch the public site (issue #16), with weekly follow-up of the team.</li>
<li><b>Ethics approval</b> for the user study and the dictation study, requested before the January exams so that Semester 2 starts on time. Consent forms in Arabic; no names stored with the answers.</li>
<li>Book a pharmacist (Faculty of Pharmacy) for the gold set and the warning review: about 6 hours in total, split into short sessions.</li>
</ul>
<div class="box"><b>Feature freeze on 14 January 2027.</b> After this date only bug fixes, text and accessibility changes go in. Anything unfinished moves to "future work" in the thesis, and stretch items are cut first.</div>
</section>

<section class="page">
<h2>7. Evaluation plan</h2>
<p>Each claim in the thesis and the paper is tied to one experiment, one dataset and one script.</p>
{table(["What", "Test data", "Metrics", "Target / status"], eval_rows)}
<h3>How the new test data is built</h3>
<ul>
<li><b>Gold set (500 pairs).</b> Stratified by single vs combination products, dosage form, and "near misses" (same ingredient, different strength or salt). A pharmacist labels each pair "exact alternative" or "not". 100 pairs are labelled twice to report agreement (Cohen's κ).</li>
<li><b>Dictation study (real queries).</b> Volunteers hear or see 40 drug names each (audio, box photo, handwritten note) and type what they would search. 30 volunteers × 40 names = 1,200 real queries in Arabic, English and Franco. No personal data is kept.</li>
<li><b>Photo set.</b> 200 boxes photographed by the team in normal light, at two angles, with phones of different quality.</li>
<li><b>User study.</b> Five tasks (find an alternative, save a medicine, read a warning, set a reminder, use voice search), then the System Usability Scale. Three groups: patients, pharmacists, adults over 60.</li>
<li><b>Statistics.</b> 95% confidence intervals for proportions; McNemar's test when two models answer the same queries; mean ± standard deviation across cross-validation folds.</li>
</ul>
</section>

<section class="page">
<h2>8. Semester 2 — experiments, thesis, research paper</h2>
<p><b>Window:</b> about 7 February – 26 June 2027 (20 weeks; adjust to the official ECU calendar). Ramadan falls around 8 February – 9 March 2027, so the first weeks are for experiments that need little coding. <b>No new features</b>: only fixes and polish.</p>
{gantt("Semester 2", s2_weeks, s2_rows)}
{legend}
<div class="two">
<div><h3>Phase A · W1–W5 · Experiments</h3><ul>
<li>Run every benchmark from §7 on the frozen v1.0</li>
<li>User study and dictation study (ethics approved in January)</li>
<li>Pharmacist reviews the 200 warnings and finishes the gold set</li>
<li>Release dataset v2.0 on Zenodo with a DOI</li></ul>
<h3>Phase B · W3–W10 · Thesis chapters 2–5</h3><ul>
<li>Literature review with a comparison table of 10–15 works</li>
<li>Requirements, design and implementation, using the diagrams and code in the repository</li></ul></div>
<div><h3>Phase C · W9–W14 · Evaluation + paper</h3><ul>
<li>Chapter 6 from the experiment outputs; chapter 7</li>
<li>Paper A drafted from chapters 4–6, reviewed by the supervisor, submitted in W14</li></ul>
<h3>Phase D · W13–W20 · Finish</h3><ul>
<li>Full thesis review; fix comments</li>
<li>Poster, 3-minute demo video, slides</li>
<li>Two full rehearsals with questions</li>
<li>Defense, with a local copy of the site in case the internet fails</li></ul></div>
</div>
<h3>Thesis structure</h3>
{table(["Ch.", "Title", "Content", "Status"], thesis)}
</section>

<section class="page">
<h2>9. Milestones and acceptance criteria</h2>
<p>A milestone is reached only when its evidence exists in the repository or on GitHub.</p>
{table(["#", "Date", "Milestone", "Evidence (done when)"], milestones)}
<h3>Weekly rhythm</h3>
<ul>
<li><b>Sunday:</b> 30-minute stand-up per track. Each person says what they finished, what is next and what blocks them. Update the GitHub issue.</li>
<li><b>Thursday:</b> pull requests reviewed and merged. Nothing is merged without passing tests and the attack suite.</li>
<li><b>Every two weeks:</b> a short demo and progress report to the supervisor, using this table.</li>
</ul>
</section>

<section class="page">
<h2>10. Research paper plan</h2>
<h3>Paper A — main paper</h3>
<p><b>Working title:</b> <i>Badeel: Exact Medicine Alternatives with Bilingual Misspelling-Tolerant Search and Personalised Safety Warnings for the Egyptian Market.</i> The final title follows the final product name.</p>
<p><b>Research questions</b></p>
<ol>
<li>RQ1. How accurately can rule-based normalisation identify exact alternatives in a noisy national drug list? (C2)</li>
<li>RQ2. How much does learned ranking improve bilingual misspelled search over a TF-IDF baseline, and how does LightGBM compare? Do results on generated queries hold for real ones? (C3)</li>
<li>RQ3. What coverage and precision do open international sources reach when linked to Egyptian products? (C1, C4)</li>
<li>RQ4. Is the system usable by patients, pharmacists and older adults? (SUS)</li>
</ol>
<p><b>Structure (IMRaD, 8–10 pages):</b> introduction, related work, data, method (normalisation, ranking, safety layer), experiments, results, discussion and limitations, conclusion.</p>
<p><b>Candidate venues</b> (check each call for papers and deadline in January):</p>
<ul>
<li>Journals with rolling submission: <i>JMIR Formative Research</i>; <i>BMC Medical Informatics and Decision Making</i>.</li>
<li>IEEE conferences held in Egypt, for example NILES, ITC-Egypt and MIUCC.</li>
</ul>
<h3>Paper B — dataset paper (optional)</h3>
<p>The linked Egyptian dataset (C1), submitted to <i>Data in Brief</i>, with the Zenodo DOI. It reuses chapter 5 and the coverage tables.</p>
<h3>Paper C — security (optional)</h3>
<p>A short paper on security by design for a health web app (C5): the attack suite, the tamper-evident log, blind-index allergy checks, and bot detection with a honeypot.</p>
<div class="box"><b>Writing rules:</b>
<ul>
<li>Every number in the paper comes from a script in <code>checks/</code>, <code>ml/</code> or <code>manage.py</code>.</li>
<li>Tables are generated, not typed.</li>
<li>Limitations are stated plainly: generated queries, DrugCentral noise, SIDER age, the U.S. origin of the ISMP list.</li>
</ul></div>
</section>

<section class="page">
<h2>11. Risks, ethics and law</h2>
{table(["Risk", "Impact", "What we do"], risks)}
<h3>Ethics</h3>
<ul>
<li>Badeel gives information, not prescriptions. There is no dose calculator, and a ticked danger sign stops all suggestions.</li>
<li>Studies with people need university ethics approval, written consent, and anonymous answers.</li>
<li>Health data is stored only with consent, encrypted, and can be deleted by the user.</li>
</ul>
<h3>Licences</h3>
<ul>
<li>Each dataset file carries the licence of its source.</li>
<li>DDInter (non-commercial) and the share-alike sources (DrugCentral, SIDER) limit how the data can be reused. This is stated in the dataset card and the paper.</li>
</ul>

<h2 style="margin-top:6mm">12. Ways of working</h2>
<ul>
<li><b>One task, one GitHub issue.</b> Each issue has an owner, a "done when" line from this plan, and a link to its pull request.</li>
<li><b>Branches and pull requests</b> for every change. A pull request is merged only when <code>python -m unittest</code> and <code>checks/security_check.py</code> pass.</li>
<li><b>Results files</b> go in <code>docs/results/</code>. They are the source for the thesis and the paper.</li>
<li><b>Data changes</b> run through <code>manage.py</code> commands, so the database can be rebuilt from scratch.</li>
<li><b>This plan</b> is updated at every milestone: statuses, dates, and anything moved to future work.</li>
</ul>
</section>
</body></html>"""
open(__import__("os").path.join(__import__("os").path.dirname(__import__("os").path.abspath(__file__)), "Badeel_Project_Plan.html"), "w", encoding="utf-8").write(doc)
print("ok")
