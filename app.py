from flask import Flask, jsonify
import ee
import os

app = Flask(__name__)
project_id = 'xward-481405'

def init_ee():
    try:
        # Check if already initialized by trying to get a dummy info object
        ee.data.getAssetInfo('projects/earthengine-public/assets/COPERNICUS/S1_GRD')
    except Exception:
        # If not initialized, perform the Cloud Run Identity auth
        try:
            creds = ee.ComputeEngineCredentials()
            ee.Initialize(creds, project=project_id)
        except Exception:
            # Fallback for local testing
            ee.Initialize(project=project_id)
@app.route('/')
def index():
    return "Bihar Hydro-Climatic Risk Atlas: Flask Backend Active. Access /analyze for SAR results."

@app.route('/analyze')
def analyze():
    init_ee()
    aoi = ee.Geometry.BBox(84.90, 25.50, 85.30, 25.80)
    # Terrain Guard: Mask steep slopes for your MTP accuracy
    dem = ee.Image('USGS/SRTMGL1_003').clip(aoi)
    slope = ee.Terrain.slope(dem)
    slope_mask = slope.lt(8) 
    
    s1 = ee.ImageCollection('COPERNICUS/S1_GRD').filterBounds(aoi).filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH'))
    pre_img = s1.filterDate('2024-05-01', '2024-05-30').median().clip(aoi)
    post_img = s1.filterDate('2024-08-01', '2024-08-30').median().clip(aoi)
    
    diff = pre_img.subtract(post_img)
    flooded = diff.gt(1.25).updateMask(slope_mask)
    
    stats = flooded.multiply(ee.Image.pixelArea()).reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=aoi,
        scale=30,
        maxPixels=1e9
    )
    area_ha = round(stats.get('VH').getInfo() / 10000, 2) if stats.get('VH').getInfo() else 0
    
    return jsonify({"location": "Danapur", "flooded_area_ha": area_ha})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)