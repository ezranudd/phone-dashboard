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

# Run App
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

    app.run()