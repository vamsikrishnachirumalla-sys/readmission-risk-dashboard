# Agile Backlog: 30-Day Readmission Risk Dashboard

## Product vision

Give the quality team a simple, trusted way to find patients likely to be readmitted within 30 days, so care managers can follow up before discharge.

## Roles

| Role | Person | Cares about |
|---|---|---|
| Product owner | Director of Quality | Lowering the readmission rate |
| End users | Care managers | Knowing who to call first |
| Stakeholder | Finance | Penalty dollars and program cost |
| Data analyst | Vamsi Krishna Chirumalla | Building and explaining the analysis |

## Definition of done

A story is done when the code runs from a clean checkout, outputs are saved to `reports/`, numbers have been checked against totals, and the result is written in plain language for its audience.

---

## Epic 1: Data foundation (Sprint 1)

**US-1.1** As an analyst, I need a data dictionary for every field so the team reads the data the same way.
- Acceptance: every column has a definition, type, distinct count, and % missing.
- Output: `reports/data_dictionary.csv`

**US-1.2** As an analyst, I need data quality checks so bad records don't skew results.
- Acceptance: missing values, duplicates, invalid codes, and excluded discharges are counted before cleaning, and every cleaning rule is written down.
- Output: `reports/data_quality_report.md`, `data/processed/encounters_clean.csv`

## Epic 2: Readmission analysis (Sprint 2)

**US-2.1** As the Director of Quality, I want readmission rates by age, diagnosis, and length of stay so I know where the problem is concentrated.
- Acceptance: rates shown against the overall rate, groups under 100 patients excluded, totals reconcile.
- Output: `reports/figures/01-04_*.png`

**US-2.2** As a care manager, I want to know which discharge factors link to readmission so I know what to ask patients.
- Acceptance: factors ranked by relative risk and explained in plain language, with a caveat that these are associations.
- Output: `reports/factor_ranking.csv`, `reports/findings_summary.md`

## Epic 3: Risk scoring (Sprint 3)

**US-3.1** As a care manager, I want each patient scored low, medium, or high risk so I can prioritize calls.
- Acceptance: tiers sized to team capacity (top 20% = High), model tested on held-out patients, AUC, recall, precision, and lift reported honestly.
- Output: `data/processed/patients_scored.csv`, `reports/model_metrics.json`

**US-3.2** As the Director of Quality, I want to understand why a patient is high risk so I can trust the score.
- Acceptance: top drivers shown with readable names, not raw codes.
- Output: `reports/risk_drivers.csv`, `reports/figures/05_risk_drivers.png`

## Epic 4: Dashboard and handoff (Sprint 4)

**US-4.1** As a care manager, I want a dashboard filtered to high-risk patients so I can work through my list each morning.
- Acceptance: filters by tier, diagnosis, and age; sorted by risk; downloadable.
- Output: `app.py` worklist tab

**US-4.2** As Finance, I want an estimate of savings if readmissions drop so I can see the value.
- Acceptance: every assumption is visible and editable; program cost is subtracted.
- Output: `app.py` finance tab

---

## Sprint plan

| Sprint | Weeks | Goal | Review deliverable |
|---|---|---|---|
| 1 | 1-2 | Data foundation | Data quality report |
| 2 | 3-4 | Analysis | Findings summary for the Director of Quality |
| 3 | 5-6 | Risk scoring | Model results with known limits |
| 4 | 7-8 | Dashboard and handoff | Live dashboard demo |

---

## Sprint retrospectives

Fill these in as you go. Keep each one short and honest.

### Sprint 1
- **What went well:**
- **What didn't:**
- **What I'll change:**

### Sprint 2
- **What went well:**
- **What didn't:**
- **What I'll change:**

### Sprint 3
- **What went well:**
- **What didn't:** A pure recall-based cutoff flagged over half of patients as high risk. Statistically fine, useless to a care team.
- **What I'll change:** Sized the high tier to team capacity (top 20%) and reported lift instead.

### Sprint 4
- **What went well:**
- **What didn't:**
- **What I'll change:**
