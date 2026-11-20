-- Badeel database schema.
-- Written in plain SQL that works on SQLite (used now) and needs only small
-- changes for PostgreSQL (AUTOINCREMENT -> SERIAL / IDENTITY).

CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL,
    email           TEXT    NOT NULL UNIQUE,
    password_hash   TEXT    NOT NULL,                 -- never the password itself
    role            TEXT    NOT NULL DEFAULT 'patient'
                    CHECK (role IN ('patient', 'pharmacist', 'admin')),
    status          TEXT    NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active', 'pending', 'disabled')),
    allergies_enc   TEXT,                             -- encrypted (Fernet/AES)
    conditions_enc  TEXT,                             -- encrypted list of condition groups
    consent_at      TEXT,                             -- explicit consent for health data
    failed_logins   INTEGER NOT NULL DEFAULT 0,
    locked_until    TEXT,
    created_at      TEXT    NOT NULL
);

-- One row per active ingredient (scientific name), e.g. "paracetamol".
CREATE TABLE IF NOT EXISTS ingredients (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT NOT NULL UNIQUE
);

-- One row per product on the shelf, e.g. "Panadol 500 mg tablets".
CREATE TABLE IF NOT EXISTS drugs (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_name          TEXT NOT NULL,
    trade_name_ar       TEXT,
    ingredients_display TEXT NOT NULL,   -- "Amoxicillin + Clavulanic acid"
    strength_display    TEXT,            -- "875 mg + 125 mg"
    form                TEXT NOT NULL,   -- normalised: tablet, syrup, ...
    form_raw            TEXT,            -- as typed in the source data
    company             TEXT,
    price               REAL CHECK (price IS NULL OR price >= 0),
    pack_count          INTEGER,         -- units in the pack (20 tablets), if known
    drug_class          TEXT,
    country             TEXT,
    availability        TEXT NOT NULL DEFAULT 'unknown'
                        CHECK (availability IN ('available', 'shortage', 'unknown')),
    -- The two keys below are what the recommendation engine compares.
    ingredient_key      TEXT NOT NULL,   -- "amoxicillin|clavulanic acid"
    composition_key     TEXT NOT NULL,   -- "amoxicillin:875mg|clavulanic acid:125mg"
    strength_known      INTEGER NOT NULL DEFAULT 1,
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_drugs_composition ON drugs (composition_key, form);
CREATE INDEX IF NOT EXISTS idx_drugs_ingredient  ON drugs (ingredient_key);
CREATE INDEX IF NOT EXISTS idx_drugs_class       ON drugs (drug_class);

-- Many-to-many: a drug can contain several ingredients, each with a strength.
CREATE TABLE IF NOT EXISTS drug_ingredients (
    drug_id         INTEGER NOT NULL REFERENCES drugs(id) ON DELETE CASCADE,
    ingredient_id   INTEGER NOT NULL REFERENCES ingredients(id),
    strength_value  REAL,
    strength_unit   TEXT,
    strength_text   TEXT,
    PRIMARY KEY (drug_id, ingredient_id)
);
CREATE INDEX IF NOT EXISTS idx_di_ingredient ON drug_ingredients (ingredient_id);

CREATE TABLE IF NOT EXISTS favorites (
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    drug_id     INTEGER NOT NULL REFERENCES drugs(id) ON DELETE CASCADE,
    created_at  TEXT NOT NULL,
    PRIMARY KEY (user_id, drug_id)
);

CREATE TABLE IF NOT EXISTS search_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    query       TEXT NOT NULL,
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_history_user ON search_history (user_id, created_at);

-- Failed logins, honeypot hits, blocked requests ...
CREATE TABLE IF NOT EXISTS security_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    type        TEXT NOT NULL,
    ip          TEXT,
    path        TEXT,
    user_agent  TEXT,
    detail      TEXT,
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_time ON security_events (created_at);
CREATE INDEX IF NOT EXISTS idx_events_ip   ON security_events (ip, type, created_at);

-- Who changed what (admin and pharmacist actions).
CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action      TEXT NOT NULL,
    detail      TEXT,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key     TEXT PRIMARY KEY,
    value   TEXT
);

-- ------------------------------------------------------------------------
-- Data added from outside sources (python manage.py collect-data).
-- Ingredients are stored as "moiety" names (normalize.moiety_key) so the
-- rows stay valid when the drug list is re-imported.

-- Drug-drug interactions, one row per pair (ingredient_a < ingredient_b).
CREATE TABLE IF NOT EXISTS drug_interactions (
    ingredient_a    TEXT NOT NULL,
    ingredient_b    TEXT NOT NULL,
    severity        TEXT NOT NULL CHECK (severity IN ('major', 'moderate', 'minor', 'unknown')),
    source          TEXT NOT NULL,
    PRIMARY KEY (ingredient_a, ingredient_b)
);
CREATE INDEX IF NOT EXISTS idx_interactions_b ON drug_interactions (ingredient_b);

