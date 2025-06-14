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

# Battery Type Pie Chart
@app.route('/battery_type_pie.svg')
def battery_type_pie():
    # Count phones by battery type
    battery_counts = df['battery_type'].value_counts()
    
    # Create figure and axis
    plt.figure(figsize=(8, 8))
    
    # Create pie chart
    wedges, texts, autotexts = plt.pie(
        battery_counts, 
        labels=battery_counts.index,
        autopct='%1.1f%%',  # Show percentages
        startangle=90,      # Start angle
        shadow=False,       # No shadow
        explode=[0.05] * len(battery_counts),  # Slightly explode all slices
        textprops={'fontsize': 12},  # Font size for labels
        colors=['lightblue', 'lightcoral']  # Custom colors
    )
    
    # Set percentage text color to white
    for autotext in autotexts:
        autotext.set_color('white')
    
    # Equal aspect ratio ensures the pie chart is circular
    plt.axis('equal')
    
    # Add title
    plt.title('Battery Type Distribution', fontsize=16)
    
    # Add legend with counts
    legend_labels = [f"{btype} ({count})" for btype, count in zip(battery_counts.index, battery_counts)]
    plt.legend(legend_labels, loc='center right', bbox_to_anchor=(1.3, 0.5), fontsize=12)
    
    # Save plot to bytes buffer
    buffer = io.BytesIO()
    plt.savefig(buffer, format='svg', bbox_inches='tight')
    buffer.seek(0)
    plt.close()
    
    return send_file(buffer, mimetype='image/svg+xml')

# Video Format Count Plots
@app.route('/video_formats.svg')
def video_formats():
    # Video format columns
    video_cols = ['video_720p', 'video_1080p', 'video_4K', 'video_8K', 
                  'video_30fps', 'video_60fps', 'video_120fps', 'video_240fps', 
                  'video_480fps', 'video_960fps']
    
    # Create a 2x5 subplot grid
    fig, axes = plt.subplots(2, 5, figsize=(20, 8))
    fig.suptitle('Video Format Support Distribution', fontsize=20, y=0.98)
    
    # Flatten axes for easier iteration
    axes = axes.flatten()
    
    colors = ['lightgreen', 'lightcoral']
    
    for i, col in enumerate(video_cols):
        # Count True/False values
        counts = df[col].value_counts()
        
        # Create bar plot
        bars = axes[i].bar(counts.index.astype(str), counts.values, color=colors)
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            axes[i].text(bar.get_x() + bar.get_width()/2., height + 5,
                        f'{int(height)}', ha='center', va='bottom', fontsize=10)
        
        # Customize subplot
        axes[i].set_title(col.replace('_', ' ').title(), fontsize=12)
        axes[i].set_ylabel('Count', fontsize=10)
        axes[i].set_ylim(0, max(counts.values) * 1.1)
        axes[i].grid(True, alpha=0.3)
    
    # Adjust layout
    plt.tight_layout()
    plt.subplots_adjust(top=0.92)
    
    # Save plot to bytes buffer
    buffer = io.BytesIO()
    plt.savefig(buffer, format='svg', bbox_inches='tight')
    buffer.seek(0)
    plt.close()
    
    return send_file(buffer, mimetype='image/svg+xml')

# Average Price by Brand
@app.route('/avg_price_by_brand.svg')
def avg_price_by_brand():
    # Calculate average price by brand
    avg_price = df.groupby('brand')['price(USD)'].mean().sort_values(ascending=False)
    
    # Create figure
    plt.figure(figsize=(14, 8))
    
    # Create bar plot
    bars = plt.bar(range(len(avg_price)), avg_price.values, 
                   color=plt.cm.viridis(np.linspace(0, 1, len(avg_price))))
    
    # Customize the plot
    plt.title('Average Price by Brand', fontsize=16)
    plt.xlabel('Brand', fontsize=12)
    plt.ylabel('Average Price (USD)', fontsize=12)
    plt.xticks(range(len(avg_price)), avg_price.index, rotation=45, ha='right')
    plt.grid(True, alpha=0.3, axis='y')
    
    # Add value labels on bars
    for i, bar in enumerate(bars):
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 5,
                f'${height:.0f}', ha='center', va='bottom', fontsize=9)
    
    # Adjust layout
    plt.tight_layout()
    
    # Save plot to bytes buffer
    buffer = io.BytesIO()
    plt.savefig(buffer, format='svg', bbox_inches='tight')
    buffer.seek(0)
    plt.close()
    
    return send_file(buffer, mimetype='image/svg+xml')

