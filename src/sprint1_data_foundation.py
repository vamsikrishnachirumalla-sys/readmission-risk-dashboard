# Sprint 1 - data foundation
#
# goal for this sprint: get the raw data loaded, write down what every
# column means, count what's wrong with it, then clean it into one table
# the rest of the project can trust.
#
#   python src/sprint1_data_foundation.py

import pandas as pd

from config import CLEAN_FILE, EXCLUDED_DISCHARGE_IDS, RAW_FILE, REPORTS_DIR, UCI_DATASET_ID


def fix_blanks(df):
    # the ucimlrepo download turns some values into blanks.
    # putting them back how the original csv had them:
    # lab tests not taken -> "None", everything else missing -> "?"
    for col in ["max_glu_serum", "A1Cresult"]:
        if col in df:
            df[col] = df[col].replace("", "None")
    return df.replace("", "?")


def load_raw():
    # na_filter=False on purpose. this dataset uses "?" for missing,
    # and "None" is a real value meaning the test wasn't done.
    # if pandas guesses, "None" turns into NaN and that meaning is gone
    if RAW_FILE.exists():
        print("loading data from disk")
        return fix_blanks(pd.read_csv(RAW_FILE, na_filter=False, low_memory=False))

    print("no local copy yet, pulling it from UCI (only happens once)")
    from ucimlrepo import fetch_ucirepo

    data = fetch_ucirepo(id=UCI_DATASET_ID).data.original
    data.to_csv(RAW_FILE, index=False)
    return fix_blanks(pd.read_csv(RAW_FILE, na_filter=False, low_memory=False))


# wrote these by hand. it's the first file anyone opens to understand
# the data, so it's worth getting right
COLUMN_NOTES = {
    "encounter_id": "Unique ID for one hospital stay",
    "patient_nbr": "Unique ID for a patient; one patient can have many stays",
    "race": "Patient race as recorded by the hospital",
    "gender": "Patient gender",
    "age": "Age band in 10-year groups, e.g. [70-80)",
    "weight": "Weight band in pounds; mostly missing",
    "admission_type_id": "How the patient came in (1=Emergency, 2=Urgent, 3=Elective, ...)",
    "discharge_disposition_id": "Where the patient went after discharge (1=Home, 3=Skilled nursing, 11=Expired, ...)",
    "admission_source_id": "Referral source (7=Emergency room, 1=Physician referral, ...)",
    "time_in_hospital": "Length of stay in days (1-14)",
    "payer_code": "Insurance payer code (MC=Medicare, MD=Medicaid, ...)",
    "medical_specialty": "Specialty of the admitting physician",
    "num_lab_procedures": "Lab tests done during the stay",
    "num_procedures": "Non-lab procedures done during the stay",
    "num_medications": "Distinct medications given during the stay",
    "number_outpatient": "Outpatient visits in the year before this stay",
    "number_emergency": "ER visits in the year before this stay",
    "number_inpatient": "Inpatient stays in the year before this stay",
    "diag_1": "Primary diagnosis (ICD-9 code)",
    "diag_2": "Secondary diagnosis (ICD-9 code)",
    "diag_3": "Additional secondary diagnosis (ICD-9 code)",
    "number_diagnoses": "Total diagnoses entered for the stay",
    "max_glu_serum": "Glucose serum test result; 'None' means not tested",
    "A1Cresult": "HbA1c test result; 'None' means not tested",
    "change": "Whether diabetes medication was changed (Ch / No)",
    "diabetesMed": "Whether any diabetes medication was prescribed",
    "readmitted": "Readmission outcome: <30 days, >30 days, or NO",
}


def data_dictionary(df):
    rows = []
    for col in df.columns:
        vals = df[col].astype(str)
        rows.append({
            "column": col,
            # anything not in the notes is one of the 23 medication columns
            "definition": COLUMN_NOTES.get(col, "Medication status: No / Steady / Up / Down"),
            "dtype": str(df[col].dtype),
            "distinct_values": df[col].nunique(),
            "pct_missing": round((vals == "?").mean() * 100, 1),
            "top_values": ", ".join(vals.value_counts().head(5).index),
        })
    return pd.DataFrame(rows)


def count_problems(df):
    # count everything BEFORE cleaning so the report shows the starting point
    missing = (df.astype(str) == "?").mean().mul(100).round(1)
    return {
        "total_rows": len(df),
        "unique_patients": df["patient_nbr"].nunique(),
        "duplicate_encounters": int(df["encounter_id"].duplicated().sum()),
        "repeat_patient_rows": int(df["patient_nbr"].duplicated().sum()),
        "expired_or_hospice": int(df["discharge_disposition_id"].isin(EXCLUDED_DISCHARGE_IDS).sum()),
        "bad_gender": int((~df["gender"].isin(["Male", "Female"])).sum()),
        "los_out_of_range": int((~df["time_in_hospital"].between(1, 14)).sum()),
        "missing_pct": missing[missing > 0].sort_values(ascending=False).to_dict(),
    }