-- One package leaflet per set of ingredients (from openFDA drug labels).
CREATE TABLE IF NOT EXISTS ingredient_labels (
    ingredient_key      TEXT PRIMARY KEY,    -- moiety names sorted, joined by "|"
    source              TEXT NOT NULL,
    label_id            TEXT,
    set_id              TEXT,                -- opens the leaflet on DailyMed
    effective_date      TEXT,
    brand_name          TEXT,
    indications         TEXT,
    dosage              TEXT,
    pediatric           TEXT,
    geriatric           TEXT,
    pregnancy           TEXT,
    lactation           TEXT,
    contraindications   TEXT,
    warnings            TEXT,
    boxed_warning       TEXT,
    pediatric_note      TEXT,                -- 'not_established' | 'min_age' | NULL
    min_age_months      INTEGER
);

-- Diseases an ingredient treats or must not be used with (DrugCentral).
CREATE TABLE IF NOT EXISTS ingredient_conditions (
    ingredient  TEXT NOT NULL,          -- moiety name
    condition   TEXT NOT NULL,          -- DrugCentral concept name, e.g. "Peptic ulcer"
    relation    TEXT NOT NULL CHECK (relation IN ('indication', 'contraindication', 'off_label')),
    umls_cui    TEXT,
    source      TEXT NOT NULL,
    PRIMARY KEY (ingredient, condition, relation)
);
CREATE INDEX IF NOT EXISTS idx_conditions_condition ON ingredient_conditions (condition, relation);

-- Medicine reminders: the patient's own schedule for a saved medicine.
-- Times are UTC text, like every other time in this database.
CREATE TABLE IF NOT EXISTS reminders (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    drug_id             INTEGER NOT NULL REFERENCES drugs(id) ON DELETE CASCADE,
    every_hours         INTEGER NOT NULL CHECK (every_hours IN (6, 8, 12, 24)),
    first_dose_at       TEXT NOT NULL,
    units_per_dose      REAL NOT NULL DEFAULT 1 CHECK (units_per_dose > 0 AND units_per_dose <= 10),
    units_in_box        INTEGER CHECK (units_in_box IS NULL OR units_in_box > 0),
    box_started_at      TEXT,
    active              INTEGER NOT NULL DEFAULT 1,
    last_dose_notified  TEXT,
    refill_notified_at  TEXT,
    created_at          TEXT NOT NULL,
    UNIQUE (user_id, drug_id)
);
CREATE INDEX IF NOT EXISTS idx_reminders_active ON reminders (active);

-- Browsers that may receive notifications (Web Push subscriptions).
CREATE TABLE IF NOT EXISTS push_subscriptions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    endpoint    TEXT NOT NULL UNIQUE,
    p256dh      TEXT NOT NULL,
    auth        TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

-- Look-alike / sound-alike names (ISMP list, and pairs found in the drug list itself).
CREATE TABLE IF NOT EXISTS lasa_pairs (
    name_a      TEXT NOT NULL,          -- lower-case name as written in the source
    name_b      TEXT NOT NULL,
    source      TEXT NOT NULL,          -- 'ISMP' or 'Badeel'
    PRIMARY KEY (name_a, name_b, source)
);
CREATE INDEX IF NOT EXISTS idx_lasa_b ON lasa_pairs (name_b);

-- Side effects with their frequency in clinical trials (SIDER 4.1).
CREATE TABLE IF NOT EXISTS ingredient_side_effects (
    ingredient  TEXT NOT NULL,          -- moiety name
    effect      TEXT NOT NULL,          -- MedDRA preferred term
    freq_lower  REAL,                   -- 0..1, NULL when only "reported"
    freq_upper  REAL,
    source      TEXT NOT NULL,
    PRIMARY KEY (ingredient, effect)
);

-- Ingredient names matched to RxNorm (official name and RxCUI).
CREATE TABLE IF NOT EXISTS ingredient_rxnorm (
    ingredient  TEXT PRIMARY KEY,       -- moiety name in Badeel
    rxcui       TEXT,
    rx_name     TEXT,                   -- RxNorm ingredient name, NULL when not found
    checked_at  TEXT NOT NULL
);

-- Strength splits proposed for combination products, waiting for a pharmacist.
CREATE TABLE IF NOT EXISTS combo_suggestions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    drug_id     INTEGER NOT NULL REFERENCES drugs(id) ON DELETE CASCADE,
    proposal    TEXT NOT NULL,          -- JSON: [{"ingredient": ..., "value": 875, "unit": "mg"}, ...]
    evidence    TEXT,                   -- the RxNorm product it was taken from
    status      TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    reviewed_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at TEXT,
    created_at  TEXT NOT NULL,
    UNIQUE (drug_id, proposal)
);

-- Ingredients of products on the EDA's list of medicines sold without a prescription.
CREATE TABLE IF NOT EXISTS otc_ingredients (
    ingredient  TEXT PRIMARY KEY,       -- moiety name
    source      TEXT NOT NULL
);
