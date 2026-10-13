# Sprint 3 - risk scoring
#
# score every patient low / medium / high so care managers know who to call,
# and show what's driving the score so the quality team can trust it.
#
# went with logistic regression on purpose. a boosted model might get a
# slightly better AUC, but the quality team has to explain this to doctors.
# readable coefficients beat a black box here. can swap later if needed.
#
#   python src/sprint3_risk_model.py

import json

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from config import CLEAN_FILE, FIGURES_DIR, METRICS_FILE, MODEL_FILE, RANDOM_STATE, REPORTS_DIR, SCORED_FILE

NUMERIC = [
    "age_mid", "time_in_hospital", "num_lab_procedures", "num_procedures",
    "num_medications", "number_outpatient", "number_emergency",
    "number_inpatient", "number_diagnoses",
]
CATEGORICAL = [
    "gender", "admission_type_id", "discharge_disposition_id",
    "admission_source_id", "diag_1_group", "A1Cresult", "insulin",
    "change", "diabetesMed",
]

# tiers are based on how many calls the care team can actually make,
# not on some statistical cutoff. first version flagged over half the
# patients as high risk, which nobody could ever work through.
# change these if the real team has more or less capacity
HIGH_SHARE = 0.20    # top 20% of scores = High
MEDIUM_SHARE = 0.30  # next 30% = Medium

# nicer names for the driver chart. "cat__discharge_disposition_id_3"
# means nothing to a care manager
NICE_NAMES = {
    "age_mid": "Older age",
    "time_in_hospital": "Longer stay",
    "num_lab_procedures": "More lab tests",
    "num_procedures": "More procedures",
    "num_medications": "More medications",
    "number_outpatient": "Prior outpatient visits",
    "number_emergency": "Prior ER visits",
    "number_inpatient": "Prior inpatient stays",
    "number_diagnoses": "More diagnoses",
}
PREFIXES = {
    "discharge_disposition_id": "Discharged to",
    "admission_source_id": "Admitted from",
    "admission_type_id": "Admission type",
    "diag_1_group": "Primary dx",
    "A1Cresult": "HbA1c",
    "insulin": "Insulin",
    "change": "Med change",
    "diabetesMed": "On diabetes meds",
    "gender": "Gender",
}
# code meanings from the IDs_mapping file that comes with the dataset.
# the first version only had the common ones and the chart ended up showing
# stuff like "Discharged to: 28", so this is the full list now
CODES = {
    "discharge_disposition_id": {
        "1": "home", "2": "short-term hospital", "3": "skilled nursing facility",
        "4": "intermediate care facility", "5": "another inpatient facility",
        "6": "home with health service", "7": "left against medical advice",
        "8": "home with IV provider", "9": "admitted to this hospital",
        "10": "neonate to another hospital", "12": "still a patient",
        "15": "swing bed", "16": "outpatient at another facility",
        "17": "outpatient at this facility", "18": "unknown",
        "22": "rehab facility", "23": "long-term care hospital",
        "24": "Medicaid nursing facility", "25": "not mapped", "26": "unknown",
        "27": "federal facility", "28": "psychiatric hospital",
        "29": "critical access hospital", "30": "other facility",
    },
    "admission_source_id": {
        "1": "physician referral", "2": "clinic referral", "3": "HMO referral",
        "4": "another hospital", "5": "skilled nursing facility",
        "6": "another facility", "7": "emergency room", "8": "court/law enforcement",
        "9": "not available", "10": "critical access hospital",
        "15": "not available", "17": "unknown", "20": "not mapped",
        "21": "unknown", "22": "same facility", "25": "ambulatory surgery center",
    },
    "admission_type_id": {
        "1": "emergency", "2": "urgent", "3": "elective", "4": "newborn",
        "5": "not available", "6": "unknown", "7": "trauma center", "8": "not mapped",
    },
    "A1Cresult": {"None": "not tested"},
    "change": {"Ch": "yes", "No": "no"},
}

# codes that only mean "we don't know". they get big coefficients sometimes,
# but nobody can do anything with "discharge not mapped", so they stay in the
# csv and come off the chart
NOT_ACTIONABLE = ("unknown", "not mapped", "not available", "rare codes")


def make_pipeline():
    prep = ColumnTransformer([
        ("num", StandardScaler(), NUMERIC),
        ("cat", OneHotEncoder(handle_unknown="ignore", min_frequency=50), CATEGORICAL),
    ])
    # only ~1 in 10 patients gets readmitted. without balanced weights the
    # model just says "no" to everyone and still looks 90% accurate
    model = LogisticRegression(max_iter=2000, class_weight="balanced", C=0.5)
    return Pipeline([("prep", prep), ("model", model)])


def readable(feature):
    raw = feature.split("__", 1)[1]
    if raw in NICE_NAMES:
        return NICE_NAMES[raw]
    for col, label in PREFIXES.items():
        if raw.startswith(col + "_"):
            value = raw[len(col) + 1:]
            # sklearn lumps codes with <50 patients into "infrequent_sklearn"
            if value == "infrequent_sklearn":
                return f"{label}: other (rare codes)"
            return f"{label}: {CODES.get(col, {}).get(value, value)}"
    return raw.replace("_", " ")


