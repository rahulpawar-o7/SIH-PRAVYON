 
import argparse
import pandas as pd
 
NUMERIC_COLS = ["original_cost", "revised_cost", "cumulative_expenditure", "physical_progress_pct"]
DATE_COLS = ["approval_start_date", "original_target_doc", "revised_doc"]
 
 
def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
 
    # --- Numeric columns -----------------------------------------------
    # These SHOULD already be clean numbers coming out of Postgres (they were
    # parsed with clean_number() before insertion), but we coerce again as a
    # safety net in case any text/None slipped through.
    for col in NUMERIC_COLS:
        if col in df.columns:
            before_na = df[col].isna().sum()
            df[col] = pd.to_numeric(df[col], errors="coerce")
            after_na = df[col].isna().sum()
            if after_na > before_na:
                print(f"[warn] '{col}': {after_na - before_na} extra values could not "
                      f"be parsed as numbers and became NaN — inspect the raw CSV for that column.")
 
    # --- Date columns ----------------------------------------------------
    # Unknown exact format coming from the PDF text, so let pandas infer it
    # and report failures instead of silently guessing wrong.
    for col in DATE_COLS:
        if col in df.columns:
            parsed = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
            fail_mask = parsed.isna() & df[col].notna() & (df[col].astype(str).str.strip() != "")
            fail_count = fail_mask.sum()
            if fail_count:
                examples = df.loc[fail_mask, col].astype(str).unique()[:5]
                print(f"[warn] '{col}': {fail_count} values did not parse as dates. "
                      f"Example raw values: {list(examples)}")
            df[col] = parsed
 
    return df
 
 
def missing_report(df: pd.DataFrame, cols):
    print("\n--- Missing value report ---")
    for col in cols:
        if col in df.columns:
            pct = df[col].isna().mean() * 100
            print(f"{col:30s} {pct:5.1f}% missing  ({df[col].isna().sum()} / {len(df)} rows)")
 
 
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_path")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
 
    raw = pd.read_csv(args.csv_path)
    print(f"Loaded {len(raw)} rows, {raw['project_code'].nunique()} unique projects, "
          f"months: {sorted(raw['reporting_month'].unique())}")
 
    cleaned = clean(raw)
    missing_report(cleaned, NUMERIC_COLS + DATE_COLS)
 
    cleaned.to_csv(args.out, index=False)
    print(f"\nSaved cleaned data -> {args.out}")