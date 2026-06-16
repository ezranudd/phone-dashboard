# Phone Dashboard

This is a Flask application for analyzing a smartphone dataset with pandas and scikit-learn.
Beyond describing the data, it answers two questions — **what drives phone price** and
**which phones are the best value** — through a price-prediction model, a value ranking,
and market-tier clustering. It provides an interactive web interface with tabbed analysis
views, summary statistics, interactive Plotly charts, and DataTables-powered table browsing.

Dataset source: https://www.kaggle.com/datasets/berkayeserr/phone-prices

## What This Project Does

- Loads and preprocesses smartphone data from `main.csv`
- Computes dataset diagnostics (`df.info()` and `df.describe()`)
- Computes chart aggregates in pandas and serves them as JSON (`/data/charts.json`)
- Trains models (scikit-learn) for price drivers, best-value ranking, and tier
  clustering, served as JSON (`/data/insights.json`)
- Renders interactive charts client-side with Plotly (hover, zoom, legend toggle, dropdown selectors)
- Exposes browse views in HTML and JSON
- Adds interactive browse tables (search, sort, pagination, horizontal scroll)
- Leads with a hero + KPI strip (live numbers from the models) and organizes
  analysis into a narrative arc of front-page tabs:
  - `The Market` — how the dataset splits (tiers, brands, OS, trends)
  - `Why Price?` — price-driver model, accuracy, correlations
  - `Best Value` — value ranking, price spread, efficiency
  - `Explore` — supporting distributions, feature detail, and methodology

## Tech Stack

- Python 3
- Flask
- pandas
- scikit-learn (price model, value ranking, k-means tiers)
- Plotly.js (CDN, dashboard charts)
- jQuery (CDN, browse pages)
- DataTables.net (CDN, browse pages)

## Architecture

The Flask backend is a thin data layer. It computes chart aggregates in pandas
(`/data/charts.json`) and trains the models once at startup, serving their results
as JSON (`/data/insights.json`); both payloads are memoized since `df` is static.
The browser fetches both, merges them, and builds every chart with Plotly
(`static/js/charts.js`). Charts render lazily the first time their tab/`<details>`
container becomes visible, which avoids Plotly's zero-width render problem inside
hidden containers.

### Modeling (`/data/insights.json`)

- **Price drivers** — a `RandomForestRegressor` and a standardized `LinearRegression`
  predict `price(USD)` from numeric specs; reported with held-out R²/MAE and the
  forest's feature importances. (Specs alone explain only part of price — brand and
  positioning, analysed elsewhere, account for much of the rest.)
- **Best value** — each phone's out-of-fold residual (`predicted − actual`, via
  `cross_val_predict`) ranks phones by how far below their spec-predicted price they sell.
- **Market tiers** — `KMeans` (k=3) on standardized specs + price, ordered by mean
  price into Budget / Mid-range / Flagship.

### Design decisions (the "why")

- **Client-side Plotly over server-rendered images.** Charts are interactive
  (hover, zoom, dropdowns) and the backend stays a thin JSON layer with no
  plotting dependency, which also keeps it static-host friendly.
- **Lazy render to dodge a real gotcha.** Plotly draws at zero width inside a
  hidden tab or collapsed `<details>`. The render manager (`charts.js`) draws a
  chart only when its container first becomes visible and resizes it on later
  reveals — solved once in shared code, so every chart inherits it.
- **Train once, memoize.** `df` is static after startup, so both JSON payloads
  are constant; `functools.cache` makes each endpoint a one-time computation
  rather than per-request work.
- **"Value" = model residual, not an arbitrary score.** Ranking phones by how far
  their price sits below the model's spec-based prediction reuses the price model
  and is defensible, rather than hand-weighting specs into a made-up index.

## Project Structure

