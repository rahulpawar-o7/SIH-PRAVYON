
import argparse
import numpy as np
import pandas as pd
 
 
def add_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
 
    # Sort so that "previous month" logic (velocity, deltas) is correct per project.
    df = df.sort_values(["project_code", "reporting_month"]).reset_index(drop=True)
 
    # --- 1) cost_growth_pct -------------------------------------------
    df["cost_growth_pct"] = np.where(
        df["original_cost"].notna() & (df["original_cost"] != 0) & df["revised_cost"].notna(),
        (df["revised_cost"] - df["original_cost"]) / df["original_cost"] * 100,
        np.nan,
    )
 
    # --- 2) progress_velocity (this month's progress - previous month's) ---
    grouped = df.groupby("project_code")["physical_progress_pct"]
    df["prev_physical_progress_pct"] = grouped.shift(1)
    df["progress_velocity"] = df["physical_progress_pct"] - df["prev_physical_progress_pct"]
    # First reporting month for a project has no "previous" -> velocity is unknown, not zero.
    df.loc[df["prev_physical_progress_pct"].isna(), "progress_velocity"] = np.nan
 
    # --- 3) expenditure_progress_gap -----------------------------------
    expenditure_ratio = np.where(
        df["original_cost"].notna() & (df["original_cost"] != 0) & df["cumulative_expenditure"].notna(),
        df["cumulative_expenditure"] / df["original_cost"],
        np.nan,
    )
    progress_ratio = df["physical_progress_pct"] / 100.0
    df["expenditure_progress_gap"] = expenditure_ratio - progress_ratio
 
    # --- 4) schedule_slippage_days --------------------------------------
    original_target = pd.to_datetime(df["original_target_doc"], errors="coerce", dayfirst=True)
    revised_target = pd.to_datetime(df["revised_doc"], errors="coerce", dayfirst=True)
 
    df["schedule_slippage_days"] = (revised_target - original_target).dt.days
    # Distinguish "not yet revised" (unknown) from "revised with zero slippage" (actually 0).
    df["schedule_revised_yet"] = revised_target.notna()
 
    return df
 
 
def summarize(df: pd.DataFrame):
    print("\n--- Feature summary ---")
    for col in ["cost_growth_pct", "progress_velocity", "expenditure_progress_gap", "schedule_slippage_days"]:
        valid = df[col].dropna()
        if len(valid):
            print(f"{col:28s} n={len(valid):6d}  mean={valid.mean():8.2f}  "
                  f"min={valid.min():8.2f}  max={valid.max():8.2f}")
        else:
            print(f"{col:28s} no valid values yet (check upstream data)")
    print(f"\nProjects with at least one revised deadline: "
          f"{df.loc[df['schedule_revised_yet'], 'project_code'].nunique()} / {df['project_code'].nunique()}")
 
 
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_path")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
 
    data = pd.read_csv(args.csv_path)
    featured = add_features(data)
    summarize(featured)
 
    featured.to_csv(args.out, index=False)
    print(f"\nSaved feature-engineered data -> {args.out}")
 