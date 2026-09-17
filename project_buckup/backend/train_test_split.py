"""
Step 5 — Split the labeled data into train/test/live sets for the PRAVYON risk model.
"""

import argparse
import numpy as np
import pandas as pd


def split_by_project(df: pd.DataFrame, test_size: float, seed: int = 42):
    # Only rows with a known label can be used for training/testing at all.
    trainable = df.dropna(subset=["high_risk_next_month"]).copy()
    live = df[df["next_reporting_month"].isna()].copy()

    unique_projects = trainable["project_code"].unique()
    rng = np.random.default_rng(seed)
    rng.shuffle(unique_projects)

    n_test = max(1, int(len(unique_projects) * test_size))
    test_projects = set(unique_projects[:n_test])
    train_projects = set(unique_projects[n_test:])

    train_df = trainable[trainable["project_code"].isin(train_projects)]
    test_df = trainable[trainable["project_code"].isin(test_projects)]

    return train_df, test_df, live


def summarize(train_df, test_df, live_df):
    print(f"Train: {len(train_df)} rows, {train_df['project_code'].nunique()} unique projects")
    print(f"Test:  {len(test_df)} rows, {test_df['project_code'].nunique()} unique projects")
    print(f"Live (no label, for real predictions later): {len(live_df)} rows")

    overlap = set(train_df["project_code"]) & set(test_df["project_code"])
    print(f"\nProject overlap between train and test: {len(overlap)} "
          f"({'OK - should be 0' if len(overlap) == 0 else 'BUG - this should never happen'})")

    for name, part in [("Train", train_df), ("Test", test_df)]:
        if len(part):
            rate = part["high_risk_next_month"].mean() * 100
            print(f"{name} high-risk rate: {rate:.1f}%")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_path")
    ap.add_argument("--test-size", type=float, default=0.2)
    ap.add_argument("--out-prefix", required=True)
    args = ap.parse_args()

    data = pd.read_csv(args.csv_path)
    train_df, test_df, live_df = split_by_project(data, args.test_size)
    summarize(train_df, test_df, live_df)

    train_df.to_csv(f"{args.out_prefix}_train.csv", index=False)
    test_df.to_csv(f"{args.out_prefix}_test.csv", index=False)
    live_df.to_csv(f"{args.out_prefix}_live.csv", index=False)
    print(f"\nSaved: {args.out_prefix}_train.csv, {args.out_prefix}_test.csv, {args.out_prefix}_live.csv")