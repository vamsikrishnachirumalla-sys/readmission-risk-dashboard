# Sprint 4 - dashboard
#
# four tabs, one per audience:
#   worklist -> care managers picking who to call
#   overview -> director of quality
#   finance  -> rough savings estimate
#   model    -> how much to trust the score
#
#   streamlit run app.py

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.append(str(Path(__file__).parent / "src"))
from config import FIGURES_DIR, METRICS_FILE, SCORED_FILE

st.set_page_config(page_title="Readmission Risk Dashboard", layout="wide")

if not SCORED_FILE.exists():
    st.error("No scored data yet. Run sprints 1-3 first:\n\n"
             "`python src/sprint1_data_foundation.py`\n\n"
             "`python src/sprint2_analysis.py`\n\n"
             "`python src/sprint3_risk_model.py`")
    st.stop()


@st.cache_data
def load():
    # cached so the csv isn't re-read every time someone clicks a filter
    return pd.read_csv(SCORED_FILE), json.loads(METRICS_FILE.read_text())


df, m = load()
high = df[df["risk_tier"] == "High"]

st.title("30-Day Readmission Risk Dashboard")
st.caption("Built on de-identified encounters from the UCI Diabetes 130-US Hospitals dataset. "
           "For portfolio demonstration only, not for clinical use.")

worklist_tab, overview_tab, finance_tab, model_tab = st.tabs(
    ["Care manager worklist", "Overview", "Finance impact", "About the model"])


with worklist_tab:
    st.subheader("Who should get a follow-up call?")

    c1, c2, c3 = st.columns(3)
    tiers = c1.multiselect("Risk tier", ["High", "Medium", "Low"], default=["High"])
    diags = c2.multiselect("Primary diagnosis", sorted(df["diag_1_group"].unique()))
    ages = c3.multiselect("Age band", sorted(df["age"].unique()))

    view = df[df["risk_tier"].isin(tiers)]
    if diags:
        view = view[view["diag_1_group"].isin(diags)]
    if ages:
        view = view[view["age"].isin(ages)]
    view = view.sort_values("risk_score", ascending=False)

    st.write(f"**{len(view):,} patients** match these filters.")

    table = view.rename(columns={
        "patient_nbr": "Patient ID", "age": "Age", "gender": "Gender",
        "diag_1_group": "Primary diagnosis", "time_in_hospital": "Days in hospital",
        "number_inpatient": "Prior stays (1 yr)", "number_emergency": "Prior ER visits",
        "risk_score": "Risk score", "risk_tier": "Tier",
    })[["Patient ID", "Tier", "Risk score", "Age", "Gender", "Primary diagnosis",
        "Days in hospital", "Prior stays (1 yr)", "Prior ER visits"]]

    # only showing 500 rows on screen, the download has everything
    st.dataframe(table.head(500), width="stretch", hide_index=True,
                 column_config={"Risk score": st.column_config.ProgressColumn(
                     format="%.2f", min_value=0.0, max_value=1.0)})
    st.download_button("Download worklist (CSV)", table.to_csv(index=False),
                       file_name="readmission_worklist.csv", mime="text/csv")


with overview_tab:
    overall = df["readmit_30"].mean()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Patients", f"{len(df):,}")
    k2.metric("30-day readmission rate", f"{overall:.1%}")
    k3.metric("Flagged high risk", f"{len(high):,}", f"{len(high) / len(df):.0%} of patients",
              delta_color="off")
    k4.metric("Readmissions caught by high tier",
              f"{high['readmit_30'].sum() / df['readmit_30'].sum():.0%}")

    left, right = st.columns(2)
    with left:
        st.markdown("**Readmission rate by primary diagnosis**")
        by_diag = df.groupby("diag_1_group")["readmit_30"].mean().sort_values(ascending=False)
        st.bar_chart(by_diag * 100, y_label="Rate (%)")
    with right:
        st.markdown("**Readmission rate by prior inpatient stays**")
        # lump 5+ together, the tail is too thin to read on its own
        prior = df["number_inpatient"].clip(upper=5).astype(str).replace("5", "5+")
        st.bar_chart(df.groupby(prior)["readmit_30"].mean() * 100, y_label="Rate (%)")

    st.markdown("**Charts from sprints 2 and 3**")
    cols = st.columns(2)
    for i, img in enumerate(sorted(FIGURES_DIR.glob("*.png"))):
        cols[i % 2].image(str(img), width="stretch")


with finance_tab:
    st.subheader("What is a drop in readmissions worth?")
    st.write("Every number here is an assumption you can change. "
             "The defaults are placeholders, swap in a real hospital's figures.")

    a1, a2, a3 = st.columns(3)
    cost_per_readmit = a1.number_input("Average cost per readmission ($)", value=15_000, step=500)
    reduction = a2.slider("Expected reduction in high-tier readmissions", 0, 50, 10, format="%d%%")
    cost_per_call = a3.number_input("Follow-up program cost per patient ($)", value=150, step=25)

    high_readmits = int(high["readmit_30"].sum())
    avoided = high_readmits * reduction / 100
    program_cost = len(high) * cost_per_call
    net = avoided * cost_per_readmit - program_cost

    f1, f2, f3, f4 = st.columns(4)
    f1.metric("Readmissions in high tier", f"{high_readmits:,}")
    f2.metric("Readmissions avoided", f"{avoided:,.0f}")
    f3.metric("Program cost", f"${program_cost:,.0f}")
    f4.metric("Net savings", f"${net:,.0f}")

    st.caption("This leaves out CMS penalty adjustments, which depend on each hospital's "
               "excess readmission ratio for specific conditions. It's a rough sizing, not a forecast.")


with model_tab:
    st.subheader("How good is the risk score?")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("ROC AUC", m["roc_auc"])
    c2.metric("Patients flagged high", f"{m['flagged_share']:.0%}")
    c3.metric("Readmissions caught", f"{m['recall']:.0%}",
              help="Share of actual readmissions that landed in the high tier")
    c4.metric("Precision", f"{m['precision']:.0%}",
              help="Share of high-tier patients who actually came back")
    c5.metric("Lift vs random", f"{m['lift_vs_random']}x")

    st.markdown(f"""
- The high tier is sized to what a care team can realistically call, about **{m['flagged_share']:.0%}
  of discharges**. That's a capacity decision, not a statistical one.
- Calling that group catches **{m['recall']:.0%} of readmissions**. Picking the same number of patients
  at random would catch about {m['flagged_share']:.0%}, so the score gives **{m['lift_vs_random']}x lift**.
- About **{m['precision']:.0%}** of high-tier patients came back, against a base rate of
  {m['base_rate']:.0%}. That gap is what the score is worth.
- An AUC around 0.6 to 0.7 is normal for readmission models built on admin data.
  Clinical notes and social factors usually push it higher.
""")