# Battery Efficiency by Brand (Battery capacity per dollar)
@app.route('/battery_efficiency_by_brand.svg')
def battery_efficiency_by_brand():
    # Calculate battery efficiency (mAh per dollar)
    df['battery_efficiency'] = df['battery'] / df['price(USD)']
    avg_efficiency = df.groupby('brand')['battery_efficiency'].mean().sort_values(ascending=False)
    
    # Create figure
    plt.figure(figsize=(14, 8))
    
    # Create bar plot
    bars = plt.bar(range(len(avg_efficiency)), avg_efficiency.values,
                   color=plt.cm.plasma(np.linspace(0, 1, len(avg_efficiency))))
    
    # Customize the plot
    plt.title('Battery Efficiency by Brand (mAh per USD)', fontsize=16)
    plt.xlabel('Brand', fontsize=12)
    plt.ylabel('Battery Efficiency (mAh/USD)', fontsize=12)
    plt.xticks(range(len(avg_efficiency)), avg_efficiency.index, rotation=45, ha='right')
    plt.grid(True, alpha=0.3, axis='y')
    
    # Add value labels on bars
    for i, bar in enumerate(bars):
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                f'{height:.1f}', ha='center', va='bottom', fontsize=9)
    
    # Adjust layout
    plt.tight_layout()
    
    # Save plot to bytes buffer
    buffer = io.BytesIO()
    plt.savefig(buffer, format='svg', bbox_inches='tight')
    buffer.seek(0)
    plt.close()
    
    return send_file(buffer, mimetype='image/svg+xml')

# Specifications by Brand (Height, RAM, Storage, Weight)
@app.route('/specs_by_brand.svg')
def specs_by_brand():
    # Specifications to analyze
    specs = ['height', 'ram(GB)', 'storage(GB)', 'weight(g)']
    spec_titles = ['Height (pixels)', 'RAM (GB)', 'Storage (GB)', 'Weight (g)']
    
    # Create a 2x2 subplot grid
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Average Specifications by Brand', fontsize=18, y=0.95)
    
    # Flatten axes for easier iteration
    axes = axes.flatten()
    
    colors = ['lightblue', 'lightgreen', 'lightcoral', 'gold']
    
    for i, (spec, title, color) in enumerate(zip(specs, spec_titles, colors)):
        # Calculate average by brand
        avg_spec = df.groupby('brand')[spec].mean().sort_values(ascending=False)
        
        # Create bar plot
        bars = axes[i].bar(range(len(avg_spec)), avg_spec.values, color=color, alpha=0.7)
        
        # Customize subplot
        axes[i].set_title(f'Average {title}', fontsize=14)
        axes[i].set_xlabel('Brand', fontsize=10)
        axes[i].set_ylabel(f'Average {title}', fontsize=10)
        axes[i].set_xticks(range(len(avg_spec)))
        axes[i].set_xticklabels(avg_spec.index, rotation=45, ha='right', fontsize=8)
        axes[i].grid(True, alpha=0.3, axis='y')
        
        # Add value labels on bars (only for top 5 to avoid clutter)
        for j, bar in enumerate(bars[:5]):
            height = bar.get_height()
            axes[i].text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                        f'{height:.0f}', ha='center', va='bottom', fontsize=8)
    
    # Adjust layout
    plt.tight_layout()
    plt.subplots_adjust(top=0.92)
    
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

if __name__ == '__main__':
    with app.app_context():
        response = app.test_client().get('/brand_pie.svg')
        with open('static/images/brand_pie.svg', 'wb') as f:
            f.write(response.data)

        response = app.test_client().get('/os_pie.svg')
        with open('static/images/os_pie.svg', 'wb') as f:
            f.write(response.data)

        response = app.test_client().get('/histograms.svg')
        with open('static/images/histograms.svg', 'wb') as f:
            f.write(response.data)
            
        response = app.test_client().get('/battery_type_pie.svg')
        with open('static/images/battery_type_pie.svg', 'wb') as f:
            f.write(response.data)
            
        response = app.test_client().get('/video_formats.svg')
        with open('static/images/video_formats.svg', 'wb') as f:
            f.write(response.data)
            
        response = app.test_client().get('/avg_price_by_brand.svg')
        with open('static/images/avg_price_by_brand.svg', 'wb') as f:
            f.write(response.data)
            
        response = app.test_client().get('/battery_efficiency_by_brand.svg')
        with open('static/images/battery_efficiency_by_brand.svg', 'wb') as f:
            f.write(response.data)
            
        response = app.test_client().get('/specs_by_brand.svg')
        with open('static/images/specs_by_brand.svg', 'wb') as f:
            f.write(response.data)

    app.run()