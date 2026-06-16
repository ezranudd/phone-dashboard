import functools
import os
import pandas as pd
from flask import Flask, jsonify, render_template
import io

app = Flask(__name__)

# Load and preprocess data once at startup
df = pd.read_csv("main.csv")

# DATA PREPROCESSING
def preprocess_data():
    global df
    
    # Split resolution column into separate Width and Height columns
    df['width'] = df['resolution'].apply(lambda x: x.split('x')[0]).astype('int64')
    df['height'] = df['resolution'].apply(lambda x: x.split('x')[1]).astype('int64')
    
    # Extract announcement_year from announcement_date column
    df['announcement_year'] = df['announcement_date'].apply(lambda x: x.split('-')[0]).astype('int32')
    
    # Drop announcement_date and resolution columns
    df.drop(columns=['announcement_date', 'resolution'], inplace=True)
    
    # Remove Outliers

    # Remove weight > 450
    Outliers_W = df[df['weight(g)'] > 450]
    df.drop(Outliers_W.index, inplace=True, axis=0)
    df.reset_index(drop=True, inplace=True)
    
    # Correct Storage
    # Realme GT5 240W listed as 1GB storage but actually 1024GB
    if len(df) > 1507:  # Safety check
        df.iloc[1507, 8] = 1024
    
    # Remove price > 1500
    Outliers_P = df[df['price(USD)'] > 1500]
    df.drop(Outliers_P.index, inplace=True, axis=0)
    df.reset_index(drop=True, inplace=True)

# Preprocess data at startup
preprocess_data()

# Home Page (using template)
@app.route("/")
def home():
    
    # Capture df.info()
    buffer = io.StringIO()
    df.info(buf=buffer)
    info_output = buffer.getvalue()
    buffer.close()
    
    # df.describe() output to html with fixed precision
    descr_output = df.describe().to_html(float_format=lambda x: f"{x:.2f}")
    
    return render_template('index.html', 
        dataframe_info=info_output,
        dataframe_describe=descr_output)

# Browse CSV as an html table
@app.route('/browse.html')
def browse():
    # Pandas Display Options
    pd.set_option('display.float_format', '{}'.format)
    
    # Define columns to exclude
    exclude = [
        'video_720p', 'video_1080p', 'video_4K', 'video_8K',
        'video_30fps', 'video_60fps', 'video_120fps', 'video_240fps',
        'video_480fps', 'video_960fps'
    ]
    
    # Create a copy of the dataframe excluding specified columns
    df_filtered = df.drop(columns=[col for col in exclude if col in df.columns])
    
    # Convert filtered csv to html
    table_html = df_filtered.to_html(classes='data', header="true", index=False)
    
    # Return using template
    return render_template('browse.html',
        table_html=table_html)

# Browse CSV as an html table
@app.route('/browse-full.html')
def browsefull():
    # Pandas Display Options
    pd.set_option('display.float_format', '{}'.format)
    
    # Convert csv to html
    table_html = df.to_html(classes='data', header="true", index=False)
    
    # Return using template
    return render_template('browse-full.html',
        table_html=table_html)

@app.route('/browse.json')
def browse_json():
    # Convert DataFrame to list of dictionaries
    data = df.to_dict(orient='records')
    
    # JSONify
    return jsonify(data)

