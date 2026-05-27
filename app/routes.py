"""
Smart HORECA AI — Flask Routes
Uses only: Flask + built-in sqlite3 + werkzeug (already in Flask)
No flask-login, no flask-sqlalchemy required.
"""

import os, json, functools
import numpy as np
import joblib
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, jsonify, session)
from werkzeug.security import generate_password_hash, check_password_hash
from app.db import query, execute

main = Blueprint("main", __name__)

# ── Load Models ───────────────────────────────────────────────────────────────
BASE    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MDL_DIR = os.path.join(BASE, "models")

def _load(n): return joblib.load(os.path.join(MDL_DIR, n))

demand_model   = _load("demand_model.pkl");   demand_scaler   = _load("demand_scaler.pkl")
wastage_model  = _load("wastage_model.pkl");  wastage_scaler  = _load("wastage_scaler.pkl")
quantity_model = _load("quantity_model.pkl"); quantity_scaler = _load("quantity_scaler.pkl")
le_service = _load("le_Service_Type.pkl")
le_day     = _load("le_Day_Type.pkl")
le_meal    = _load("le_Meal_Time.pkl")

with open(os.path.join(MDL_DIR, "stats.json")) as f:
    STATS = json.load(f)

# ── Auth helpers ──────────────────────────────────────────────────────────────

def login_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "error")
            return redirect(url_for("main.login"))
        return f(*args, **kwargs)
    return decorated

def get_current_user():
    if "user_id" not in session:
        return None
    return query("SELECT * FROM users WHERE id=?", (session["user_id"],), one=True)

@main.context_processor
def inject_user():
    return {"current_user": get_current_user()}

# ── Prediction helper ─────────────────────────────────────────────────────────

def predict_all(d):
    checkout = float(d["checkout_price"])
    base     = float(d["base_price"])
    row = [
        float(d.get("week", 75)),
        float(d.get("center_id", 55)),
        float(d.get("meal_id", 1885)),
        checkout, base,
        int(d.get("emailer_for_promotion", 0)),
        int(d.get("homepage_featured", 0)),
        float(d["Customers_Count"]),
        int(le_service.transform([d["Service_Type"]])[0]),
        int(le_day.transform([d["Day_Type"]])[0]),
        int(le_meal.transform([d["Meal_Time"]])[0]),
        base - checkout,
        (base - checkout) / (base + 1e-5),
    ]
    X = np.array(row).reshape(1, -1)
    demand   = max(0, float(demand_model.predict(demand_scaler.transform(X))[0]))
    wastage  = max(0, float(wastage_model.predict(wastage_scaler.transform(X))[0]))
    quantity = max(0, float(quantity_model.predict(quantity_scaler.transform(X))[0]))
    wp = (wastage / (quantity + 1e-5)) * 100
    alert = "HIGH" if wp > 30 else ("MEDIUM" if wp > 15 else "LOW")
    return round(demand,2), round(wastage,2), round(quantity,2), round(wp,1), alert

# ── Routes ────────────────────────────────────────────────────────────────────

@main.route("/")
def index():
    if session.get("user_id"):
        return redirect(url_for("main.dashboard"))
    return redirect(url_for("main.login"))

