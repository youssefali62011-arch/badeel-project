"""Pages anyone can open: home, search, drug page, ingredient page, about."""
from flask import (Blueprint, abort, flash, g, jsonify, redirect, render_template, request,
                   session, url_for)

from .. import db, security
from ..services import conditions, interactions, labels, lasa, ocr, recommender, side_effects, symptoms, search as search_service
from ..services.normalize import canon_ingredient, display_name

bp = Blueprint("public", __name__)


def _fetch_in_order(ids):
    if not ids:
        return []
    marks = ",".join("?" for _ in ids)
    rows = db.query(
        f"SELECT d.*, (SELECT COUNT(*) FROM drugs x WHERE x.composition_key = d.composition_key "
        f"AND x.form = d.form AND x.id != d.id AND d.strength_known = 1) AS alt_count "
        f"FROM drugs d WHERE d.id IN ({marks})", ids)
    by_id = {r["id"]: r for r in rows}
    return [by_id[i] for i in ids if i in by_id]


def user_allergies():
    if not g.user:
        return set()
    text = security.decrypt(g.user["allergies_enc"])
    return {canon_ingredient(a) for a in text.replace("،", ",").split(",") if a.strip()}


@bp.route("/")
def home():
    stats = db.one("SELECT (SELECT COUNT(*) FROM drugs) AS drugs, "
                   "(SELECT COUNT(*) FROM ingredients) AS ingredients")
    # A real match from the database, shown as a worked example on the home page.
    example = []
    group = db.one(
        "SELECT composition_key, form FROM drugs WHERE strength_known = 1 AND price IS NOT NULL "
        "GROUP BY composition_key, form HAVING COUNT(*) > 1 ORDER BY COUNT(*) DESC, "
        "composition_key LIMIT 1")
    if group:
        example = db.query(
            "SELECT * FROM drugs WHERE composition_key = ? AND form = ? ORDER BY price DESC LIMIT 3",
            (group["composition_key"], group["form"]))
    return render_template("home.html", stats=stats, example=example)


@bp.route("/search")
def search():
    q = request.args.get("q", "").strip()[:100]
    results = []
    if q:
        results = _fetch_in_order([i for i, _ in search_service.search(q, limit=30)])
        if g.user:
            last = db.one("SELECT query FROM search_history WHERE user_id = ? "
                          "ORDER BY id DESC LIMIT 1", (g.user["id"],))
            if not last or last["query"] != q:
                db.execute("INSERT INTO search_history (user_id, query, created_at) "
                           "VALUES (?, ?, ?)", (g.user["id"], q, db.now()))
                db.commit()
    return render_template("search.html", q=q, results=results)


def _tr(en, ar):
    return ar if g.get("lang", "ar") == "ar" else en


PHOTO_ERRORS = {
    "empty": ("Choose or take a photo first.", "اختار صورة أو صوّر العلبة الأول."),
    "too_large": ("The photo is larger than 8 MB.", "الصورة أكبر من 8 ميجا."),
    "not_image": ("This file is not a photo (JPG, PNG or WEBP).", "الملف ده مش صورة (JPG أو PNG أو WEBP)."),
    "timeout": ("Reading the photo took too long. Try a closer, clearer photo.",
                "قراءة الصورة أخدت وقت طويل. جرّب صورة أقرب وأوضح."),
}


@bp.route("/photo-search", methods=["POST"])
def photo_search():
    """Search by a photo of the medicine box (text read on the server, photo not kept)."""
    if not ocr.available():
        flash(_tr("Search by photo is not available on this server.", "البحث بالصورة مش متاح على السيرفر ده."), "error")
        return redirect(url_for("public.home"))
    if not ocr.allowed(security.client_ip()):
        flash(_tr("Too many photos in a short time. Wait a few minutes.", "صور كتير في وقت قصير. استنى كام دقيقة."), "error")
        return redirect(url_for("public.home"))
    f = request.files.get("photo")
    data = f.read(ocr.MAX_BYTES + 1) if f else b""
    try:
        text = ocr.read_text(data)
    except ocr.PhotoError as e:
        flash(_tr(*PHOTO_ERRORS[str(e)]), "error")
        return redirect(url_for("public.home"))
    best, others = ocr.best_match(text, lambda q, n: search_service.search(q, limit=n))
    if not best:
        flash(_tr("No medicine name could be read. Take the photo closer, in good light, with the name facing the camera.",
                  "مقدرناش نقرا اسم دوا. صوّر العلبة من قريب، في نور كويس، والاسم قدام الكاميرا."), "error")
        return redirect(url_for("public.home"))
    results = _fetch_in_order([i for i, _ in search_service.search(best, limit=30)])
    return render_template("search.html", q=best, results=results, from_photo=True, photo_others=others)


