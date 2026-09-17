
from feature_engineering import add_features
from create_labels import add_labels
from run_predictions import fetch_raw

data = add_labels(add_features(fetch_raw()), threshold=10.0)
trainable = data.dropna(subset=["high_risk_next_month"])

emerging = trainable[(trainable["cost_growth_pct"] <= 10) & (trainable["high_risk_next_month"] == 1)]
already_high = trainable[(trainable["cost_growth_pct"] > 10) & (trainable["high_risk_next_month"] == 1)]

print(f"Already-high-risk rows (easy, persistence): {len(already_high)}")
print(f"Genuinely EMERGING risk rows (hard, valuable): {len(emerging)}")
print(f"Emerging risk as % of all high-risk cases: {len(emerging) / max(1, len(already_high) + len(emerging)) * 100:.1f}%")