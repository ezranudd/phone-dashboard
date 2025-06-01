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

# Run App
if __name__ == '__main__':
    app.run()