import pandas as pd
import numpy as np
from flask import Flask, request, jsonify, send_file
import matplotlib
matplotlib.use('Agg') # Non-gui for use with flask
import matplotlib.pyplot as plt
import io

app = Flask(__name__)
df = pd.read_csv("main.csv")

# Home Page (index.html)
@app.route("/")
def home():
    with open("index.html") as f:
        html = f.read()

    # Capture df.info() output
    buffer = io.StringIO()
    df.info(buf=buffer)
    info_output = buffer.getvalue()
    buffer.close()

    # df.describe() output to html
    descr_output = df.describe().to_html()

    return html.format(dataframe_info=info_output, dataframe_describe=descr_output)

# Browse CSV as an html table
@app.route('/browse.html')
def browse():
    # Pandas Display Options
    pd.set_option('display.float_format', '{}'.format)
    
    # Convert csv to html
    table_html = df.to_html(classes='data', header="true", index=False)
    
    # Format page with header
    browse_html = f"""
    <html>
    <h1>Browse</h1>
    <a href="https://www.kaggle.com/datasets/amansingh0000000/smartphones/data">Source (kaggle.com)</a>
    {table_html}
    </html>
    """
    
    # Return result
    return browse_html

@app.route('/browse.json')
def browse_json():
    
    # Convert DataFrame to list of dictionaries
    data = df.to_dict(orient='records')
    
    # JSONify
    return jsonify(data)

@app.route('/dashboard1.svg')
def dashboard1():
    plt.figure(figsize=(12, 8))
    
    # Scatter Plot: Price vs Rating (colored by Brand)
    brands = df['Brand'].unique()
    colors = plt.cm.tab10(np.linspace(0, 1, len(brands)))
    
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
    
    # Configue Plot
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

# Run App
if __name__ == '__main__':
    with app.app_context():
        response = app.test_client().get('/dashboard1.svg')
        with open('dashboard1.svg', 'wb') as f:
            f.write(response.data)
    app.run()