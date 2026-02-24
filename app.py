from flask import Flask, render_template, request, jsonify
import ee
import os

app = Flask(__name__)
project_id = 'xward-481405'

def init_ee():
    try:
        ee.data.getSTAC()
    except Exception:
        try:
            creds = ee.ComputeEngineCredentials()
            ee.Initialize(creds, project=project_id)
        except Exception:
            ee.Initialize(project=project_id)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    init_ee()
    data = request.json
    # Defaulting to Danapur/Patna coordinates
    aoi = ee.Geometry.BBox(84.90, 25.50, 85.30, 25.80)
    
    # --- PHASE 1: MCA RISK MODELING ---
    dem = ee.Image('USGS/SRTMGL1_003').select('elevation').clip(aoi)
    slope = ee.Terrain.slope(dem).clip(aoi).clamp(0, 40)
    slope_r = slope.where(slope.lte(2), 5).where(slope.gt(2).And(slope.lte(5)), 4).where(slope.gt(5).And(slope.lte(10)), 3).where(slope.gt(10).And(slope.lte(20)), 2).where(slope.gt(20), 1)
    
    lulc = ee.ImageCollection("ESA/WorldCover/v200").mosaic().select('Map').clip(aoi)
    lulc_r = lulc.remap([10,20,30,40,50,60,80,90], [1,2,2,3,5,4,5,5])
    
    risk_map = lulc_r.multiply(0.40).add(slope_r.multiply(0.60)).clip(aoi).round()
    risk_map_id = risk_map.getMapId({'min':1,'max':5,'palette':['#1a9850','#91cf60','#ffffbf','#fc8d59','#d73027']})['tile_fetcher'].url_format

    # --- PHASE 2: SAR FLOOD DETECTION ---
    # Terrain Guard: Vital for removing Radar Shadows in Manali/Naggar
    slope_mask = slope.lt(8)
    s1 = ee.ImageCollection('COPERNICUS/S1_GRD').filterBounds(aoi).filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH'))
    
    pre_img = s1.filterDate('2024-05-01', '2024-05-30').median().clip(aoi)
    post_img = s1.filterDate('2024-08-01', '2024-08-30').median().clip(aoi)
    
    diff = pre_img.subtract(post_img)
    flooded = diff.gt(1.25).updateMask(slope_mask)
    
    stats = flooded.multiply(ee.Image.pixelArea()).reduceRegion(reducer=ee.Reducer.sum(), geometry=aoi, scale=30, maxPixels=1e9)
    area_ha = round(stats.get('VH').getInfo() / 10000, 2) if stats.get('VH').getInfo() else 0

    return jsonify({
        "risk_tiles": risk_map_id,
        "flooded_area": area_ha,
        "status": "Success"
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)