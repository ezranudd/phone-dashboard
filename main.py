import pandas as pd
import numpy as np
from flask import Flask, request, jsonify, send_file, render_template
import matplotlib
matplotlib.use('Agg')  # Non-gui for use with flask
import matplotlib.pyplot as plt
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
    Outliers_W = df[df['weight(g)'] > 450]
    df.drop(Outliers_W.index, inplace=True, axis=0)
    df.reset_index(drop=True, inplace=True)
    
    # Correct Storage
    if len(df) > 1507:  # Safety check
        df.iloc[1507, 8] = 1024
    
    Outliers_P = df[df['price(USD)'] > 1500]
    df.drop(Outliers_P.index, inplace=True, axis=0)
    df.reset_index(drop=True, inplace=True)

# Preprocess data at startup
preprocess_data()

# Home Page (using template)
@app.route("/")
def home():
    # Capture initial df.info() - we'll simulate this since we already preprocessed
    buffer = io.StringIO()
    df.info(buf=buffer)
    info_output_1 = "Initial data info (preprocessed at startup)"
    
    # Since preprocessing is already done, just capture current state
    buffer = io.StringIO()
    df.info(buf=buffer)
    info_output_2 = buffer.getvalue()
    buffer.close()
    
    buffer = io.StringIO()
    df.info(buf=buffer)
    info_output_3 = buffer.getvalue()
    buffer.close()
    
    # df.describe() output to html
    descr_output = df.describe().to_html()
    
    return render_template('index.html', 
        dataframe_info_1=info_output_1,
        dataframe_info_2=info_output_2,
        dataframe_info_3=info_output_3,
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

@app.route('/brand_pie.svg')
def brand_pie():
    # Count phones by brand
    brand_counts = df['brand'].value_counts()
    
    # Create figure and axis
    plt.figure(figsize=(10, 8))

    # Define a threshold for small slices (e.g., less than 3%)
    total_count = brand_counts.sum()
    threshold_pct = 3.5

    # Separate labels and percentages for better control
    def autopct_format(pct):
        if pct < threshold_pct:
            return ''  # Don't show percentage for very small slices
        return f'{pct:.1f}%'

    # Create custom labels - only show brand names for larger slices
    labels = []
    for i, (brand, count) in enumerate(brand_counts.items()):
        pct = (count / total_count) * 100
        if pct >= threshold_pct:
            labels.append(brand)
        else:
            labels.append('')  # Empty label for small slices
    
    # Create pie chart
    wedges, texts, autotexts = plt.pie(
        brand_counts, 
        labels=labels,
        autopct=autopct_format,  # Show percentages
        startangle=90,      # Start angle
        shadow=False,       # No shadow
        explode=[0.05] * len(brand_counts),  # Slightly explode all slices
        textprops={'fontsize': 12},  # Font size for labels
        colors=plt.cm.tab20(np.linspace(0, 1, len(brand_counts)))  # Using tab20 colormap
    )
    
    # Set percentage text color to white
    for autotext in autotexts:
        autotext.set_color('white')
    
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

@app.route('/os_pie.svg')
def os_pie():
    # Count phones by operating system
    os_counts = df['os'].value_counts()
    
    # Group categories with count < 10 into "Other"
    threshold_count = 40
    filtered_counts = {}
    other_count = 0
    
    for os, count in os_counts.items():
        if count >= threshold_count:
            filtered_counts[os] = count
        else:
            other_count += count
    
    # Add "Other" category if there are any small categories
    if other_count > 0:
        filtered_counts['Other'] = other_count
    
    # Convert back to Series for consistency with original code
    os_counts = pd.Series(filtered_counts)
    
    # Create figure and axis
    plt.figure(figsize=(10, 8))

    # Define a threshold for small slices (e.g., less than 3%)
    total_count = os_counts.sum()
    threshold_pct = 3.5

    # Separate labels and percentages for better control
    def autopct_format(pct):
        if pct < threshold_pct:
            return ''  # Don't show percentage for very small slices
        return f'{pct:.1f}%'

    # Create custom labels - only show OS names for larger slices
    labels = []
    for i, (os, count) in enumerate(os_counts.items()):
        pct = (count / total_count) * 100
        if pct >= threshold_pct:
            labels.append(os)
        else:
            labels.append('')  # Empty label for small slices
    
    # Create pie chart
    wedges, texts, autotexts = plt.pie(
        os_counts, 
        labels=labels,
        autopct=autopct_format,  # Show percentages
        startangle=90,      # Start angle
        shadow=False,       # No shadow
        explode=[0.05] * len(os_counts),  # Slightly explode all slices
        textprops={'fontsize': 12},  # Font size for labels
        colors=plt.cm.tab20(np.linspace(0, 1, len(os_counts)))  # Using tab20 colormap
    )

    # Set percentage text color to white
    for autotext in autotexts:
        autotext.set_color('white')
    
    # Customize the chart
    plt.title('Smartphone Distribution by Operating System', fontsize=16)
    plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle

    # Add legend with counts - Moved to the right side outside the pie chart
    legend_labels = [f"{os} ({count})" for os, count in zip(os_counts.index, os_counts)]
    plt.legend(legend_labels, loc='center right', bbox_to_anchor=(1.25, 0.5), fontsize=10)
    
    # Save to BytesIO object
    buffer = io.BytesIO()
    plt.savefig(buffer, format='svg', bbox_inches='tight')
    buffer.seek(0)
    plt.close()  # Close the figure to free memory
    
    # Return SVG
    return send_file(buffer, mimetype='image/svg+xml')

@app.route('/histogram_inches.svg')
def histogram_inches():
    plt.figure(figsize=(10, 6))
    plt.hist(df['inches'].dropna(), bins=30, color='skyblue', alpha=0.7, edgecolor='black')
    plt.title('Distribution of Screen Size (inches)', fontsize=16)
    plt.xlabel('Screen Size (inches)', fontsize=12)
    plt.ylabel('Frequency', fontsize=12)
    plt.grid(True, alpha=0.3)
    
    # Save plot to bytes buffer
    buffer = io.BytesIO()
    plt.savefig(buffer, format='svg', bbox_inches='tight')
    buffer.seek(0)
    plt.close()
    
    return send_file(buffer, mimetype='image/svg+xml')

@app.route('/histogram_battery.svg')
def histogram_battery():
    plt.figure(figsize=(10, 6))
    plt.hist(df['battery'].dropna(), bins=30, color='lightgreen', alpha=0.7, edgecolor='black')
    plt.title('Distribution of Battery Capacity (mAh)', fontsize=16)
    plt.xlabel('Battery Capacity (mAh)', fontsize=12)
    plt.ylabel('Frequency', fontsize=12)
    plt.grid(True, alpha=0.3)
    
    # Save plot to bytes buffer
    buffer = io.BytesIO()
    plt.savefig(buffer, format='svg', bbox_inches='tight')
    buffer.seek(0)
    plt.close()
    
    return send_file(buffer, mimetype='image/svg+xml')

@app.route('/histogram_ram.svg')
def histogram_ram():
    plt.figure(figsize=(10, 6))
    plt.hist(df['ram(GB)'].dropna(), bins=20, color='lightcoral', alpha=0.7, edgecolor='black')
    plt.title('Distribution of RAM (GB)', fontsize=16)
    plt.xlabel('RAM (GB)', fontsize=12)
    plt.ylabel('Frequency', fontsize=12)
    plt.grid(True, alpha=0.3)
    
    # Save plot to bytes buffer
    buffer = io.BytesIO()
    plt.savefig(buffer, format='svg', bbox_inches='tight')
    buffer.seek(0)
    plt.close()
    
    return send_file(buffer, mimetype='image/svg+xml')

@app.route('/histogram_weight.svg')
def histogram_weight():
    plt.figure(figsize=(10, 6))
    plt.hist(df['weight(g)'].dropna(), bins=25, color='gold', alpha=0.7, edgecolor='black')
    plt.title('Distribution of Weight (g)', fontsize=16)
    plt.xlabel('Weight (g)', fontsize=12)
    plt.ylabel('Frequency', fontsize=12)
    plt.grid(True, alpha=0.3)
    
    # Save plot to bytes buffer
    buffer = io.BytesIO()
    plt.savefig(buffer, format='svg', bbox_inches='tight')
    buffer.seek(0)
    plt.close()
    
    return send_file(buffer, mimetype='image/svg+xml')

@app.route('/histogram_storage.svg')
def histogram_storage():
    plt.figure(figsize=(10, 6))
    plt.hist(df['storage(GB)'].dropna(), bins=25, color='mediumpurple', alpha=0.7, edgecolor='black')
    plt.title('Distribution of Storage (GB)', fontsize=16)
    plt.xlabel('Storage (GB)', fontsize=12)
    plt.ylabel('Frequency', fontsize=12)
    plt.grid(True, alpha=0.3)
    
    # Save plot to bytes buffer
    buffer = io.BytesIO()
    plt.savefig(buffer, format='svg', bbox_inches='tight')
    buffer.seek(0)
    plt.close()
    
    return send_file(buffer, mimetype='image/svg+xml')

@app.route('/histogram_price.svg')
def histogram_price():
    plt.figure(figsize=(10, 6))
    plt.hist(df['price(USD)'].dropna(), bins=30, color='orange', alpha=0.7, edgecolor='black')
    plt.title('Distribution of Price (USD)', fontsize=16)
    plt.xlabel('Price (USD)', fontsize=12)
    plt.ylabel('Frequency', fontsize=12)
    plt.grid(True, alpha=0.3)
    
    # Save plot to bytes buffer
    buffer = io.BytesIO()
    plt.savefig(buffer, format='svg', bbox_inches='tight')
    buffer.seek(0)
    plt.close()
    
    return send_file(buffer, mimetype='image/svg+xml')

@app.route('/histogram_width.svg')
def histogram_width():
    plt.figure(figsize=(10, 6))
    plt.hist(df['width'].dropna(), bins=25, color='lightblue', alpha=0.7, edgecolor='black')
    plt.title('Distribution of Screen Width (pixels)', fontsize=16)
    plt.xlabel('Width (pixels)', fontsize=12)
    plt.ylabel('Frequency', fontsize=12)
    plt.grid(True, alpha=0.3)
    
    # Save plot to bytes buffer
    buffer = io.BytesIO()
    plt.savefig(buffer, format='svg', bbox_inches='tight')
    buffer.seek(0)
    plt.close()
    
    return send_file(buffer, mimetype='image/svg+xml')

@app.route('/histogram_height.svg')
def histogram_height():
    plt.figure(figsize=(10, 6))
    plt.hist(df['height'].dropna(), bins=25, color='lightpink', alpha=0.7, edgecolor='black')
    plt.title('Distribution of Screen Height (pixels)', fontsize=16)
    plt.xlabel('Height (pixels)', fontsize=12)
    plt.ylabel('Frequency', fontsize=12)
    plt.grid(True, alpha=0.3)
    
    # Save plot to bytes buffer
    buffer = io.BytesIO()
    plt.savefig(buffer, format='svg', bbox_inches='tight')
    buffer.seek(0)
    plt.close()
    
    return send_file(buffer, mimetype='image/svg+xml')

@app.route('/histogram_announcement_year.svg')
def histogram_announcement_year():
    plt.figure(figsize=(10, 6))
    plt.hist(df['announcement_year'].dropna(), bins=20, color='lightseagreen', alpha=0.7, edgecolor='black')
    plt.title('Distribution of Announcement Year', fontsize=16)
    plt.xlabel('Announcement Year', fontsize=12)
    plt.ylabel('Frequency', fontsize=12)
    plt.grid(True, alpha=0.3)
    
    # Save plot to bytes buffer
    buffer = io.BytesIO()
    plt.savefig(buffer, format='svg', bbox_inches='tight')
    buffer.seek(0)
    plt.close()
    
    return send_file(buffer, mimetype='image/svg+xml')

# Combined histograms route
@app.route('/histograms.svg')
def all_histograms():
    # Create a 3x3 subplot grid
    fig, axes = plt.subplots(3, 3, figsize=(18, 15))
    fig.suptitle('Smartphone Data Distribution Analysis', fontsize=20, y=0.95)
    
    # Define the columns and their corresponding colors
    columns = ['inches', 'battery', 'ram(GB)', 'weight(g)', 'storage(GB)', 
               'price(USD)', 'width', 'height', 'announcement_year']
    colors = ['skyblue', 'lightgreen', 'lightcoral', 'gold', 'mediumpurple', 
              'orange', 'lightblue', 'lightpink', 'lightseagreen']
    titles = ['Screen Size (inches)', 'Battery Capacity (mAh)', 'RAM (GB)', 
              'Weight (g)', 'Storage (GB)', 'Price (USD)', 
              'Width (pixels)', 'Height (pixels)', 'Announcement Year']
    
    # Create histograms
    for i, (col, color, title) in enumerate(zip(columns, colors, titles)):
        row = i // 3
        col_idx = i % 3
        ax = axes[row, col_idx]
        
        # Handle different bin counts for different data types
        if col == 'ram(GB)' or col == 'announcement_year':
            bins = 20
        elif col in ['width', 'height', 'weight(g)', 'storage(GB)']:
            bins = 25
        else:
            bins = 30
            
        ax.hist(df[col].dropna(), bins=bins, color=color, alpha=0.7, edgecolor='black')
        ax.set_title(title, fontsize=12)
        ax.set_xlabel(title, fontsize=10)
        ax.set_ylabel('Frequency', fontsize=10)
        ax.grid(True, alpha=0.3)
    
    # Adjust layout to prevent overlap
    plt.tight_layout()
    plt.subplots_adjust(top=0.92)
    
    # Save plot to bytes buffer
    buffer = io.BytesIO()
    plt.savefig(buffer, format='svg', bbox_inches='tight')
    buffer.seek(0)
    plt.close()
    
    return send_file(buffer, mimetype='image/svg+xml')

# Update the __main__ section to generate histogram SVGs
if __name__ == '__main__':
    with app.app_context():
        # Generate and save brand_pie.svg
        response = app.test_client().get('/brand_pie.svg')
        with open('static/images/brand_pie.svg', 'wb') as f:
            f.write(response.data)

        # Generate and save os_pie.svg
        response = app.test_client().get('/os_pie.svg')
        with open('static/images/os_pie.svg', 'wb') as f:
            f.write(response.data)
            
        # Generate and save all histogram SVGs
        histogram_routes = [
            'histogram_inches', 'histogram_battery', 'histogram_ram',
            'histogram_weight', 'histogram_storage', 'histogram_price',
            'histogram_width', 'histogram_height', 'histogram_announcement_year',
            'histograms'
        ]
        
        for route in histogram_routes:
            response = app.test_client().get(f'/{route}.svg')
            with open(f'static/images/{route}.svg', 'wb') as f:
                f.write(response.data)

    app.run()