# Phone Dashboard

This is a Flask application for analyzing a smartphone dataset with pandas and matplotlib.
It provides an interactive web interface with tabbed analysis views, summary statistics, and full-table browsing.

Dataset source: https://www.kaggle.com/datasets/berkayeserr/phone-prices

## What This Project Does

- Loads and preprocesses smartphone data from `main.csv`
- Computes dataset diagnostics (`df.info()` and `df.describe()`)
- Generates static SVG visualizations for fast dashboard rendering
- Exposes browse views in HTML and JSON
- Organizes analysis into front-page tabs:
  - `Overview`
  - `Distributions`
  - `Brand & Value`
  - `Advanced Analysis`

## Tech Stack

- Python 3
- Flask
- pandas
- numpy
- matplotlib

## Project Structure

- `main.py`: Flask app, preprocessing logic, route handlers, chart generation
- `main.csv`: dataset input file
- `templates/index.html`: dashboard landing page with tabbed analysis UI
- `templates/browse.html`: partial-column data table view
- `templates/browse-full.html`: full-column data table view
- `static/css/main.css`: global dashboard styling
- `static/images/*.svg`: generated chart assets

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
pip install flask pandas numpy matplotlib
```

### 3. Start the app

```bash
python3 main.py
```

The app runs at:

- `http://127.0.0.1:5000/`

## Main Routes

- `/`: dashboard home
- `/browse.html`: partial table view
- `/browse-full.html`: full table view
- `/browse.json`: dataset as JSON

Chart endpoints (examples):

- `/brand_pie.svg`
- `/os_pie.svg`
- `/histograms.svg`
- `/correlation_heatmap.svg`
- `/yearly_trends.svg`
- `/price_by_os_boxplot.svg`

## Notes

- On startup, the app uses Flask's test client to regenerate chart SVGs into `static/images/`.
- `df.describe()` values on the dashboard are formatted to 2 decimal places.
- Wide tables are wrapped in horizontal-scroll containers to avoid page overflow.
