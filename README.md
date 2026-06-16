# Phone Dashboard

This is a Flask application for analyzing a smartphone dataset with pandas.
It provides an interactive web interface with tabbed analysis views, summary statistics,
interactive Plotly charts, and DataTables-powered table browsing.

Dataset source: https://www.kaggle.com/datasets/berkayeserr/phone-prices

## What This Project Does

- Loads and preprocesses smartphone data from `main.csv`
- Computes dataset diagnostics (`df.info()` and `df.describe()`)
- Computes chart aggregates in pandas and serves them as JSON (`/data/charts.json`)
- Renders interactive charts client-side with Plotly (hover, zoom, legend toggle, dropdown selectors)
- Exposes browse views in HTML and JSON
- Adds interactive browse tables (search, sort, pagination, horizontal scroll)
- Organizes analysis into front-page tabs:
  - `Overview`
  - `Distributions`
  - `Brand & Value`
  - `Advanced Analysis`

## Tech Stack

- Python 3
- Flask
- pandas
- Plotly.js (CDN, dashboard charts)
- jQuery (CDN, browse pages)
- DataTables.net (CDN, browse pages)

## Architecture

The Flask backend is a thin data layer: it computes chart aggregates in pandas and
exposes them as JSON at `/data/charts.json`. The browser fetches that payload once and
builds every chart with Plotly (`static/js/charts.js`). Charts render lazily the first
time their tab/`<details>` container becomes visible, which avoids Plotly's zero-width
render problem inside hidden containers.

## Project Structure

- `main.py`: Flask app, preprocessing logic, route handlers, chart-data aggregation
- `main.csv`: dataset input file
- `templates/index.html`: dashboard landing page with tabbed analysis UI
- `templates/browse.html`: partial-column interactive data table view
- `templates/browse-full.html`: full-column interactive data table view
- `static/css/main.css`: global dashboard styling
- `static/js/charts.js`: client-side Plotly chart builders + lazy-render manager
- `verify_charts.py`: Playwright check that all charts render (optional, dev-only)

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

## Run Locally

### 1. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install flask pandas
```

Charts load Plotly.js from a CDN, so no plotting library is needed server-side.
For the optional render check, also install `playwright` and run `playwright install chromium`.

### 3. Start the app

```bash
python3 main.py
```

The app runs at:

- `http://127.0.0.1:5000/`

## Main Routes

- `/`: dashboard home
- `/data/charts.json`: aggregated + raw data powering every dashboard chart
- `/browse.html`: partial interactive table view (DataTables)
- `/browse-full.html`: full interactive table view (DataTables)
- `/browse.json`: dataset as JSON

## Notes

- All dashboard charts are rendered client-side by Plotly from `/data/charts.json`.
- `df.describe()` values on the dashboard are formatted to 2 decimal places.
- Browse pages include direct links for `Home`, dataset source, and switching between partial/full table views.
- Browse tables use DataTables with client-side search, sorting, pagination, and horizontal scrolling.
