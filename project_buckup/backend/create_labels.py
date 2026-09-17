"""
Step 4 — Create labels for the PRAVYON risk model.
"""

import argparse
import pandas as pd


def add_labels(df: pd.DataFrame, threshold: float) -> pd.DataFrame:
    df = df.copy().sort_values(["project_code", "reporting_month"]).reset_index(drop=True)

    grouped = df.groupby("project_code")
    df["next_reporting_month"] = grouped["reporting_month"].shift(-1)
    df["next_cost_growth_pct"] = grouped["cost_growth_pct"].shift(-1)

    df["high_risk_next_month"] = (df["next_cost_growth_pct"] > threshold).astype("Int64")
    # No next month exists yet -> label unknown (this row is a live prediction candidate,
    # NOT usable for training).
    df.loc[df["next_reporting_month"].isna(), "high_risk_next_month"] = pd.NA

    return df


def summarize(df: pd.DataFrame):
    trainable = df.dropna(subset=["high_risk_next_month"])
    live = df[df["next_reporting_month"].isna()]

    print(f"Total rows: {len(df)}")
    print(f"Trainable rows (have a known next-month outcome): {len(trainable)}")
    print(f"Live rows (latest month per project, no label yet -> used for real predictions): {len(live)}")

    if len(trainable):
        rate = trainable["high_risk_next_month"].mean() * 100
        print(f"\nClass balance in trainable data: {rate:.1f}% high-risk, {100 - rate:.1f}% low-risk")
        if rate < 5 or rate > 95:
            print("[warn] Classes are very imbalanced — accuracy alone will be misleading later; "
                  "use precision/recall when evaluating the model.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_path")
    ap.add_argument("--threshold", type=float, default=10.0, help="cost_growth_pct threshold for 'high risk'")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    data = pd.read_csv(args.csv_path)
    labeled = add_labels(data, args.threshold)
    summarize(labeled)

    labeled.to_csv(args.out, index=False)
    print(f"\nSaved labeled data -> {args.out}")
    