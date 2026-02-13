from __future__ import annotations

import json
import os

import pandas as pd
import plotly.express as px
import streamlit as st

from src.alerts import add_alert_rule, evaluate_alerts, list_alert_events
from src.db import get_connection, init_db, query_country_values
from src.ingest import ingest_country
from src.scenarios import record_scenario, simulate
from src.scoring import compute_scores
from src.utils import deterministic_summary

st.set_page_config(page_title="Food Security Early Warning", layout="wide")

conn = get_connection()
init_db(conn)

st.sidebar.title("Food Security MVP")
page = st.sidebar.radio("Page", ["Country Dashboard", "Alerts", "Scenario Simulator", "Export"])
country = st.sidebar.selectbox("Country (ISO3)", ["KEN", "SDN", "YEM"])
demo_mode = st.sidebar.toggle("Offline demo mode", value=os.getenv("DEMO_MODE", "0") == "1")

status = ingest_country(conn, country, demo_mode=demo_mode)
st.sidebar.caption(f"Ingestion mode: {status}")

rows = [dict(r) for r in query_country_values(conn, country)]
df = pd.DataFrame(rows)
if df.empty:
    st.warning("No data available.")
    st.stop()

df["date"] = pd.to_datetime(df["date"])
min_date = df["date"].min().date()
max_date = df["date"].max().date()
selected_range = st.sidebar.date_input("Date range", (min_date, max_date), min_value=min_date, max_value=max_date)
if isinstance(selected_range, tuple) and len(selected_range) == 2:
    start_date, end_date = selected_range
else:
    start_date, end_date = min_date, max_date

indicator_options = sorted(df["indicator_id"].unique().tolist())
selected_indicators = st.sidebar.multiselect("Indicators", indicator_options, default=indicator_options[: min(4, len(indicator_options))])

fdf = df[(df["date"].dt.date >= start_date) & (df["date"].dt.date <= end_date)].copy()
if selected_indicators:
    fdf = fdf[fdf["indicator_id"].isin(selected_indicators)]

if fdf.empty:
    st.warning("No data after filtering.")
    st.stop()

latest_idx = fdf.groupby("indicator_id")["date"].idxmax()
latest_rows = fdf.loc[latest_idx].to_dict("records")
score_pack = compute_scores(fdf.to_dict("records"), latest_rows)
alert_count = len(list_alert_events(conn, country))
summary = deterministic_summary(country, score_pack["overall_risk"], [k for k, _ in score_pack["contributors"]], alert_count)

if page == "Country Dashboard":
    st.title("Country Dashboard")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Overall risk (0-100)", score_pack["overall_risk"])
    c2.metric("Food stress proxy", round(score_pack["category_scores"].get("food", 0.0), 2))
    c3.metric("Conflict proxy", round(score_pack["category_scores"].get("conflict", 0.0), 2))
    c4.metric("Macro proxy", round(score_pack["category_scores"].get("macro", 0.0), 2))

    st.write(summary)

    ts = px.line(fdf, x="date", y="value", color="indicator_id", title="Indicator time series")
    st.plotly_chart(ts, use_container_width=True)

    def score_at_date(date_value: pd.Timestamp) -> float:
        drows = fdf[fdf["date"] <= date_value]
        lidx = drows.groupby("indicator_id")["date"].idxmax()
        lrows = drows.loc[lidx].to_dict("records")
        return compute_scores(drows.to_dict("records"), lrows)["overall_risk"]

    dates = sorted(fdf["date"].unique())
    trend_df = pd.DataFrame({"date": dates, "overall_risk": [score_at_date(d) for d in dates]})
    st.plotly_chart(px.line(trend_df, x="date", y="overall_risk", title="Score trend"), use_container_width=True)

    cat_df = pd.DataFrame(
        [{"category": k, "score": v} for k, v in score_pack["category_scores"].items()]
    )
    st.plotly_chart(px.bar(cat_df, x="category", y="score", title="Category proxy trends (latest)"), use_container_width=True)

    with st.expander("Explain score"):
        st.write("Category weights")
        st.json(score_pack["weights"])
        st.write("Normalized inputs")
        st.json(score_pack["normalized_inputs"])
        st.write("Top contributors")
        st.dataframe(pd.DataFrame(score_pack["contributors"], columns=["indicator", "risk_score"]).head(10), use_container_width=True)

elif page == "Alerts":
    st.title("Alerts")
    with st.form("create_alert"):
        indicator = st.selectbox("Indicator", sorted(df["indicator_id"].unique().tolist()))
        direction = st.selectbox("Direction", ["above", "below"])
        threshold = st.number_input("Threshold", value=50.0)
        if st.form_submit_button("Save alert rule"):
            add_alert_rule(conn, country, indicator, direction, threshold)
            st.success("Alert rule saved")

    if st.button("Evaluate alerts on latest data"):
        hits = evaluate_alerts(conn, country)
        st.info(f"Triggered alerts: {len(hits)}")

    st.subheader("Triggered alert events")
    st.dataframe(pd.DataFrame(list_alert_events(conn, country)), use_container_width=True)

elif page == "Scenario Simulator":
    st.title("Scenario Simulator")
    shock = st.selectbox("Shock type", ["currency_depreciation", "commodity_price_spike", "conflict_spike"])
    severity = st.slider("Severity (0-100)", min_value=0, max_value=100, value=40)
    horizon = st.slider("Horizon (months)", min_value=1, max_value=24, value=6)

    before = pd.DataFrame(latest_rows)
    after = pd.DataFrame(simulate(latest_rows, shock, severity, horizon))

    before_score = compute_scores(fdf.to_dict("records"), before.to_dict("records"))["overall_risk"]
    after_score = compute_scores(fdf.to_dict("records"), after.to_dict("records"))["overall_risk"]

    merged = before[["indicator_id", "value"]].merge(
        after[["indicator_id", "value"]], on="indicator_id", suffixes=("_before", "_after")
    )
    melted = merged.melt(id_vars=["indicator_id"], var_name="state", value_name="value")
    st.plotly_chart(px.bar(melted, x="indicator_id", y="value", color="state", barmode="group"), use_container_width=True)

    st.metric("Before score", before_score)
    st.metric("After score", after_score)
    record_scenario(conn, country, shock, float(severity), int(horizon))
    st.write(
        f"Scenario narrative: a {shock.replace('_', ' ')} shock (severity {severity}/100, {horizon} months) "
        f"moves overall risk from {before_score:.2f} to {after_score:.2f}."
    )

else:
    st.title("Export")
    export_df = fdf.sort_values(["date", "indicator_id"])
    st.dataframe(export_df, use_container_width=True)
    st.download_button("Download CSV", data=export_df.to_csv(index=False).encode("utf-8"), file_name=f"{country.lower()}_filtered.csv", mime="text/csv")
    st.download_button("Download JSON", data=json.dumps(export_df.to_dict("records"), default=str, indent=2).encode("utf-8"), file_name=f"{country.lower()}_filtered.json", mime="application/json")
