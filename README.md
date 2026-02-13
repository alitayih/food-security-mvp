# Food Security Early Warning - Public Streamlit MVP

Deploy-ready Streamlit app for geopolitics-informed food security monitoring.

## Deploy in 3 minutes (Streamlit Community Cloud - public URL)

1. Push this repo to GitHub.
2. Open Streamlit Community Cloud -> **New app** -> select repo/branch.
3. Set **Main file path** to `streamlit_app.py` and deploy.

That is enough for a public URL. No end-user installation required.

---

## What the app includes

- **Country Dashboard**
  - Sidebar filters: country ISO3, date range, indicator selector
  - Summary cards: overall risk + food/conflict/macro proxies
  - Charts: indicator time series, category proxy chart, score trend
  - Explainability expander (weights, normalized inputs, top contributors)
- **Alerts**
  - Create above/below threshold rules and evaluate against latest data
- **Scenario Simulator**
  - Shocks: `currency_depreciation`, `commodity_price_spike`, `conflict_spike`
  - Outputs adjusted indicators and before/after risk score
- **Export**
  - Download filtered data as CSV/JSON

## Reliability and demo mode

- App works without API keys.
- Uses 2 no-key public sources:
  - World Bank API
  - OWID undernourishment dataset
- Uses bundled demo conflict + fallback demo data under `data/demo`.
- Ingestion failures automatically fall back to demo values.
- Disk cache with TTL + retry/backoff for API calls.

Force demo mode:

```bash
DEMO_MODE=1 streamlit run streamlit_app.py
```

## Local run (optional)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Optional Hugging Face Spaces deployment (public)

1. Create a new Space (SDK = Streamlit).
2. Push this repo into the Space.
3. Ensure `streamlit_app.py` remains at repo root.
4. Space builds from `requirements.txt` and exposes a public URL.

## Streamlit secrets / env vars

No secrets are required for baseline operation.
Optional values can be added in Streamlit Cloud **Advanced settings -> Secrets**:

```toml
OPENAI_API_KEY=""
```

`.env.example` includes optional env placeholders only.

## SQLite unified schema

Database path:
- default: `./app_data/food_security.db`
- fallback (if not writable): `/tmp/app_data/food_security.db`

Tables:
- `indicators_meta(indicator_id, indicator_name, category, unit, source, source_url)`
- `indicators_values(country_iso3, date, indicator_id, value, unit, source, last_updated)`
- `alerts(alert_id, country_iso3, indicator_id, direction, threshold, created_at)`
- `alert_events(event_id, alert_id, triggered_at, observed_value, date)`

## Add a new indicator/source

1. Add indicator metadata in `data/demo/indicators_meta.csv`.
2. Implement fetch logic in one of:
   - `src/sources_worldbank.py`
   - `src/sources_food.py`
   - `src/sources_conflict.py`
3. Ensure ingestion mapping exists in `src/ingest.py`.
4. Ensure new indicator appears in score logic and category mapping in `src/scoring.py`.
5. Add tests under `tests/`.

## Project structure

- `streamlit_app.py`
- `src/db.py`
- `src/cache.py`
- `src/sources_worldbank.py`
- `src/sources_food.py`
- `src/sources_conflict.py`
- `src/ingest.py`
- `src/scoring.py`
- `src/alerts.py`
- `src/scenarios.py`
- `src/utils.py`
- `data/demo/`
- `tests/`
- `.github/workflows/ci.yml`

## Troubleshooting

- **App fails to fetch APIs**: switch on Demo Mode in sidebar (or set `DEMO_MODE=1`).
- **No write permission in app_data**: app auto-falls back to `/tmp/app_data`.
- **Cold starts on hosted platform**: keep dependencies minimal and avoid heavy datasets.

## CI

GitHub Actions runs:
- `ruff check .`
- `pytest -q`
