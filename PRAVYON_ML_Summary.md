# PRAVYON — Machine Learning Pipeline Summary

**Project:** PRAVYON — AI-powered predictive early-warning layer on top of MoSPI's PAIMANA infrastructure project-monitoring portal (Smart India Hackathon 2026, Problem Statement 26103)

---

## 1. The Problem We're Solving

PAIMANA tracks government infrastructure projects (roads, railways, power, water, etc.) and reports their cost, expenditure, and physical progress every month. But it's **descriptive, not predictive** — it tells you what already happened, not what's about to happen.

**Our goal:** Build a system that predicts *before* a project overruns its budget or timeline, explains *why*, and prioritizes which projects need attention first.

---

## 2. Data Pipeline — Getting Real Data In

- PAIMANA publishes a monthly PDF "Flash Report" — ours ran to 100+ pages, with the project list buried inside as a complex table ("Table 6 / All Ongoing Projects") with multi-line, nested cells (project name + agency + project code all packed into one cell).
- We wrote a custom Python extractor (`extract_table6.py` using `pdfplumber`) that:
  - Finds the right pages automatically (text-based detection, not fixed page/table numbers — this mattered because table numbering shifted between 2025 and 2026 report versions)
  - Splits the nested cells into clean fields
  - Carries ministry/sector labels forward across section-header rows
- Each monthly PDF → one clean CSV. Multiple months, uploaded one at a time, get merged into a single **PostgreSQL historical database** — so the same project's numbers across April, May, June... form a time series.

**Result:** ~2,000+ real projects extracted per monthly report, verified against the official portal — no synthetic/fake data used in the final pipeline (we caught and removed an early version that was accidentally testing on fake seed data).

---

## 3. Feature Engineering — Turning Raw Numbers into Signals

From the raw monthly data (original cost, revised cost, expenditure, physical progress %, dates), we engineered:

| Feature | What it captures |
|---|---|
| `cost_growth_pct` | How much the cost has grown vs. the approved baseline |
| `progress_velocity` | How fast physical progress is moving month-over-month (slowing down = warning sign) |
| `expenditure_progress_gap` | Money spent vs. actual work done — a project spending fast but not progressing is a red flag |
| `schedule_slippage_days` | How many days the deadline has already moved |

---

## 4. Label Creation — Defining "Risk" the Right Way

Instead of just labeling "is this project risky *right now*", we labeled **"will this project cross the risk threshold *next month*"**, using next month's actual `cost_growth_pct` as the target.

**Why this mattered:** using this month's own outcome as its own label isn't prediction — it's just describing the present. Predicting next month's outcome from this month's features is what makes it a genuine early-warning system, not a status dashboard.

---

## 5. Train/Test Split — Avoiding a Common Mistake

We split by **project**, not by row. If we'd split randomly, the same project's April and May records could end up on opposite sides of the split — the model would effectively "know" that project already, making test results look artificially good. Splitting by project means the model is tested only on projects it has genuinely never seen.

---

## 6. Model Training — Statistics vs. AI

We trained and compared two models on identical data:
- **Statistical baseline:** Logistic Regression
- **ML model:** Random Forest

Evaluated on **Precision, Recall, and F1 score** (not just accuracy, since high-risk projects are a minority class — accuracy alone would be misleading). This directly answers the hackathon's requirement to prove ML actually adds value over traditional statistics, rather than just asserting it.

---

## 7. Explainability — Not a Black Box

For every prediction, the system surfaces the top contributing factors in plain English, e.g.:
- *"Cost has grown 190.7% above the approved baseline"*
- *"Spending is outpacing physical progress (gap: 2.42)"*
- *"Deadline has already slipped by 2192 days"*

This was built using a feature-deviation ranking approach (comparing each project's own values against the training population), so every risk score comes with a **reason**, not just a number.

---

## 8. Wiring It Into the Live App

- The trained model (`risk_model.pkl`) runs against the current database, and its predictions (risk score, category, and reasons) are written back into a `predictions` table.
- The live web app (`Early Warning` page) fetches this in real time via a REST API and displays it — searchable by project name, code, or ministry.

---

## 9. Current Status & Honest Limitations

- Working end-to-end on real PAIMANA data (not synthetic), verified against the source PDFs.
- Currently trained on a partial set of months (more monthly reports are being added — the pipeline re-runs on new data without any code changes).
- Cost-overrun prediction is live; a matching time-overrun model is a planned next step.
- With few months of history, some risk scores currently look extreme (0% or 100%) — this will smooth out into more nuanced scores as more months of data are added.

---

*This pipeline — PDF → structured historical database → engineered features → leakage-aware labels → project-wise split → compared models → explainable predictions → live dashboard — is the full, working system, not a mockup.*
