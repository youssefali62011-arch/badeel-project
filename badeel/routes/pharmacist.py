"""Pharmacist tools: report shortages and update prices from the counter."""
from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from .. import db, security

bp = Blueprint("pharmacist", __name__)


def tr(en, ar):
    return ar if g.lang == "ar" else en


@bp.route("/pharmacist")
@security.role_required("pharmacist", "admin")
def dashboard():
    shortages = db.query(
        "SELECT d.*, (SELECT COUNT(*) FROM drugs x WHERE x.composition_key = d.composition_key "
        "AND x.form = d.form AND x.id != d.id AND x.availability != 'shortage' "
        "AND d.strength_known = 1) AS alt_count "
        "FROM drugs d WHERE d.availability = 'shortage' ORDER BY d.updated_at DESC LIMIT 200")
    stats = db.one(
        "SELECT (SELECT COUNT(*) FROM drugs) AS products,"
        " (SELECT COUNT(*) FROM drugs WHERE availability = 'shortage') AS shortages,"
        " (SELECT COUNT(*) FROM drugs WHERE availability = 'available') AS available,"
        " (SELECT COUNT(*) FROM audit_log WHERE user_id = ? AND action = 'drug_status'"
        "  AND created_at > ?) AS mine_today",
        (g.user["id"], db.now(-24 * 60)))
    no_alternative = sum(1 for d in shortages if not d["alt_count"])
    return render_template("pharmacist/dashboard.html", shortages=shortages, stats=stats,
                           no_alternative=no_alternative)


@bp.route("/drug/<int:drug_id>/status", methods=["POST"])
@security.role_required("pharmacist", "admin")
def update_status(drug_id):
    d = db.one("SELECT * FROM drugs WHERE id = ?", (drug_id,))
    if not d:
        abort(404)
    availability = request.form.get("availability")
    price_text = request.form.get("price", "").strip()
    if availability not in ("available", "shortage", "unknown"):
        abort(400)
    try:
        price = float(price_text) if price_text else None
        if price is not None and not 0 <= price < 1_000_000:
            raise ValueError
    except ValueError:
        flash(tr("Price must be a positive number.", "السعر يجب أن يكون رقمًا موجبًا."), "error")
        return redirect(url_for("public.drug", drug_id=drug_id))

    db.execute("UPDATE drugs SET availability = ?, price = ?, updated_at = ? WHERE id = ?",
               (availability, price, db.now(), drug_id))
    security.audit("drug_status",
                   f"{d['trade_name']} (#{drug_id}): {d['availability']} -> {availability}, "
                   f"price {d['price']} -> {price}")
    db.commit()
    flash(tr("Availability and price updated.", "تم تحديث التوافر والسعر."), "success")
    return redirect(url_for("public.drug", drug_id=drug_id))


@bp.route("/pharmacist/combinations")
@security.role_required("pharmacist", "admin")
def combinations():
    """Strength splits proposed from RxNorm for combination products: approve or reject."""
    import json
    rows = db.query("SELECT s.*, d.trade_name, d.trade_name_ar, d.ingredients_display, d.form FROM combo_suggestions s "
                    "JOIN drugs d ON d.id = s.drug_id WHERE s.status = 'pending' ORDER BY d.trade_name LIMIT 200")
    items = [{"s": r, "parts": json.loads(r["proposal"])} for r in rows]
    done = db.one("SELECT SUM(status = 'approved') AS approved, SUM(status = 'rejected') AS rejected, "
                  "SUM(status = 'pending') AS pending FROM combo_suggestions")
    return render_template("pharmacist/combinations.html", items=items, done=done)


@bp.route("/pharmacist/combinations/<int:suggestion_id>", methods=["POST"])
@security.role_required("pharmacist", "admin")
def review_combination(suggestion_id):
    from ..services import rxnorm
    if request.form.get("decision") == "approve":
        ok = rxnorm.approve(suggestion_id, g.user["id"])
        security.audit("combination_approved", f"suggestion {suggestion_id}")
        flash(tr("Strengths saved: the product can now get exact alternatives.",
                 "اتحفظت التركيزات: الدواء بقى ممكن يكون له بدائل مطابقة.") if ok else
              tr("This proposal no longer fits the product.", "الاقتراح ده مبقاش مناسب للدواء."), "success" if ok else "error")
    else:
        rxnorm.reject(suggestion_id, g.user["id"])
        security.audit("combination_rejected", f"suggestion {suggestion_id}")
    db.commit()
    return redirect(url_for("pharmacist.combinations"))