def write_quality_report(p, clean_rows, rate):
    decisions = {
        "weight": "Dropped. Too sparse to use.",
        "payer_code": "Kept as 'Unknown'. Missing payer might mean something on its own.",
        "medical_specialty": "Kept as 'Unknown'.",
        "race": "Kept as 'Unknown'.",
    }

    out = [
        "# Data Quality Report (Sprint 1)",
        "",
        "## Row counts",
        f"- Raw rows: {p['total_rows']:,}",
        f"- Unique patients: {p['unique_patients']:,}",
        f"- Duplicate encounter IDs: {p['duplicate_encounters']:,}",
        f"- Extra rows from repeat patients: {p['repeat_patient_rows']:,}",
        f"- Expired or hospice discharges: {p['expired_or_hospice']:,}",
        f"- Invalid gender values: {p['bad_gender']:,}",
        f"- Length of stay outside 1-14 days: {p['los_out_of_range']:,}",
        "",
        "## Missing values ('?' in the source)",
        "",
        "| Column | % missing | Decision |",
        "|---|---|---|",
    ]
    for col, pct in p["missing_pct"].items():
        out.append(f"| {col} | {pct}% | {decisions.get(col, 'Filled with Unknown / grouped as Other')} |")

    out += [
        "",
        "## Cleaning rules",
        "1. Removed expired and hospice discharges, since these patients can't be readmitted.",
        "2. Kept only each patient's first stay. Repeat stays from the same person aren't "
        "independent and would inflate the patterns.",
        "3. Removed rows with invalid gender.",
        "4. Grouped ICD-9 codes into readable diagnosis categories.",
        "5. Target = readmitted within 30 days (1) or not (0).",
        "",
        "## Result",
        f"- Clean rows: {clean_rows:,}",
        f"- 30-day readmission rate: {rate:.1%}",
    ]
    (REPORTS_DIR / "data_quality_report.md").write_text("\n".join(out))


def icd9_group(code):
    # same grouping as the original paper (Strack et al. 2014).
    # 700+ raw codes is unreadable on a chart, 9 groups isn't
    if code in ["?", ""]:
        return "Missing"
    if code.startswith(("V", "E")):
        return "Other"
    try:
        n = float(code)
    except ValueError:
        return "Other"

    if 390 <= n <= 459 or int(n) == 785:
        return "Circulatory"
    if 460 <= n <= 519 or int(n) == 786:
        return "Respiratory"
    if 520 <= n <= 579 or int(n) == 787:
        return "Digestive"
    if int(n) == 250:
        return "Diabetes"
    if 800 <= n <= 999:
        return "Injury"
    if 710 <= n <= 739:
        return "Musculoskeletal"
    if 580 <= n <= 629 or int(n) == 788:
        return "Genitourinary"
    if 140 <= n <= 239:
        return "Neoplasms"
    return "Other"


def clean(df):
    df = df[~df["discharge_disposition_id"].isin(EXCLUDED_DISCHARGE_IDS)]
    df = df[df["gender"].isin(["Male", "Female"])]

    # keep each patient's first visit. encounter_id goes up over time in this data
    df = df.sort_values("encounter_id").drop_duplicates("patient_nbr", keep="first").copy()

    df = df.drop(columns=["weight"])
    for col in ["race", "payer_code", "medical_specialty"]:
        df[col] = df[col].replace("?", "Unknown")

    for col in ["diag_1", "diag_2", "diag_3"]:
        df[col + "_group"] = df[col].astype(str).map(icd9_group)

    # "[70-80)" -> 75 so age can be sorted and used as a number
    df["age_mid"] = df["age"].str.extract(r"\[(\d+)-")[0].astype(int) + 5

    df["prior_visits_total"] = df["number_outpatient"] + df["number_emergency"] + df["number_inpatient"]
    df["readmit_30"] = (df["readmitted"] == "<30").astype(int)
    return df.reset_index(drop=True)


if __name__ == "__main__":
    raw = load_raw()

    data_dictionary(raw).to_csv(REPORTS_DIR / "data_dictionary.csv", index=False)
    problems = count_problems(raw)

    df = clean(raw)
    df.to_csv(CLEAN_FILE, index=False)

    rate = df["readmit_30"].mean()
    write_quality_report(problems, len(df), rate)

    print(f"raw rows:   {len(raw):,}")
    print(f"clean rows: {len(df):,}")
    print(f"30-day readmission rate: {rate:.1%}")
    print("saved data dictionary + quality report to reports/")
