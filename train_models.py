"""
Trains 3 models: 
  1. Demand Prediction      → predict num_orders
  2. Wastage Prediction     → predict Wastage
  3. Quantity Recommendation → predict Quantity_Prepared

"""

import os, json, warnings
import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

BASE    = os.path.dirname(os.path.abspath(__file__))
DATA    = os.path.join(BASE, "dataset/horeca_food_waste_dataset.csv")
MDL_DIR = os.path.join(BASE, "models")
os.makedirs(MDL_DIR, exist_ok=True)

# 1 Preprocess 
print("Loading data...")
df = pd.read_csv(DATA)
print(f"  Shape: {df.shape}")

le = {}
for col in ["Service_Type", "Day_Type", "Meal_Time"]:
    le[col] = LabelEncoder()
    df[col + "_enc"] = le[col].fit_transform(df[col])
    joblib.dump(le[col], os.path.join(MDL_DIR, f"le_{col}.pkl"))

# Feature engineering
df["price_discount"]   = df["base_price"] - df["checkout_price"]
df["discount_pct"]     = df["price_discount"] / (df["base_price"] + 1e-5)
df["orders_per_cust"]  = df["num_orders"] / (df["Customers_Count"] + 1e-5)
df["waste_ratio"]      = df["Wastage"] / (df["Quantity_Prepared"] + 1e-5)

FEATURES = [
    "week", "center_id", "meal_id",
    "checkout_price", "base_price",
    "emailer_for_promotion", "homepage_featured",
    "Customers_Count",
    "Service_Type_enc", "Day_Type_enc", "Meal_Time_enc",
    "price_discount", "discount_pct",
]

# ── 2. Helpers ────────────────────────────────────────────────────────────────

def get_metrics(y_true, y_pred):
    return {
        "MAE":  round(mean_absolute_error(y_true, y_pred), 4),
        "RMSE": round(np.sqrt(mean_squared_error(y_true, y_pred)), 4),
        "R2":   round(r2_score(y_true, y_pred), 4),
    }

def compare_and_save(task_name, X, y, save_prefix):
    """Train 3 algos, pick best R², save best model + scaler."""
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42)
    scaler = StandardScaler()
    X_tr_s = scaler.fit_transform(X_tr)
    X_te_s = scaler.transform(X_te)

    candidates = {
        "LinearRegression":       LinearRegression(),
        "RandomForest":           RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1),
        "GradientBoosting":       GradientBoostingRegressor(n_estimators=200, learning_rate=0.08,
                                                             max_depth=5, random_state=42),
    }

    results = {}
    best_model, best_r2, best_name = None, -999, ""
    print(f"\n  [{task_name}]")
    for name, mdl in candidates.items():
        mdl.fit(X_tr_s, y_tr)
        m = get_metrics(y_te, mdl.predict(X_te_s))
        results[name] = m
        print(f"    {name:25s}  R²={m['R2']:>7}  MAE={m['MAE']:>8}  RMSE={m['RMSE']:>8}")
        if m["R2"] > best_r2:
            best_r2, best_model, best_name = m["R2"], mdl, name

    print(f"    ✔ Best: {best_name} (R²={best_r2})")
    joblib.dump(best_model, os.path.join(MDL_DIR, f"{save_prefix}_model.pkl"))
    joblib.dump(scaler,     os.path.join(MDL_DIR, f"{save_prefix}_scaler.pkl"))
    return {"task": task_name, "best_algo": best_name, "best_metrics": results[best_name], "all": results}

# ── 3. Train ──────────────────────────────────────────────────────────────────

X = df[FEATURES]

r1 = compare_and_save("Demand Prediction",       X, df["num_orders"],        "demand")
r2 = compare_and_save("Wastage Prediction",       X, df["Wastage"],           "wastage")
r3 = compare_and_save("Quantity Recommendation",  X, df["Quantity_Prepared"], "quantity")

# ── 4. Save Summary ───────────────────────────────────────────────────────────

summary = {"demand": r1, "wastage": r2, "quantity": r3}
with open(os.path.join(MDL_DIR, "metrics.json"), "w") as f:
    json.dump(summary, f, indent=2)

# Save dataset statistics for dashboard charts
stats = {
    "avg_wastage":     round(df["Wastage"].mean(), 2),
    "avg_orders":      round(df["num_orders"].mean(), 2),
    "avg_qty":         round(df["Quantity_Prepared"].mean(), 2),
    "waste_by_meal":   df.groupby("Meal_Time")["Wastage"].mean().round(2).to_dict(),
    "waste_by_service":df.groupby("Service_Type")["Wastage"].mean().round(2).to_dict(),
    "orders_by_day":   df.groupby("Day_Type")["num_orders"].mean().round(2).to_dict(),
    "weekly_trend":    df.groupby("week")["num_orders"].mean().round(2).to_dict(),
}
with open(os.path.join(MDL_DIR, "stats.json"), "w") as f:
    json.dump(stats, f, indent=2)

print("\n✅ All models saved. Training complete.")
print(json.dumps({"demand_R2": r1["best_metrics"]["R2"],
                  "wastage_R2": r2["best_metrics"]["R2"],
                  "quantity_R2": r3["best_metrics"]["R2"]}, indent=2))
