# makes a fake dataset with the same columns as the real UCI file.
# I use this to test the scripts quickly without downloading anything.
# the numbers are made up, so don't quote anything from it.
#
#   python src/make_sample_data.py
#   python src/make_sample_data.py --rows 5000

import argparse

import numpy as np
import pandas as pd

from config import RAW_FILE, RANDOM_STATE

MEDS = [
    "metformin", "repaglinide", "nateglinide", "chlorpropamide", "glimepiride",
    "acetohexamide", "glipizide", "glyburide", "tolbutamide", "pioglitazone",
    "rosiglitazone", "acarbose", "miglitol", "troglitazone", "tolazamide",
    "examide", "citoglipton", "insulin", "glyburide-metformin",
    "glipizide-metformin", "glimepiride-pioglitazone",
    "metformin-rosiglitazone", "metformin-pioglitazone",
]

AGE_BANDS = ["[0-10)", "[10-20)", "[20-30)", "[30-40)", "[40-50)",
             "[50-60)", "[60-70)", "[70-80)", "[80-90)", "[90-100)"]
AGE_WEIGHTS = [0.002, 0.007, 0.016, 0.037, 0.095, 0.17, 0.22, 0.256, 0.169, 0.028]

# mix of real icd-9 codes so the diagnosis grouping has something to work with
ICD9_CODES = ["428", "414", "786", "410", "427", "486", "491", "715", "682",
              "434", "780", "996", "276", "250.8", "250.6", "250.02", "599",
              "584", "V57", "403", "562", "577", "820", "198", "?"]


def build(rows):
    rng = np.random.default_rng(RANDOM_STATE)

    # real data has patients coming back more than once, so ids repeat
    n_patients = int(rows * 0.72)
    patient_ids = rng.integers(100_000, 100_000 + n_patients * 3, size=rows)

    age = rng.choice(AGE_BANDS, size=rows, p=AGE_WEIGHTS)
    days = rng.integers(1, 15, size=rows)
    prior_stays = rng.poisson(0.6, size=rows)
    prior_er = rng.poisson(0.2, size=rows)
    n_diag = rng.integers(3, 17, size=rows).clip(max=16)
    a1c = rng.choice(["None", ">8", ">7", "Norm"], size=rows, p=[0.83, 0.08, 0.04, 0.05])
    discharge = rng.choice([1, 3, 6, 18, 2, 22, 11, 5, 25, 4], size=rows,
                           p=[0.59, 0.137, 0.127, 0.036, 0.021, 0.02, 0.016, 0.012, 0.01, 0.031])

    # tie readmission to roughly the same things that drive it in the real data,
    # otherwise the later sprints just find random noise
    age_idx = np.array([AGE_BANDS.index(a) for a in age])
    logit = (-2.6 + 0.45 * np.minimum(prior_stays, 6) + 0.2 * prior_er
             + 0.03 * days + 0.04 * (n_diag - 7)
             + 0.06 * (age_idx - 6) + 0.35 * np.isin(discharge, [3, 22, 5]))
    p30 = 1 / (1 + np.exp(-logit))
    roll = rng.random(rows)
    readmitted = np.where(roll < p30, "<30", np.where(roll < p30 + 0.35, ">30", "NO"))

    df = pd.DataFrame({
        "encounter_id": np.arange(2_000_000, 2_000_000 + rows),
        "patient_nbr": patient_ids,
        "race": rng.choice(["Caucasian", "AfricanAmerican", "Hispanic", "Asian", "Other", "?"],
                           size=rows, p=[0.75, 0.19, 0.02, 0.006, 0.014, 0.02]),
        "gender": rng.choice(["Female", "Male"], size=rows, p=[0.54, 0.46]),
        "age": age,
        "weight": rng.choice(["?", "[75-100)", "[50-75)"], size=rows, p=[0.97, 0.02, 0.01]),
        "admission_type_id": rng.choice([1, 2, 3, 5, 6], size=rows, p=[0.53, 0.18, 0.19, 0.05, 0.05]),
        "discharge_disposition_id": discharge,
        "admission_source_id": rng.choice([7, 1, 17, 4, 6], size=rows, p=[0.56, 0.29, 0.07, 0.04, 0.04]),
        "time_in_hospital": days,
        "payer_code": rng.choice(["?", "MC", "HM", "SP", "BC", "MD"], size=rows,
                                 p=[0.4, 0.32, 0.06, 0.05, 0.05, 0.12]),
        "medical_specialty": rng.choice(["?", "InternalMedicine", "Emergency/Trauma",
                                         "Family/GeneralPractice", "Cardiology", "Surgery-General"],
                                        size=rows, p=[0.49, 0.15, 0.08, 0.08, 0.1, 0.1]),
        "num_lab_procedures": rng.integers(1, 100, size=rows),
        "num_procedures": rng.integers(0, 7, size=rows),
        "num_medications": rng.integers(1, 60, size=rows),
        "number_outpatient": rng.poisson(0.35, size=rows),
        "number_emergency": prior_er,
        "number_inpatient": prior_stays,
        "diag_1": rng.choice(ICD9_CODES, size=rows),
        "diag_2": rng.choice(ICD9_CODES, size=rows),
        "diag_3": rng.choice(ICD9_CODES, size=rows),
        "number_diagnoses": n_diag,
        "max_glu_serum": rng.choice(["None", "Norm", ">200", ">300"], size=rows,
                                    p=[0.95, 0.025, 0.015, 0.01]),
        "A1Cresult": a1c,
    })

    for med in MEDS:
        df[med] = rng.choice(["No", "Steady", "Up", "Down"], size=rows, p=[0.8, 0.15, 0.025, 0.025])
    df["change"] = rng.choice(["No", "Ch"], size=rows, p=[0.54, 0.46])
    df["diabetesMed"] = rng.choice(["Yes", "No"], size=rows, p=[0.77, 0.23])
    df["readmitted"] = readmitted
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=20_000)
    args = parser.parse_args()

    fake = build(args.rows)
    fake.to_csv(RAW_FILE, index=False)
    print(f"wrote {len(fake):,} fake rows to {RAW_FILE}")
    print("heads up: this is practice data, rerun sprint 1 with the real file before sharing anything")