@main.route("/login", methods=["GET","POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        email = request.form.get("email","").strip()
        pw    = request.form.get("password","")
        u = query("SELECT * FROM users WHERE email=?", (email,), one=True)
        if u and check_password_hash(u["password"], pw):
            session["user_id"] = u["id"]
            return redirect(url_for("main.dashboard"))
        flash("Invalid email or password.", "error")
    return render_template("login.html")

@main.route("/register", methods=["GET","POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        name  = request.form.get("name","").strip()
        email = request.form.get("email","").strip()
        pw    = request.form.get("password","")
        if query("SELECT id FROM users WHERE email=?", (email,), one=True):
            flash("Email already registered.", "error")
        else:
            cnt  = query("SELECT COUNT(*) as c FROM users", one=True)["c"]
            role = "admin" if cnt == 0 else "staff"
            uid  = execute(
                "INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)",
                (name, email, generate_password_hash(pw), role)
            )
            session["user_id"] = uid
            return redirect(url_for("main.dashboard"))
    return render_template("register.html")

@main.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("main.login"))

@main.route("/dashboard")
@login_required
def dashboard():
    uid = session["user_id"]
    total_preds = query("SELECT COUNT(*) as c FROM predictions WHERE user_id=?", (uid,), one=True)["c"]
    high_alerts = query("SELECT COUNT(*) as c FROM predictions WHERE user_id=? AND alert='HIGH'", (uid,), one=True)["c"]
    recent      = query("SELECT * FROM predictions WHERE user_id=? ORDER BY created_at DESC LIMIT 5", (uid,))
    avg_waste   = query("SELECT AVG(pred_wastage) as v FROM predictions WHERE user_id=?", (uid,), one=True)["v"] or 0
    avg_demand  = query("SELECT AVG(pred_demand)  as v FROM predictions WHERE user_id=?", (uid,), one=True)["v"] or 0
    return render_template("dashboard.html",
        total_preds=total_preds, high_alerts=high_alerts, recent=recent,
        avg_waste=round(avg_waste,1), avg_demand=round(avg_demand,1), stats=STATS)

@main.route("/predict", methods=["GET","POST"])
@login_required
def predict():
    result = None
    if request.method == "POST":
        try:
            d = request.form.to_dict()
            demand, wastage, quantity, wp, alert = predict_all(d)
            result = dict(demand=demand, wastage=wastage, quantity=quantity, waste_pct=wp, alert=alert)
            execute(
                """INSERT INTO predictions
                   (user_id,meal_time,service_type,day_type,customers_count,
                    checkout_price,base_price,emailer,homepage,
                    pred_demand,pred_wastage,pred_quantity,alert)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (uid := session["user_id"],
                 d["Meal_Time"], d["Service_Type"], d["Day_Type"], int(d["Customers_Count"]),
                 float(d["checkout_price"]), float(d["base_price"]),
                 int(d.get("emailer_for_promotion",0)), int(d.get("homepage_featured",0)),
                 demand, wastage, quantity, alert)
            )
        except Exception as e:
            flash(f"Prediction error: {e}", "error")
    return render_template("predict.html", result=result)

@main.route("/history")
@login_required
def history():
    preds = query("SELECT * FROM predictions WHERE user_id=? ORDER BY created_at DESC",
                  (session["user_id"],))
    return render_template("history.html", preds=preds)

@main.route("/admin")
@login_required
def admin():
    u = get_current_user()
    if u["role"] != "admin":
        flash("Admin access only.", "error")
        return redirect(url_for("main.dashboard"))
    users       = query("SELECT * FROM users ORDER BY created_at DESC")
    total_preds = query("SELECT COUNT(*) as c FROM predictions", one=True)["c"]
    high_risk   = query("SELECT COUNT(*) as c FROM predictions WHERE alert='HIGH'", one=True)["c"]
    all_preds   = query("""
        SELECT p.*, u.name as user_name
        FROM predictions p JOIN users u ON p.user_id=u.id
        ORDER BY p.created_at DESC LIMIT 30
    """)
    return render_template("admin.html", users=users,
                           total_preds=total_preds, high_risk=high_risk,
                           all_preds=all_preds)

# ── API ───────────────────────────────────────────────────────────────────────

@main.route("/api/predict", methods=["POST"])
def api_predict():
    try:
        d = request.get_json(force=True)
        demand, wastage, quantity, wp, alert = predict_all(d)
        return jsonify({"success":True, "predicted_demand":demand,
                        "predicted_wastage":wastage, "suggested_quantity":quantity,
                        "waste_percentage":wp, "risk_alert":alert})
    except Exception as e:
        return jsonify({"success":False, "error":str(e)}), 400

@main.route("/api/dashboard-stats")
@login_required
def api_dashboard_stats():
    uid   = session["user_id"]
    preds = query("SELECT * FROM predictions WHERE user_id=? ORDER BY created_at DESC LIMIT 10", (uid,))
    preds = list(reversed(preds))
    return jsonify({
        "labels":  [p["created_at"][:16] for p in preds],
        "demand":  [p["pred_demand"]  for p in preds],
        "wastage": [p["pred_wastage"] for p in preds],
        "quantity":[p["pred_quantity"] for p in preds],
        "waste_by_meal":    STATS["waste_by_meal"],
        "waste_by_service": STATS["waste_by_service"],
        "orders_by_day":    STATS["orders_by_day"],
    })
