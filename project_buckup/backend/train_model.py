"""
Step 6 — Train the PRAVYON risk model.
"""

import argparse
import joblib
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

FEATURE_COLS = [
    "cost_growth_pct", "progress_velocity", "expenditure_progress_gap",
    "schedule_slippage_days", "schedule_revised_yet",
]
TARGET_COL = "high_risk_next_month"


def build_pipelines():
    statistical = Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
        ("model", LogisticRegression(class_weight="balanced", max_iter=1000)),
    ])
    ml_model = Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("model", RandomForestClassifier(
            n_estimators=200, max_depth=6, class_weight={0: 1, 1: 5}, random_state=42
        )),
    ])
    return {"Statistical Baseline (Logistic Regression)": statistical,
            "ML Model (Random Forest)": ml_model}


def evaluate(name, model, X_test, y_test):
    preds = model.predict(X_test)
    print(f"\n--- {name} ---")
    print(f"Accuracy:  {accuracy_score(y_test, preds):.3f}")
    print(f"Precision: {precision_score(y_test, preds, zero_division=0):.3f}  "
          f"(of projects flagged high-risk, how many actually were)")
    print(f"Recall:    {recall_score(y_test, preds, zero_division=0):.3f}  "
          f"(of actual high-risk projects, how many were caught)")
    print(f"F1 score:  {f1_score(y_test, preds, zero_division=0):.3f}")
    return f1_score(y_test, preds, zero_division=0)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("train_csv")
    ap.add_argument("test_csv")
    ap.add_argument("--out-model", required=True)
    args = ap.parse_args()

    train_df = pd.read_csv(args.train_csv)
    test_df = pd.read_csv(args.test_csv)

    X_train, y_train = train_df[FEATURE_COLS], train_df[TARGET_COL].astype(int)
    X_test, y_test = test_df[FEATURE_COLS], test_df[TARGET_COL].astype(int)

    print(f"Training on {len(X_train)} rows, testing on {len(X_test)} rows, "
          f"{len(FEATURE_COLS)} features: {FEATURE_COLS}")

    best_name, best_model, best_score = None, None, -1
    for name, pipeline in build_pipelines().items():
        pipeline.fit(X_train, y_train)
        score = evaluate(name, pipeline, X_test, y_test)
        if score > best_score:
            best_name, best_model, best_score = name, pipeline, score

    print(f"\n>>> Best model: {best_name} (F1={best_score:.3f})")
    joblib.dump({"model": best_model, "features": FEATURE_COLS, "model_name": best_name}, args.out_model)
    print(f"Saved -> {args.out_model}")