# Data Quality Report (Sprint 1)

## Row counts
- Raw rows: 101,766
- Unique patients: 71,518
- Duplicate encounter IDs: 0
- Extra rows from repeat patients: 30,248
- Expired or hospice discharges: 2,423
- Invalid gender values: 3
- Length of stay outside 1-14 days: 0

## Missing values ('?' in the source)

| Column | % missing | Decision |
|---|---|---|
| weight | 96.9% | Dropped. Too sparse to use. |
| medical_specialty | 49.1% | Kept as 'Unknown'. |
| payer_code | 39.6% | Kept as 'Unknown'. Missing payer might mean something on its own. |
| race | 2.2% | Kept as 'Unknown'. |
| diag_3 | 1.4% | Filled with Unknown / grouped as Other |
| diag_2 | 0.4% | Filled with Unknown / grouped as Other |

## Cleaning rules
1. Removed expired and hospice discharges, since these patients can't be readmitted.
2. Kept only each patient's first stay. Repeat stays from the same person aren't independent and would inflate the patterns.
3. Removed rows with invalid gender.
4. Grouped ICD-9 codes into readable diagnosis categories.
5. Target = readmitted within 30 days (1) or not (0).

## Result
- Clean rows: 69,987
- 30-day readmission rate: 9.0%