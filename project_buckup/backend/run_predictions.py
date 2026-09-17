"""
Step 8 — Run predictions for the PRAVYON risk model.
"""

import os
import json
import argparse
from datetime import date

import joblib
import pandas as pd
import psycopg
from dotenv import load_dotenv

from feature_engineering import add_features
from explain_model import per_project_factors

load_dotenv()
DATABASE_URL = os.environ.get("DATABASE_URL")


def db():
    return psycopg.connect(DATABASE_URL, row_factory=psycopg.rows.dict_row)

def fetch_raw() -> pd.DataFrame:
    with db() as conn:
        rows = conn.execute("""
            SELECT p.project_code, p.original_cost, p.original_target_doc,
                   h.reporting_month, h.revised_doc, h.revised_cost,
                   h.cumulative_expenditure, h.physical_progress_pct
            FROM projects p JOIN project_monthly_history h ON h.project_code = p.project_code
            ORDER BY p.project_code, h.reporting_month
        """).fetchall()
    df = pd.DataFrame(rows)
    numeric_cols = ["original_cost", "revised_cost", "cumulative_expenditure", "physical_progress_pct"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype(float)
    return df


def latest_row_per_project(featured: pd.DataFrame) -> pd.DataFrame:
    idx = featured.groupby("project_code")["reporting_month"].idxmax()
    return featured.loc[idx].reset_index(drop=True)


def predict(bundle, live_df: pd.DataFrame) -> pd.DataFrame:
    pipeline = bundle["model"]
    X = live_df[bundle["features"]]
    imputed = pipeline.named_steps["impute"].transform(X)
    for_model = pipeline.named_steps["scale"].transform(imputed) if "scale" in pipeline.named_steps else imputed
    probs = pipeline.named_steps["model"].predict_proba(for_model)[:, 1]

    live_df = live_df.copy()
    live_df["risk_score"] = (probs * 100).round(1)
    live_df["risk_category"] = pd.cut(live_df["risk_score"], bins=[-1, 30, 60, 101], labels=["Low", "Medium", "High"])
    live_df["top_risk_factors"] = per_project_factors(bundle, live_df)
    return live_df

def upsert_predictions(df: pd.DataFrame):
    today = date.today().isoformat()
    records = [
        (row["project_code"], today, float(row["risk_score"]), str(row["risk_category"]),
         round(float(row["risk_score"]) / 100, 4), json.dumps(list(row["top_risk_factors"])))
        for _, row in df.iterrows()
    ]
    with db() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.executemany("""
                INSERT INTO predictions (project_code, prediction_date, risk_score, risk_category,
                    cost_overrun_probability, top_risk_factors)
                VALUES (%s,%s,%s,%s,%s,%s)
                ON CONFLICT (project_code) DO UPDATE SET
                    prediction_date=EXCLUDED.prediction_date, risk_score=EXCLUDED.risk_score,
                    risk_category=EXCLUDED.risk_category,
                    cost_overrun_probability=EXCLUDED.cost_overrun_probability,
                    top_risk_factors=EXCLUDED.top_risk_factors
            """, records)
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("model_path")
    args = ap.parse_args()

    bundle = joblib.load(args.model_path)
    featured = add_features(fetch_raw())
    live = latest_row_per_project(featured)
    predicted = predict(bundle, live)
    upsert_predictions(predicted)

    print(f"Updated predictions for {len(predicted)} projects.\n")
    print(predicted[["project_code", "risk_score", "risk_category"]].to_string())