- `main.py`: Flask app, preprocessing logic, route handlers, chart-data aggregation
- `main.csv`: dataset input file
- `templates/index.html`: dashboard landing page with tabbed analysis UI
- `templates/browse.html`: partial-column interactive data table view
- `templates/browse-full.html`: full-column interactive data table view
- `static/css/main.css`: global dashboard styling (Warm Editorial design tokens as CSS variables)
- `static/js/charts.js`: client-side Plotly chart builders, shared theme, KPI wiring, lazy-render manager
- `design/`: Claude Design component library — `tokens.css` (source of truth for the palette) and component previews, kept in sync with the claude.ai/design project
- `tests/test_endpoints.py`: fast endpoint + data-contract tests (pytest)
- `verify_charts.py`: Playwright check that all charts render (optional, dev-only)
- `requirements.txt` / `requirements-dev.txt`: runtime and dev dependencies

## Data Preprocessing

The app applies these transformations at startup:

1. Splits `resolution` into numeric `width` and `height`
2. Extracts `announcement_year` from `announcement_date`
3. Drops `resolution` and `announcement_date`
4. Removes extreme outliers:
   - `weight(g) > 450`
   - `price(USD) > 1500`
5. Corrects a known storage anomaly for one record

## Included Analysis

Current visuals:

- Brand distribution pie chart
- OS distribution pie chart
- Battery type distribution
- Video format support counts
- Average price by brand
- Battery efficiency by brand
- Average specs by brand
- Combined feature histograms
- Yearly release/price trend charts
- Price distribution by OS (boxplot)
- Numeric feature correlation heatmap
- Price-driver model: feature importance + predicted-vs-actual (Advanced Analysis)
- Best-value phone ranking (Brand & Value)
- Market-tier clustering: storage-vs-price scatter + tier profile table (Distributions)

## Run Locally

### 1. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

Charts load Plotly.js from a CDN, so no plotting library is needed server-side.
To run the tests as well, install the dev extras and the browser for the render gate:

```bash
pip install -r requirements-dev.txt
playwright install chromium
```

### 3. Start the app

```bash
python3 main.py
```

The app runs at:

- `http://127.0.0.1:5000/`

## Deploy

The app is a Python/Flask server (it trains the models and serves the JSON the
charts fetch), so it needs a Python runtime — a static host alone won't work.
A `Procfile` and `gunicorn` (in `requirements.txt`) make it deployable to any
Procfile-aware PaaS:

```
web: gunicorn main:app --bind 0.0.0.0:${PORT:-5000}
```

On **Render** (free tier): create a Web Service from this repo with build command
`pip install -r requirements.txt` and start command `gunicorn main:app --bind 0.0.0.0:$PORT`.
The platform injects `$PORT`; `main.py`'s built-in `app.run()` is for local use only.

The models train lazily on first request and are memoized (`functools.cache`),
so the first hit after a cold start does the modeling work once, then every
later request is served from cache.

## Tests

Run from the repo root:

```bash
python -m pytest        # fast endpoint + data-contract checks (no browser)
python verify_charts.py # browser render gate: all 16 charts paint (needs Chromium)
```

`tests/test_endpoints.py` checks the JSON the frontend depends on (status, keys,
JSON-serializability, tier price-ordering, value-ranking order, sane model
metrics). It's deterministic because the models fix `random_state=42`.
`verify_charts.py` drives headless Chromium to confirm every chart actually
renders across tabs and inside collapsed `<details>`.

## Main Routes

- `/`: dashboard home
- `/data/charts.json`: aggregated + raw data powering the descriptive charts
- `/data/insights.json`: model outputs (price drivers, value ranking, tiers)
- `/browse.html`: partial interactive table view (DataTables)
- `/browse-full.html`: full interactive table view (DataTables)
- `/browse.json`: dataset as JSON

## Notes

- All dashboard charts are rendered client-side by Plotly from `/data/charts.json`.
- `df.describe()` values on the dashboard are formatted to 2 decimal places.
- Browse pages include direct links for `Home`, dataset source, and switching between partial/full table views.
- Browse tables use DataTables with client-side search, sorting, pagination, and horizontal scrolling.
