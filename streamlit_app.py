from __future__ import annotations

import json
import os
from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from src.alerts import add_alert_rule, evaluate_alerts, list_alert_events
from src.db import get_connection, init_db, query_country_values
from src.ingest import ingest_country
from src.scenarios import record_scenario, simulate
from src.scoring import compute_scores
from src.utils import country_display_name, deterministic_summary, ordered_countries

st.set_page_config(page_title="Food Security Early Warning", layout="wide")

I18N = {
    "EN": {
        "app_title": "Food Security MVP",
        "page": "Page",
        "country": "Country (ISO3)",
        "pinned": "Pinned Countries",
        "demo": "Offline demo mode",
        "ttl": "Cache TTL (hours)",
        "mode": "Ingestion mode",
        "date_range": "Date range",
        "indicators": "Indicators",
        "dashboard": "Country Dashboard",
        "alerts": "Alerts",
        "sim": "Scenario Simulator",
        "export": "Export",
        "overall": "Overall risk (0-100)",
        "food": "Food stress proxy",
        "conflict": "Conflict proxy",
        "macro": "Macro proxy",
        "timeseries": "Indicator time series",
        "score_trend": "Score trend",
        "category_trend": "Category proxy (latest)",
        "explain": "Explain score",
        "weights": "Category weights",
        "normalized": "Normalized inputs",
        "contributors": "Top contributors",
        "provenance": "Dataset provenance",
        "rule_saved": "Alert rule saved",
        "eval_alerts": "Evaluate alerts on latest data",
        "triggered": "Triggered alerts",
        "download_csv": "Download CSV",
        "download_json": "Download JSON",
    },
    "AR": {
        "app_title": "نظام إنذار الأمن الغذائي",
        "page": "الصفحة",
        "country": "الدولة (ISO3)",
        "pinned": "الدول المثبتة",
        "demo": "وضع العرض بدون إنترنت",
        "ttl": "مدة التخزين المؤقت (ساعة)",
        "mode": "وضع جلب البيانات",
        "date_range": "النطاق الزمني",
        "indicators": "المؤشرات",
        "dashboard": "لوحة الدولة",
        "alerts": "التنبيهات",
        "sim": "محاكاة السيناريو",
        "export": "تصدير",
        "overall": "مخاطر كلية (0-100)",
        "food": "مؤشر ضغط الغذاء",
        "conflict": "مؤشر الصراع",
        "macro": "المؤشر الاقتصادي الكلي",
        "timeseries": "سلسلة المؤشرات الزمنية",
        "score_trend": "اتجاه درجة المخاطر",
        "category_trend": "اتجاه الفئات (الأحدث)",
        "explain": "شرح النتيجة",
        "weights": "أوزان الفئات",
        "normalized": "المدخلات المطبعة",
        "contributors": "أبرز المساهمين",
        "provenance": "مصادر البيانات",
        "rule_saved": "تم حفظ قاعدة التنبيه",
        "eval_alerts": "تقييم التنبيهات على أحدث البيانات",
        "triggered": "التنبيهات المفعلة",
        "download_csv": "تنزيل CSV",
        "download_json": "تنزيل JSON",
    },
}

conn = get_connection()
init_db(conn)

st.sidebar.title("🌍 Food Security")
lang = st.sidebar.segmented_control("Language / اللغة", options=["EN", "AR"], default="EN")
T = I18N[lang]

page = st.sidebar.radio(T["page"], [T["dashboard"], T["alerts"], T["sim"], T["export"]])

try:
    demo_country_list = pd.read_csv("data/demo/indicators_values.csv")["country_iso3"].dropna().unique().tolist()
except Exception:
    demo_country_list = ["KEN", "SDN", "YEM"]
country_options = ordered_countries(demo_country_list)
st.sidebar.caption(f"{T['pinned']}: JOR, QAT, USA, SAU, EGY")
country = st.sidebar.selectbox(
    T["country"],
    country_options,
    index=0,
    format_func=lambda iso: country_display_name(iso, lang),
)
demo_mode = st.sidebar.toggle(T["demo"], value=os.getenv("DEMO_MODE", "0") == "1")
ttl_hours = int(st.sidebar.slider(T["ttl"], min_value=1, max_value=168, value=24, step=1))

status = ingest_country(conn, country, demo_mode=demo_mode, ttl_hours=ttl_hours)
st.sidebar.caption(f"{T['mode']}: {status}")

rows = [dict(r) for r in query_country_values(conn, country)]
df = pd.DataFrame(rows)
if df.empty:
    st.warning("No data available.")
    st.stop()

df["date"] = pd.to_datetime(df["date"])
min_date = df["date"].min().date()
max_date = df["date"].max().date()
selected_range = st.sidebar.date_input(T["date_range"], (min_date, max_date), min_value=min_date, max_value=max_date)
if isinstance(selected_range, tuple) and len(selected_range) == 2:
    start_date, end_date = selected_range
else:
    start_date, end_date = min_date, max_date

