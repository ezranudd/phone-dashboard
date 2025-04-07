import pandas as pd
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

# Run App
if __name__ == '__main__':
    app.run()