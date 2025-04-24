import pandas as pd
import numpy as np
from flask import Flask, request, jsonify, send_file, render_template
import matplotlib
matplotlib.use('Agg')  # Non-gui for use with flask
import matplotlib.pyplot as plt
import io

app = Flask(__name__)
df = pd.read_csv("main.csv")

# Home Page (using template)
@app.route("/")
def home():
    # Capture df.info() output
    buffer = io.StringIO()
    df.info(buf=buffer)
    info_output = buffer.getvalue()
    buffer.close()

    # df.describe() output to html
    descr_output = df.describe().to_html()

    return render_template('index.html', 
        dataframe_info=info_output, 
        dataframe_describe=descr_output)

# Browse CSV as an html table
@app.route('/browse.html')
def browse():
    # Pandas Display Options
    pd.set_option('display.float_format', '{}'.format)
    
    # Convert csv to html
    table_html = df.to_html(classes='data', header="true", index=False)
    
    # Return using template
    return render_template('browse.html',
        table_html=table_html)

@app.route('/browse.json')
def browse_json():
    # Convert DataFrame to list of dictionaries
    data = df.to_dict(orient='records')
    
    # JSONify
    return jsonify(data)

@app.route('/price_rating.svg')
def price_rating():
    plt.figure(figsize=(12, 8))
    
    # Scatter Plot: Price vs Rating (colored by Brand)
    brands = df['Brand'].unique()
    colors = plt.cm.tab20(np.linspace(0, 1, len(brands)))
    
    for i, brand in enumerate(brands):
        brand_data = df[df['Brand'] == brand]
        plt.scatter(
            brand_data['Price (USD)'], 
            brand_data['Rating'], 
            color=colors[i], 
            label=brand, 
            s=100,  # Size of the marker
            alpha=0.7  # Transparency
        )
    
    # Horizontal line at average rating
    avg_rating = df['Rating'].mean()
    plt.axhline(y=avg_rating, color='gray', linestyle='--', alpha=0.7, 
        label=f'Avg Rating: {avg_rating:.2f}')
    
    # Trend Line
    z = np.polyfit(df['Price (USD)'], df['Rating'], 1)
    p = np.poly1d(z)
    plt.plot(df['Price (USD)'].sort_values(), 
        p(df['Price (USD)'].sort_values()), 
        "r--", alpha=0.7, 
        label=f'Trend line')
    
    # Configure Plot
    plt.title('Smartphone Price vs Rating by Brand', fontsize=16)
    plt.xlabel('Price (USD)', fontsize=12)
    plt.ylabel('Rating (out of 5)', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.legend(loc='best')
    
    # y-axis limits
    plt.ylim(3.0, 5.0)
    
    # Save plot to bytes buffer
    buffer = io.BytesIO()
    plt.savefig(buffer, format='svg', bbox_inches='tight')
    buffer.seek(0)
    plt.close()
    
    # Return SVG
    return send_file(buffer, mimetype='image/svg+xml')

@app.route('/brand_pie.svg')
def brand_pie():
    # Count phones by brand
    brand_counts = df['Brand'].value_counts()
    
    # Create figure and axis
    plt.figure(figsize=(10, 8))
    
    # Create pie chart
    plt.pie(
        brand_counts, 
        labels=brand_counts.index,
        autopct='%1.1f%%',  # Show percentages
        startangle=90,      # Start angle
        shadow=False,       # No shadow
        explode=[0.05] * len(brand_counts),  # Slightly explode all slices
        textprops={'fontsize': 12},  # Font size for labels
        colors=plt.cm.tab20(np.linspace(0, 1, len(brand_counts)))  # Using tab20 colormap
    )
    # Equal aspect ratio ensures the pie chart is circular
    plt.axis('equal')
    
    # Add title
    plt.title('Smartphone Distribution by Brand', fontsize=16)
    
    # Add legend with counts - Moved to the right side outside the pie chart
    legend_labels = [f"{brand} ({count})" for brand, count in zip(brand_counts.index, brand_counts)]
    plt.legend(legend_labels, loc='center right', bbox_to_anchor=(1.25, 0.5), fontsize=10)
    
    # Save plot to bytes buffer
    buffer = io.BytesIO()
    plt.savefig(buffer, format='svg', bbox_inches='tight')
    buffer.seek(0)
    plt.close()
    
    # Return SVG
    return send_file(buffer, mimetype='image/svg+xml')

@app.route('/brand_bar.svg')
def brand_bar():
    # Count phones by brand
    brand_counts = df['Brand'].value_counts()
    
    # Create figure and axis with adjusted figsize for bar chart
    plt.figure(figsize=(10, 8))
    
    # Create horizontal bar chart
    bars = plt.barh(
        brand_counts.index,
        brand_counts,
        color=plt.cm.tab20(np.linspace(0, 1, len(brand_counts))),
        alpha=0.8
    )
    
    # Add count labels to the end of each bar
    for bar in bars:
        width = bar.get_width()
        plt.text(
            width + 2,                 # x position (slightly offset from end of bar)
            bar.get_y() + bar.get_height()/2,  # y position (middle of bar)
            f'{int(width)}',           # label text (count as integer)
            ha='left',                 # horizontal alignment
            va='center',               # vertical alignment
            fontsize=10                # font size
        )
    
    # Add labels and title
    plt.xlabel('Number of Phones', fontsize=12)
    plt.ylabel('Brand', fontsize=12)
    plt.title('Smartphone Counts by Brand', fontsize=16)
    
    # Add grid lines for better readability
    plt.grid(axis='x', linestyle='--', alpha=0.7)
    
    # Adjust layout to ensure all elements fit properly
    plt.tight_layout()
    
    # Save plot to bytes buffer
    buffer = io.BytesIO()
    plt.savefig(buffer, format='svg', bbox_inches='tight')
    buffer.seek(0)
    plt.close()
    
    # Return SVG
    return send_file(buffer, mimetype='image/svg+xml')

@app.route('/price_histogram.svg')
def price_histogram():
    plt.figure(figsize=(12, 8))
    
    # Create histogram of phone prices
    plt.hist(
        df['Price (USD)'], 
        bins=25,           # Number of bins
        color='teal',
        alpha=0.7,
        edgecolor='black'
    )
    
    # Configure Plot
    plt.title('Smartphone Price Distribution', fontsize=16)
    plt.xlabel('Price (USD)', fontsize=12)
    plt.ylabel('Number of Phones', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.legend(loc='upper right')
    
    # Save plot to bytes buffer
    buffer = io.BytesIO()
    plt.savefig(buffer, format='svg', bbox_inches='tight')
    buffer.seek(0)
    plt.close()
    
    # Return SVG
    return send_file(buffer, mimetype='image/svg+xml')

@app.route('/rating_histogram.svg')
def rating_histogram():
    plt.figure(figsize=(12, 8))
    
    # Create histogram of phone ratings
    plt.hist(
        df['Rating'], 
        bins=20,           # Number of bins
        color='teal',
        alpha=0.7,
        edgecolor='black',
        range=(3.0, 5.0)   # Range to match ylim in price_rating chart
    )
    
    # Configure Plot
    plt.title('Smartphone Rating Distribution', fontsize=16)
    plt.xlabel('Rating (out of 5)', fontsize=12)
    plt.ylabel('Number of Phones', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.legend(loc='upper left')
    
    # Save plot to bytes buffer
    buffer = io.BytesIO()
    plt.savefig(buffer, format='svg', bbox_inches='tight')
    buffer.seek(0)
    plt.close()
    
    # Return SVG
    return send_file(buffer, mimetype='image/svg+xml')

@app.route('/platform_pie.svg')
def platform_pie():
    # Count phones by selling platform
    platform_counts = df['Selling Platform'].value_counts()
    
    # Create figure and axis
    plt.figure(figsize=(10, 8))
    
    # Create pie chart
    plt.pie(
        platform_counts, 
        labels=platform_counts.index,
        autopct='%1.1f%%',  # Show percentages
        startangle=90,      # Start angle
        shadow=False,       # No shadow
        explode=[0.05] * len(platform_counts),  # Slightly explode all slices
        textprops={'fontsize': 12},  # Font size for labels
        colors=plt.cm.tab20(np.linspace(0, 1, len(platform_counts)))  # Using tab20 colormap
    )
    # Equal aspect ratio ensures the pie chart is circular
    plt.axis('equal')
    
    # Add title
    plt.title('Smartphone Distribution by Selling Platform', fontsize=16)
    
    # Add legend with counts - Moved to the right side outside the pie chart
    legend_labels = [f"{platform} ({count})" for platform, count in zip(platform_counts.index, platform_counts)]
    plt.legend(legend_labels, loc='center right', bbox_to_anchor=(1.25, 0.5), fontsize=10)
    
    # Save plot to bytes buffer
    buffer = io.BytesIO()
    plt.savefig(buffer, format='svg', bbox_inches='tight')
    buffer.seek(0)
    plt.close()
    
    # Return SVG
    return send_file(buffer, mimetype='image/svg+xml')

# Run App
if __name__ == '__main__':
    with app.app_context():
        # Generate and save price_rating.svg
        response = app.test_client().get('/price_rating.svg')
        with open('static/images/price_rating.svg', 'wb') as f:
            f.write(response.data)
            
        # Generate and save brand_pie.svg
        response = app.test_client().get('/brand_pie.svg')
        with open('static/images/brand_pie.svg', 'wb') as f:
            f.write(response.data)

        # Generate and save brand_pie.svg
        response = app.test_client().get('/brand_bar.svg')
        with open('static/images/brand_bar.svg', 'wb') as f:
            f.write(response.data)

        # Generate and save price_histogram.svg
        response = app.test_client().get('/price_histogram.svg')
        with open('static/images/price_histogram.svg', 'wb') as f:
            f.write(response.data)

        # Generate and save rating_histogram.svg
        response = app.test_client().get('/rating_histogram.svg')
        with open('static/images/rating_histogram.svg', 'wb') as f:
            f.write(response.data)

        # Generate and save platform_pie.svg
        response = app.test_client().get('/platform_pie.svg')
        with open('static/images/platform_pie.svg', 'wb') as f:
            f.write(response.data)
            
    app.run()