# Aggregated + raw data for client-side Plotly charts.
# df is static after startup, so the payload is constant: build it once and memoize.
@functools.cache
def _charts_payload():
    # --- Aggregates (computed in pandas; awkward to do in JS) ---

    # Brand distribution
    brand_counts = df['brand'].value_counts()

    # OS distribution, grouping rare operating systems into "Other"
    os_threshold = 40
    os_counts = df['os'].value_counts()
    os_main = os_counts[os_counts >= os_threshold]
    os_other = int(os_counts[os_counts < os_threshold].sum())
    os_data = {str(k): int(v) for k, v in os_main.items()}
    if os_other > 0:
        os_data['Other'] = os_other

    # Battery type distribution
    battery_counts = df['battery_type'].value_counts()

    # Video format support (True/False counts per capability)
    video_cols = ['video_720p', 'video_1080p', 'video_4K', 'video_8K',
                  'video_30fps', 'video_60fps', 'video_120fps', 'video_240fps',
                  'video_480fps', 'video_960fps']
    video_data = {}
    for col in video_cols:
        counts = df[col].value_counts()
        video_data[col] = {
            'true': int(counts.get(True, 0)),
            'false': int(counts.get(False, 0)),
        }

    # Average price by brand (sorted high to low)
    avg_price = df.groupby('brand')['price(USD)'].mean().sort_values(ascending=False)

    # Battery efficiency (mAh per USD) by brand — computed without mutating df
    efficiency = (df['battery'] / df['price(USD)'])
    avg_eff = efficiency.groupby(df['brand']).mean().sort_values(ascending=False)

    # Average specs by brand
    spec_cols = ['height', 'ram(GB)', 'storage(GB)', 'weight(g)']
    specs_data = {}
    for spec in spec_cols:
        s = df.groupby('brand')[spec].mean().sort_values(ascending=False)
        specs_data[spec] = {
            'brands': [str(b) for b in s.index],
            'values': [round(float(v), 2) for v in s.values],
        }

    # Correlation matrix for numeric features
    numeric_cols = ['inches', 'battery', 'ram(GB)', 'weight(g)', 'storage(GB)',
                    'price(USD)', 'width', 'height', 'announcement_year']
    corr = df[numeric_cols].corr()

    # Yearly market trends
    releases_by_year = df.groupby('announcement_year').size()
    avg_price_by_year = df.groupby('announcement_year')['price(USD)'].mean()

    # --- Raw arrays (Plotly bins / builds distributions client-side) ---

    # Price by OS for boxplot — reuse the same "major OS" set as the pie's grouping
    # so the two charts can't disagree about which operating systems are major.
    major_os = os_main.index
    box_data = {
        str(os_name): [round(float(p), 2)
                       for p in df[df['os'] == os_name]['price(USD)'].dropna()]
        for os_name in major_os
    }

    # Raw columns for histograms
    hist_cols = numeric_cols
    hist_data = {col: [round(float(v), 4) for v in df[col].dropna()] for col in hist_cols}

    return {
        'brand_counts': {str(k): int(v) for k, v in brand_counts.items()},
        'os_counts': os_data,
        'battery_type_counts': {str(k): int(v) for k, v in battery_counts.items()},
        'video_formats': video_data,
        'avg_price_by_brand': {
            'brands': [str(b) for b in avg_price.index],
            'values': [round(float(v), 2) for v in avg_price.values],
        },
        'battery_efficiency_by_brand': {
            'brands': [str(b) for b in avg_eff.index],
            'values': [round(float(v), 2) for v in avg_eff.values],
        },
        'specs_by_brand': specs_data,
        'correlation': {
            'labels': numeric_cols,
            'matrix': [[round(float(v), 2) for v in row] for row in corr.values],
        },
        'yearly_trends': {
            'years': [str(y) for y in releases_by_year.index],
            'releases': [int(v) for v in releases_by_year.values],
            'avg_price': [round(float(v), 2) for v in avg_price_by_year.values],
        },
        'price_by_os': box_data,
        'histograms': hist_data,
    }


@app.route('/data/charts.json')
def charts_data():
    return jsonify(_charts_payload())


