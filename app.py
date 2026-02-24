from flask import Flask, render_template
import ee
import os

app = Flask(__name__)
project_id = 'xward-481405'

# INITIALIZE EARTH ENGINE
try:
    # Professional Method: Inherit permissions from Cloud Run Service Account
    creds = ee.ComputeEngineCredentials()
    ee.Initialize(creds, project=project_id)
except:
    # Local fallback
    ee.Initialize(project=project_id)

@app.route('/')
def index():
    # This is where you would calculate your MCA or SAR flood map
    # For now, it just loads the main dashboard page
    return render_template('index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)