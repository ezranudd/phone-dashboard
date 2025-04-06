import pandas as pd
from flask import Flask, request, send_file
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
    return html

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
    {table_html}
    </html>
    """
    
    # Return result
    return browse_html

if __name__ == '__main__':
    app.run()