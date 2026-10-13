# Sprint 2 - readmission analysis
#
# two questions from the stakeholders:
#   director of quality -> where are readmissions concentrated?
#   care managers       -> what should we ask patients about at discharge?
#
# every chart shows the group's rate next to the overall rate. a rate by itself
# doesn't mean much to anyone, "twice the hospital average" does
#
#   python src/sprint2_analysis.py

import matplotlib
matplotlib.use("Agg")  # just saving pngs, no screen needed
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from config import CLEAN_FILE, FIGURES_DIR, REPORTS_DIR

BLUE = "#1f6f8b"
GREY = "#9aa5b1"
RED = "#d1495b"


def rate_by(df, col, min_patients=100):
    # drop tiny groups, otherwise 3 patients with 2 readmits ends up on top
    out = (df.groupby(col)["readmit_30"]
             .agg(patients="count", readmissions="sum", rate="mean")
             .reset_index())
    out = out[out["patients"] >= min_patients]
    out["vs_overall"] = out["rate"] / df["readmit_30"].mean()
    return out


def bar_chart(table, col, title, filename, overall, sort=True):
    data = table.sort_values("rate") if sort else table
    # red = more than 20% above average, easy to spot at a glance
    colors = [RED if r > overall * 1.2 else BLUE for r in data["rate"]]

    fig, ax = plt.subplots(figsize=(8, max(3, 0.45 * len(data) + 1)))
    ax.barh(data[col].astype(str), data["rate"] * 100, color=colors)
    # overall line goes in a legend. tried labeling it directly but it kept
    # landing on the axis or the title depending on the chart
    ax.axvline(overall * 100, color=GREY, linestyle="--", linewidth=1,
               label=f"overall rate {overall:.1%}")
    # legend sits above the plot on the right, so it never covers a bar
    ax.legend(loc="lower right", bbox_to_anchor=(1, 1), frameon=False, fontsize=9)
    # extra room on the right so the "12.3% (n=...)" labels don't get cut off
    ax.set_xlim(0, data["rate"].max() * 100 * 1.25)

    for i, (r, n) in enumerate(zip(data["rate"], data["patients"])):
        ax.text(r * 100 + 0.2, i, f"{r:.1%}  (n={n:,})", va="center", fontsize=8, color="#333")

    ax.set_title(title, loc="left", fontsize=12, fontweight="bold")
    ax.set_xlabel("30-day readmission rate (%)")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / filename, dpi=150)
    plt.close(fig)


def los_bucket(days):
    if days <= 2:
        return "1-2 days"
    if days <= 4:
        return "3-4 days"
    if days <= 7:
        return "5-7 days"
    return "8+ days"


def factor_ranking(df):
    # simple yes/no comparisons instead of a model. care managers can act on
    # "patients with a prior stay come back almost twice as often" right away
    checks = {
        "Had 1+ inpatient stays in prior year": df["number_inpatient"] >= 1,
        "Had 1+ ER visits in prior year": df["number_emergency"] >= 1,
        "Stayed 8+ days": df["time_in_hospital"] >= 8,
        "Age 70 or older": df["age_mid"] >= 75,
        "9+ diagnoses on record": df["number_diagnoses"] >= 9,
        "Discharged to skilled nursing or other facility": df["discharge_disposition_id"].isin([3, 4, 5, 22]),
        "Diabetes meds changed during stay": df["change"] == "Ch",
        "HbA1c not tested": df["A1Cresult"] == "None",
        "Primary diagnosis circulatory": df["diag_1_group"] == "Circulatory",
        "Primary diagnosis respiratory": df["diag_1_group"] == "Respiratory",
    }

    rows = []
    for label, has_it in checks.items():
        # skip if either side is too small to trust
        if has_it.sum() < 100 or (~has_it).sum() < 100:
            continue
        with_it = df.loc[has_it, "readmit_30"].mean()
        without = df.loc[~has_it, "readmit_30"].mean()
        rows.append({
            "factor": label,
            "patients_with_factor": int(has_it.sum()),
            "share_of_patients": has_it.mean(),
            "rate_with": with_it,
            "rate_without": without,
            "relative_risk": with_it / without if without else np.nan,
        })
    return pd.DataFrame(rows).sort_values("relative_risk", ascending=False)