@bp.route("/api/suggest")
def suggest():
    """Autocomplete for the search box (called by static/js/app.js)."""
    q = request.args.get("q", "").strip()[:60]
    rows = _fetch_in_order([i for i, _ in search_service.search(q, limit=7)]) if len(q) >= 2 else []
    return jsonify([{
        "url": url_for("public.drug", drug_id=r["id"]),
        "name": r["trade_name"], "name_ar": r["trade_name_ar"] or "",
        "detail": " ".join(filter(None, [r["ingredients_display"], r["strength_display"]])),
    } for r in rows])


@bp.route("/drug/<int:drug_id>")
def drug(drug_id):
    d = db.one("SELECT * FROM drugs WHERE id = ?", (drug_id,))
    if not d:
        abort(404)
    alternatives = recommender.get_alternatives(d)
    ingredients = db.query(
        "SELECT i.id, i.name, di.strength_text FROM drug_ingredients di "
        "JOIN ingredients i ON i.id = di.ingredient_id WHERE di.drug_id = ? ORDER BY i.name",
        (drug_id,))
    allergy_hits = sorted(user_allergies() & set(d["ingredient_key"].split("|")))
    is_favorite = bool(g.user and db.one(
        "SELECT 1 FROM favorites WHERE user_id = ? AND drug_id = ?", (g.user["id"], drug_id)))
    saved_interactions = interactions.with_saved_medicines(d, g.user["id"]) if g.user else []
    disease = conditions.for_drug(d)
    condition_warnings = conditions.warnings_for(d, conditions.user_groups(g.user))
    return render_template(
        "drug.html", d=d, alt=alternatives, ingredients=ingredients,
        allergy_hits=[display_name(a) for a in allergy_hits], is_favorite=is_favorite,
        display_name=display_name, leaflet=labels.for_drug(d),
        leaflet_sections=labels.SECTION_LABELS, saved_interactions=saved_interactions,
        interaction_count=interactions.count_for(d), severity_labels=interactions.SEVERITY_LABELS,
        disease=disease, condition_warnings=condition_warnings,
        lasa_pairs=lasa.for_drug(d), side_effects=side_effects.for_drug(d),
        concept_group=conditions.CONCEPT_TO_GROUP)


@bp.route("/ingredient/<int:ingredient_id>")
def ingredient(ingredient_id):
    ing = db.one("SELECT * FROM ingredients WHERE id = ?", (ingredient_id,))
    if not ing:
        abort(404)
    drugs = db.query(
        "SELECT d.* FROM drugs d JOIN drug_ingredients di ON di.drug_id = d.id "
        "WHERE di.ingredient_id = ? ORDER BY d.form, d.strength_display, d.price IS NULL, d.price",
        (ingredient_id,))
    return render_template("ingredient.html", name=display_name(ing["name"]), drugs=drugs)


@bp.route("/disease")
def disease():
    """Products whose ingredients are listed as treating a disease."""
    group = conditions.GROUPS.get(request.args.get("group", ""))
    name = request.args.get("name", "").strip()[:200]
    if group:
        concepts, title = group["concepts"], (group["en"], group["ar"])
    elif name:
        concepts, title = [name], (name, name)
    else:
        abort(404)
    ingredients, products = conditions.products_treating(concepts)
    return render_template("disease.html", title=title, concepts=concepts, group=group,
                           ingredients=[display_name(i) for i in ingredients], drugs=products)


@bp.route("/symptoms")
def symptom_explorer():
    """What could help with these symptoms? Information to take to a pharmacist or doctor."""
    picked = [k for k in request.args.getlist("s") if k in symptoms.SYMPTOMS][:6]
    flags = symptoms.red_flags_ticked(request.args.getlist("rf"))
    asked = bool(picked or flags)
    results = [] if flags else symptoms.explore(
        picked, user=g.user, pregnant=request.args.get("pregnant") == "1",
        breastfeeding=request.args.get("breastfeeding") == "1", child=request.args.get("child") == "1")
    return render_template("symptoms.html", symptoms=symptoms.SYMPTOMS, areas=symptoms.AREAS,
                           red_flags=symptoms.RED_FLAGS, picked=set(picked), flags=flags, asked=asked,
                           results=results, args=request.args, display_name=display_name)


@bp.route("/about")
def about():
    return render_template("about.html")


@bp.route("/lang/<code>")
def set_lang(code):
    if code in ("ar", "en"):
        session["lang"] = code
    return redirect(security.safe_next(request.args.get("next")) or url_for("public.home"))