# Modeling-driven insights: what drives price, which phones are best value, and
# how the market segments into tiers. Trained once (df is static) and memoized.
@functools.cache
def _insights_payload():
    import numpy as np
    from sklearn.model_selection import train_test_split, cross_val_predict
    from sklearn.linear_model import LinearRegression
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import make_pipeline
    from sklearn.cluster import KMeans
    from sklearn.metrics import r2_score, mean_absolute_error

    feature_cols = ['inches', 'battery', 'ram(GB)', 'weight(g)', 'storage(GB)',
                    'width', 'height', 'announcement_year']
    model_df = df.dropna(subset=feature_cols + ['price(USD)']).reset_index(drop=True)
    X = model_df[feature_cols]
    y = model_df['price(USD)']

    # --- 1. Price-driver model: compare linear vs random forest, report importance ---
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42)

    linear = make_pipeline(StandardScaler(), LinearRegression())
    linear.fit(X_train, y_train)
    lin_pred = linear.predict(X_test)

    rf = RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1)
    rf.fit(X_train, y_train)
    rf_pred = rf.predict(X_test)

    metrics = {
        'linear': {'r2': round(float(r2_score(y_test, lin_pred)), 3),
                   'mae': round(float(mean_absolute_error(y_test, lin_pred)), 1)},
        'random_forest': {'r2': round(float(r2_score(y_test, rf_pred)), 3),
                          'mae': round(float(mean_absolute_error(y_test, rf_pred)), 1)},
    }

    importance = sorted(
        ({'feature': f, 'importance': round(float(i), 4)}
         for f, i in zip(feature_cols, rf.feature_importances_)),
        key=lambda d: d['importance'], reverse=True)

    pred_vs_actual = {
        'actual': [round(float(v), 2) for v in y_test],
        'predicted': [round(float(v), 2) for v in rf_pred],
    }

    # --- 2. Best-value ranking: out-of-fold residual (predicted - actual). A phone
    #        priced below what its specs predict is good value (positive residual). ---
    oof_pred = cross_val_predict(
        RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1), X, y, cv=5)
    ranked = model_df.assign(
        predicted=oof_pred, residual=oof_pred - y.values
    ).sort_values('residual', ascending=False)

    def value_row(r):
        return {
            'name': str(r['phone_name']),
            'brand': str(r['brand']),
            'actual': round(float(r['price(USD)']), 0),
            'predicted': round(float(r['predicted']), 0),
            'residual': round(float(r['residual']), 0),
        }

    value_ranking = {
        'best': [value_row(r) for _, r in ranked.head(15).iterrows()],
        'worst': [value_row(r) for _, r in ranked.tail(15).iloc[::-1].iterrows()],
    }

    # --- 3. Market tiers via k-means, ordered by mean price -> budget/mid/flagship ---
    cluster_cols = ['price(USD)', 'battery', 'ram(GB)', 'storage(GB)', 'inches', 'weight(g)']
    cluster_df = df.dropna(subset=cluster_cols).reset_index(drop=True)
    scaled = StandardScaler().fit_transform(cluster_df[cluster_cols])
    raw_labels = KMeans(n_clusters=3, random_state=42, n_init=10).fit_predict(scaled)

    # Map raw cluster ids -> tier rank (0=cheapest) by ascending mean price
    order = (cluster_df.assign(c=raw_labels)
             .groupby('c')['price(USD)'].mean().sort_values().index.tolist())
    rank_of = {c: i for i, c in enumerate(order)}
    tier_idx = [rank_of[c] for c in raw_labels]
    tier_names = ['Budget', 'Mid-range', 'Flagship']

    summary = []
    for i, c in enumerate(order):
        grp = cluster_df[raw_labels == c]
        summary.append({
            'tier': tier_names[i],
            'count': int(len(grp)),
            'mean_price': round(float(grp['price(USD)'].mean()), 0),
            'mean_ram': round(float(grp['ram(GB)'].mean()), 1),
            'mean_battery': round(float(grp['battery'].mean()), 0),
            'mean_storage': round(float(grp['storage(GB)'].mean()), 0),
        })

    tiers = {
        'names': tier_names,
        'summary': summary,
        'points': {
            'storage': [round(float(v), 0) for v in cluster_df['storage(GB)']],
            'price': [round(float(v), 2) for v in cluster_df['price(USD)']],
            'tier': tier_idx,
        },
    }

    return {
        'price_model': {'metrics': metrics, 'importance': importance,
                        'pred_vs_actual': pred_vs_actual},
        'value_ranking': value_ranking,
        'tiers': tiers,
    }


@app.route('/data/insights.json')
def insights_data():
    return jsonify(_insights_payload())


if __name__ == '__main__':
    app.run(port=int(os.environ.get('PORT', '5000')))