def write_findings(df, overall, by_diag, by_los, by_prior, factors):
    top = factors.iloc[0]
    worst_diag = by_diag.sort_values("rate", ascending=False).iloc[0]
    worst_los = by_los.sort_values("rate", ascending=False).iloc[0]
    many_stays = by_prior.loc[by_prior["prior_bucket"] == "3+", "rate"]
    no_stays = by_prior.loc[by_prior["prior_bucket"] == "0", "rate"]

    if len(many_stays) and len(no_stays):
        prior_line = (f"Patients with 3+ inpatient stays in the past year were readmitted at "
                      f"{many_stays.iloc[0]:.1%}, versus {no_stays.iloc[0]:.1%} for patients with none.")
    else:
        prior_line = "See the prior-stays chart."

    out = [
        "# Findings Summary (Sprint 2)",
        "",
        "Prepared for: Director of Quality",
        "",
        f"**Overall 30-day readmission rate: {overall:.1%}** across {len(df):,} patients.",
        "",
        "## What stands out",
        "",
        f"1. **Repeat hospital users are the clearest high-risk group.** {prior_line}",
        f"2. **{top['factor']}** has the highest relative risk: "
        f"{top['rate_with']:.1%} vs {top['rate_without']:.1%} ({top['relative_risk']:.1f}x).",
        f"3. **{worst_diag['diag_1_group']}** is the highest-risk primary diagnosis group at "
        f"{worst_diag['rate']:.1%} ({worst_diag['vs_overall']:.2f}x the overall rate).",
        f"4. **Stays of {worst_los['los_bucket']}** have the highest readmission rate at {worst_los['rate']:.1%}.",
        "",
        "## Factor ranking",
        "",
        "| Factor | Patients | Rate with | Rate without | Relative risk |",
        "|---|---|---|---|---|",
    ]
    for _, r in factors.iterrows():
        out.append(f"| {r['factor']} | {r['patients_with_factor']:,} | {r['rate_with']:.1%} | "
                   f"{r['rate_without']:.1%} | {r['relative_risk']:.2f}x |")

    out += [
        "",
        "## What this means for care managers",
        "",
        "Start discharge follow-up with patients who were already in the hospital in the past year. "
        "That one question catches a big share of the highest-risk group.",
        "",
        "## Caveats",
        "",
        "These are associations, not causes. Sicker patients both stay longer and come back more often, "
        "so length of stay is partly standing in for how sick someone is. Sprint 3 looks at all the "
        "factors together.",
    ]
    (REPORTS_DIR / "findings_summary.md").write_text("\n".join(out))


if __name__ == "__main__":
    df = pd.read_csv(CLEAN_FILE, low_memory=False)
    overall = df["readmit_30"].mean()

    by_age = rate_by(df, "age", min_patients=50)
    bar_chart(by_age, "age", "Readmission rate by age band", "01_rate_by_age.png", overall, sort=False)

    by_diag = rate_by(df, "diag_1_group")
    bar_chart(by_diag, "diag_1_group", "Readmission rate by primary diagnosis",
              "02_rate_by_diagnosis.png", overall)

    df["los_bucket"] = df["time_in_hospital"].map(los_bucket)
    by_los = rate_by(df, "los_bucket")
    # keep the buckets in time order, not alphabetical
    order = {"1-2 days": 0, "3-4 days": 1, "5-7 days": 2, "8+ days": 3}
    by_los = by_los.sort_values("los_bucket", key=lambda s: s.map(order))
    bar_chart(by_los, "los_bucket", "Readmission rate by length of stay",
              "03_rate_by_length_of_stay.png", overall, sort=False)

    df["prior_bucket"] = df["number_inpatient"].map(lambda n: str(n) if n < 3 else "3+")
    by_prior = rate_by(df, "prior_bucket", min_patients=30).sort_values("prior_bucket")
    bar_chart(by_prior, "prior_bucket", "Readmission rate by inpatient stays in the prior year",
              "04_rate_by_prior_stays.png", overall, sort=False)

    factors = factor_ranking(df)
    factors.to_csv(REPORTS_DIR / "factor_ranking.csv", index=False)
    write_findings(df, overall, by_diag, by_los, by_prior, factors)

    print(f"overall 30-day readmission rate: {overall:.1%}\n")
    print("top factors:")
    print(factors[["factor", "rate_with", "rate_without", "relative_risk"]]
          .head(5).to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    print("\ncharts saved to reports/figures/, summary in reports/findings_summary.md")
