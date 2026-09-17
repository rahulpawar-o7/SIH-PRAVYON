

import argparse
import joblib
import numpy as np
import pandas as pd

FEATURE_LABELS = {
    "cost_growth_pct": "Cost has grown {v:.1f}% above the approved baseline",
    "progress_velocity": "Physical progress is slowing down ({v:.1f} pts/month)",
    "expenditure_progress_gap": "Spending is outpacing physical progress (gap: {v:.2f})",
    "schedule_slippage_days": "Deadline has already slipped by {v:.0f} days",
    "schedule_revised_yet": "Timeline has been officially revised",
}


def global_importance(bundle):
    model = bundle["model"].named_steps["model"]
    features = bundle["features"]
    if hasattr(model, "feature_importances_"):
        scores = model.feature_importances_
    elif hasattr(model, "coef_"):
        scores = np.abs(model.coef_[0])
    else:
        return None
    ranking = sorted(zip(features, scores), key=lambda x: -x[1])
    print(f"\n--- Global feature importance ({bundle['model_name']}) ---")
    for name, score in ranking:
        print(f"{name:28s} {score:.4f}")
    return ranking


def per_project_factors(bundle, df: pd.DataFrame, top_n=3):
    features = bundle["features"]
    X = df[features]
    imputed = bundle["model"].named_steps["impute"].transform(X)
    imputed_df = pd.DataFrame(imputed, columns=features, index=df.index)

    # Rank each row's OWN features by how extreme they are vs the training
    # population median - a simple, fast, defensible stand-in for SHAP when
    # SHAP isn't installed. (If you have `pip install shap`, swap this for a
    # TreeExplainer/LinearExplainer for exact per-row attributions.)
    medians = imputed_df.median()
    spread = imputed_df.std().replace(0, 1)
    z_scores = (imputed_df - medians) / spread

    explanations = []
    for idx, row in z_scores.iterrows():
        ranked = row.abs().sort_values(ascending=False).index[:top_n]
        reasons = []
        for feat in ranked:
            raw_value = df.loc[idx, feat]
            template = FEATURE_LABELS.get(feat, feat + ": {v}")
            try:
                reasons.append(template.format(v=raw_value))
            except (ValueError, TypeError):
                reasons.append(f"{feat}: {raw_value}")
        explanations.append(reasons)
    return explanations


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("model_path")
    ap.add_argument("live_csv", help="the *_live.csv from Step 5 - current, unlabeled projects")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    bundle = joblib.load(args.model_path)
    live_df = pd.read_csv(args.live_csv)

    global_importance(bundle)

    predict_X = live_df[bundle["features"]]
    imputed = bundle["model"].named_steps["impute"].transform(predict_X)
    probs = bundle["model"].named_steps["model"].predict_proba(
        bundle["model"].named_steps.get("scale", type("_", (), {"transform": lambda self, x: x})()).transform(imputed)
        if "scale" in bundle["model"].named_steps else imputed
    )[:, 1]

    live_df["risk_score"] = (probs * 100).round(1)
    live_df["risk_category"] = pd.cut(live_df["risk_score"], bins=[-1, 30, 60, 101], labels=["Low", "Medium", "High"])
    live_df["top_risk_factors"] = per_project_factors(bundle, live_df)

    live_df.to_csv(args.out, index=False)
    print(f"\nSaved live predictions with explanations -> {args.out}")
    print(live_df[["project_code", "risk_score", "risk_category", "top_risk_factors"]].head(10).to_string())