def get_drivers(pipe):
    names = pipe.named_steps["prep"].get_feature_names_out()
    coefs = pipe.named_steps["model"].coef_[0]
    drivers = pd.DataFrame({"feature": names, "coefficient": coefs})
    drivers["odds_ratio"] = np.exp(drivers["coefficient"])
    drivers["driver"] = drivers["feature"].map(readable)
    return drivers.sort_values("coefficient", ascending=False)


def plot_drivers(drivers):
    usable = drivers[~drivers["driver"].str.contains("|".join(NOT_ACTIONABLE))]
    top = pd.concat([usable.head(8), usable.tail(5)]).iloc[::-1]
    colors = ["#d1495b" if c > 0 else "#1f6f8b" for c in top["coefficient"]]

    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.barh(top["driver"], top["coefficient"], color=colors)
    ax.axvline(0, color="#999", linewidth=0.8)
    # title goes on the figure, not the axis, so long labels can't push it off the edge
    fig.suptitle("What pushes readmission risk up (red) or down (blue)",
                 x=0.02, ha="left", fontsize=12, fontweight="bold")
    ax.set_xlabel("Model coefficient (numeric features are per 1 std. dev.)")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "05_risk_drivers.png", dpi=150)
    plt.close(fig)


def plot_tiers(df):
    # the real test: do high tier patients actually come back more?
    tiers = (df.groupby("risk_tier")["readmit_30"]
               .agg(patients="count", rate="mean")
               .reindex(["Low", "Medium", "High"]))

    fig, ax = plt.subplots(figsize=(6, 3.5))
    bars = ax.bar(tiers.index, tiers["rate"] * 100, color=["#1f6f8b", "#edae49", "#d1495b"])
    for bar, (n, r) in zip(bars, tiers.itertuples(index=False)):
        ax.text(bar.get_x() + bar.get_width() / 2, r * 100 + 0.3,
                f"{r:.1%}\n{n:,} patients", ha="center", fontsize=9)
    ax.set_ylabel("Actual readmission rate (%)")
    ax.set_title("Do the risk tiers separate patients?", loc="left", fontsize=12, fontweight="bold")
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_ylim(0, tiers["rate"].max() * 130)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "06_risk_tiers.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    df = pd.read_csv(CLEAN_FILE, low_memory=False)
    for col in CATEGORICAL:
        df[col] = df[col].astype(str)  # codes like 1, 3, 6 are labels, not numbers

    X, y = df[NUMERIC + CATEGORICAL], df["readmit_30"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, stratify=y, random_state=RANDOM_STATE)

    pipe = make_pipeline().fit(X_train, y_train)

    # set the tier cutoffs on the training patients only, so the test set
    # gets judged on a line it had no part in drawing
    train_scores = pipe.predict_proba(X_train)[:, 1]
    high_cut = float(np.quantile(train_scores, 1 - HIGH_SHARE))
    low_cut = float(np.quantile(train_scores, 1 - HIGH_SHARE - MEDIUM_SHARE))

    test_scores = pipe.predict_proba(X_test)[:, 1]
    flagged = test_scores >= high_cut
    tn, fp, fn, tp = confusion_matrix(y_test, flagged).ravel()
    recall = recall_score(y_test, flagged)

    metrics = {
        "test_patients": int(len(y_test)),
        "base_rate": round(float(y_test.mean()), 4),
        "roc_auc": round(float(roc_auc_score(y_test, test_scores)), 3),
        "threshold": round(high_cut, 3),
        "recall": round(float(recall), 3),
        "precision": round(float(precision_score(y_test, flagged)), 3),
        "flagged_share": round(float(flagged.mean()), 3),
        # if we flagged 20% at random we'd catch ~20% of readmits.
        # lift = how many times better the score does than that
        "lift_vs_random": round(float(recall / max(flagged.mean(), 1e-9)), 2),
        "confusion_matrix": {"true_neg": int(tn), "false_pos": int(fp),
                             "false_neg": int(fn), "true_pos": int(tp)},
    }
    METRICS_FILE.write_text(json.dumps(metrics, indent=2))

    # score everyone for the dashboard worklist
    df["risk_score"] = pipe.predict_proba(X)[:, 1]
    df["risk_tier"] = np.where(df["risk_score"] >= high_cut, "High",
                      np.where(df["risk_score"] >= low_cut, "Medium", "Low"))

    keep = ["encounter_id", "patient_nbr", "age", "gender", "diag_1_group",
            "time_in_hospital", "number_inpatient", "number_emergency",
            "discharge_disposition_id", "A1Cresult", "risk_score", "risk_tier", "readmit_30"]
    df[keep].to_csv(SCORED_FILE, index=False)

    drivers = get_drivers(pipe)
    drivers.to_csv(REPORTS_DIR / "risk_drivers.csv", index=False)
    plot_drivers(drivers)
    plot_tiers(df)

    joblib.dump({"pipeline": pipe, "tier_cuts": (low_cut, high_cut),
                 "numeric": NUMERIC, "categorical": CATEGORICAL}, MODEL_FILE)

    print(json.dumps(metrics, indent=2))
    print("\nreadmission rate by tier:")
    print(df.groupby("risk_tier")["readmit_30"].agg(["count", "mean"])
            .reindex(["Low", "Medium", "High"]).round(3))
    print("\ntop risk drivers:")
    print(drivers[["driver", "odds_ratio"]].head(6).to_string(index=False))
