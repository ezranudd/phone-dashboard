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

@app.route('/brand_chart.svg')
def brand_pie_chart():
    brand_counts = df['brand'].value_counts()
    
    fig, ax = plt.subplots(figsize=(10, 8))
    
    wedges, texts, autotexts = ax.pie(brand_counts.values, 
        labels=brand_counts.index,
        autopct='%1.1f%%',
        startangle=90)
    
    ax.set_title('Phone Distribution by Brand', fontsize=16, fontweight='bold', pad=20)
    
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')
        autotext.set_fontsize(10)
    
    for text in texts:
        text.set_fontsize(12)

    ax.axis('equal')
    
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='svg', bbox_inches='tight')
    img_buffer.seek(0)
    plt.close(fig)
    
    return send_file(img_buffer, mimetype='image/svg+xml')

# Run App
if __name__ == '__main__':
    with app.app_context():

        # Generate and save price_rating.svg
        response = app.test_client().get('/brand_chart.svg')
        with open('static/images/brand_chart.svg', 'wb') as f:
            f.write(response.data)

    app.run()