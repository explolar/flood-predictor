from flask import Flask, render_template, jsonify
import ee
import os

app = Flask(__name__)
project_id = 'xward-481405'

# Initialize Earth Engine using Cloud Run Identity
try:
    creds = ee.ComputeEngineCredentials()
    ee.Initialize(creds, project=project_id)
except:
    ee.Initialize(project=project_id)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze_flood')
def analyze_flood():
    # 1. Define Area of Interest (Danapur/Patna example)
    aoi = ee.Geometry.BBox(84.90, 25.50, 85.30, 25.80)
    
    # 2. Terrain Guard: Mask steep slopes to prevent Radar Shadows
    # This is critical for the integrity of your MTP results
    dem = ee.Image('USGS/SRTMGL1_003').clip(aoi)
    slope = ee.Terrain.slope(dem)
    slope_mask = slope.lt(8) 
    
    # 3. Sentinel-1 SAR Processing
    s1 = ee.ImageCollection('COPERNICUS/S1_GRD').filterBounds(aoi).filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH'))
    
    pre_img = s1.filterDate('2024-05-01', '2024-05-30').median().clip(aoi)
    post_img = s1.filterDate('2024-08-01', '2024-08-30').median().clip(aoi)
    
    # Difference Analysis
    diff = pre_img.subtract(post_img)
    flooded = diff.gt(1.25).updateMask(slope_mask)
    
    # 4. Calculate Area (The data for your thesis)
    stats = flooded.multiply(ee.Image.pixelArea()).reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=aoi,
        scale=30,
        maxPixels=1e9
    )
    
    area_ha = round(stats.get('VH').getInfo() / 10000, 2) if stats.get('VH').getInfo() else 0
    
    return jsonify({
        "status": "Success",
        "location": "Danapur/Patna",
        "flooded_area_ha": area_ha,
        "methodology": "SAR Backscatter Change Detection"
    })