indicator_options = sorted(df["indicator_id"].unique().tolist())
selected_indicators = st.sidebar.multiselect(T["indicators"], indicator_options, default=indicator_options[: min(5, len(indicator_options))])

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

st.title(f"✨ {T['app_title']}")

if page == T["dashboard"]:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(T["overall"], score_pack["overall_risk"])
    c2.metric(T["food"], round(score_pack["category_scores"].get("food", 0.0), 2))
    c3.metric(T["conflict"], round(score_pack["category_scores"].get("conflict", 0.0), 2))
    c4.metric(T["macro"], round(score_pack["category_scores"].get("macro", 0.0), 2))

    st.info(summary)

    st.plotly_chart(
        px.line(fdf, x="date", y="value", color="indicator_id", title=T["timeseries"]),
        use_container_width=True,
    )

    def score_at_date(date_value: date) -> float:
        drows = fdf[fdf["date"] <= date_value]
        lidx = drows.groupby("indicator_id")["date"].idxmax()
        lrows = drows.loc[lidx].to_dict("records")
        return compute_scores(drows.to_dict("records"), lrows)["overall_risk"]

    dates = sorted(fdf["date"].unique())
    trend_df = pd.DataFrame({"date": dates, "overall_risk": [score_at_date(d) for d in dates]})
    st.plotly_chart(px.area(trend_df, x="date", y="overall_risk", title=T["score_trend"]), use_container_width=True)

    cat_df = pd.DataFrame([{"category": k, "score": v} for k, v in score_pack["category_scores"].items()])
    st.plotly_chart(px.bar(cat_df, x="category", y="score", title=T["category_trend"], color="category"), use_container_width=True)

    with st.expander(T["explain"]):
        st.write(T["weights"])
        st.json(score_pack["weights"])
        st.write(T["normalized"])
        st.json(score_pack["normalized_inputs"])
        st.write(T["contributors"])
        st.dataframe(pd.DataFrame(score_pack["contributors"], columns=["indicator", "risk_score"]).head(10), use_container_width=True)

    with st.expander(T["provenance"]):
        prov = (
            fdf.groupby(["indicator_id", "source", "unit"], as_index=False)
            .agg(records=("value", "count"), first_date=("date", "min"), last_date=("date", "max"))
            .sort_values(["indicator_id", "source"])
        )
        meta = pd.read_sql_query("SELECT indicator_id, source_url FROM indicators_meta ORDER BY indicator_id", conn)
        prov = prov.merge(meta, on="indicator_id", how="left")
        st.dataframe(prov, use_container_width=True)

elif page == T["alerts"]:
    st.subheader(T["alerts"])
    with st.form("create_alert"):
        indicator = st.selectbox("Indicator", sorted(df["indicator_id"].unique().tolist()))
        direction = st.selectbox("Direction", ["above", "below"])
        threshold = st.number_input("Threshold", value=50.0)
        if st.form_submit_button("Save"):
            add_alert_rule(conn, country, indicator, direction, threshold)
            st.success(T["rule_saved"])

    if st.button(T["eval_alerts"]):
        hits = evaluate_alerts(conn, country)
        st.info(f"{T['triggered']}: {len(hits)}")

    st.dataframe(pd.DataFrame(list_alert_events(conn, country)), use_container_width=True)

elif page == T["sim"]:
    st.subheader(T["sim"])
    shock = st.selectbox("Shock", ["currency_depreciation", "commodity_price_spike", "conflict_spike"])
    severity = st.slider("Severity", min_value=0, max_value=100, value=40)
    horizon = st.slider("Horizon (months)", min_value=1, max_value=24, value=6)

    before = pd.DataFrame(latest_rows)
    after = pd.DataFrame(simulate(latest_rows, shock, severity, horizon))
    before_score = compute_scores(fdf.to_dict("records"), before.to_dict("records"))["overall_risk"]
    after_score = compute_scores(fdf.to_dict("records"), after.to_dict("records"))["overall_risk"]

    merged = before[["indicator_id", "value"]].merge(after[["indicator_id", "value"]], on="indicator_id", suffixes=("_before", "_after"))
    melted = merged.melt(id_vars=["indicator_id"], var_name="state", value_name="value")
    st.plotly_chart(px.bar(melted, x="indicator_id", y="value", color="state", barmode="group"), use_container_width=True)

    c1, c2 = st.columns(2)
    c1.metric("Before score", before_score)
    c2.metric("After score", after_score)
    record_scenario(conn, country, shock, float(severity), int(horizon))
    st.write(f"Scenario impact: risk moved from {before_score:.2f} to {after_score:.2f}.")

else:
    st.subheader(T["export"])
    export_df = fdf.sort_values(["date", "indicator_id"])
    st.dataframe(export_df, use_container_width=True)
    st.download_button(T["download_csv"], data=export_df.to_csv(index=False).encode("utf-8"), file_name=f"{country.lower()}_filtered.csv", mime="text/csv")
    st.download_button(T["download_json"], data=json.dumps(export_df.to_dict("records"), default=str, indent=2).encode("utf-8"), file_name=f"{country.lower()}_filtered.json", mime="application/json")
