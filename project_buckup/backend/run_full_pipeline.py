import argparse
import joblib

from feature_engineering import add_features
from create_labels import add_labels
from train_test_split import split_by_project
from train_model import build_pipelines, evaluate, FEATURE_COLS, TARGET_COL
from run_predictions import fetch_raw, predict, upsert_predictions
from explain_model import global_importance


def run(threshold: float, test_size: float, model_out: str):
    print("=" * 60)
    print("STEP 1/5 — Fetching current data from the database")
    print("=" * 60)
    raw = fetch_raw()
    print(f"Loaded {len(raw)} monthly project records.")

    print("\n" + "=" * 60)
    print("STEP 2/5 — Feature engineering")
    print("=" * 60)
    featured = add_features(raw)

    print("\n" + "=" * 60)
    print("STEP 3/5 — Label creation")
    print("=" * 60)
    labeled = add_labels(featured, threshold)
    trainable = labeled.dropna(subset=[TARGET_COL])
    live = labeled[labeled["next_reporting_month"].isna()]
    print(f"Trainable rows: {len(trainable)} | Live (for prediction) rows: {len(live)}")

    print("\n" + "=" * 60)
    print("STEP 4/5 — Train/test split, model training & comparison")
    print("=" * 60)
    train_df, test_df, _ = split_by_project(labeled, test_size)
    X_train, y_train = train_df[FEATURE_COLS], train_df[TARGET_COL].astype(int)
    X_test, y_test = test_df[FEATURE_COLS], test_df[TARGET_COL].astype(int)

    best_name, best_model, best_score = None, None, -1
    for name, pipeline in build_pipelines().items():
        pipeline.fit(X_train, y_train)
        score = evaluate(name, pipeline, X_test, y_test)
        if score > best_score:
            best_name, best_model, best_score = name, pipeline, score

    print(f"\n>>> Best model: {best_name} (F1={best_score:.3f})")
    bundle = {"model": best_model, "features": FEATURE_COLS, "model_name": best_name}
    joblib.dump(bundle, model_out)
    global_importance(bundle)

    print("\n" + "=" * 60)
    print("STEP 5/5 — Predicting on current (live) projects & saving to DB")
    print("=" * 60)
    predicted = predict(bundle, live)
    upsert_predictions(predicted)
    print(f"Updated predictions for {len(predicted)} projects.")

    print("\nPipeline complete. Dashboard and Early Warning page now reflect this run.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=float, default=10.0)
    ap.add_argument("--test-size", type=float, default=0.2)
    ap.add_argument("--model-out", default="risk_model.pkl")
    args = ap.parse_args()

    run(args.threshold, args.test_size, args.model_out)