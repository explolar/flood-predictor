import ee
import json
import math
import pandas as pd
import streamlit as st


@st.cache_data(show_spinner=False, ttl=3600)
def get_chirps_series(aoi_json, start_str, end_str):
    aoi_geom = ee.Geometry(json.loads(aoi_json))
    chirps = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY").filterDate(start_str, end_str).filterBounds(aoi_geom)
    def extract(img):
        mean = img.reduceRegion(reducer=ee.Reducer.mean(), geometry=aoi_geom, scale=5000, maxPixels=1e8)
        return ee.Feature(None, {'date': img.date().format('YYYY-MM-dd'), 'rain': mean.get('precipitation')})
    fc = chirps.map(extract).getInfo()
    if not fc or not fc.get('features'):
        return None
    records = [{'date': f['properties']['date'], 'rainfall_mm': float(f['properties']['rain'])}
               for f in fc['features'] if f['properties'].get('rain') is not None]
    if not records:
        return None
    df = pd.DataFrame(records)
    df['date'] = pd.to_datetime(df['date'])
    return df.sort_values('date').set_index('date')


@st.cache_data(show_spinner=False, ttl=7200)
def get_return_period(aoi_json):
    try:
        aoi_geom = ee.Geometry(json.loads(aoi_json))
        years_ee = ee.List.sequence(2000, 2023)
        def annual_monsoon(yr):
            yr = ee.Number(yr).int()
            start = ee.Date.fromYMD(yr, 6, 1)
            end   = ee.Date.fromYMD(yr, 11, 1)
            total = (ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY")
                     .filterDate(start, end).filterBounds(aoi_geom).sum()
                     .reduceRegion(reducer=ee.Reducer.mean(), geometry=aoi_geom, scale=10000, maxPixels=1e9))
            return ee.Feature(None, {'year': yr, 'rain': total.get('precipitation')})
        data = ee.FeatureCollection(years_ee.map(annual_monsoon)).getInfo()
        rains = [float(f['properties']['rain']) for f in data['features']
                 if f['properties'].get('rain') is not None]
        if len(rains) < 10:
            return None
        n  = len(rains)
        mu = sum(rains) / n
        std = (sum((x - mu)**2 for x in rains) / n) ** 0.5
        beta = std * (6 ** 0.5) / math.pi
        u    = mu - 0.5772 * beta
        rp   = {}
        max_val = max(rains)
        for T in [2, 5, 10, 25, 50, 100]:
            rp[T] = round(u - beta * math.log(-math.log(1 - 1/T)), 0)
        return {'mean': round(mu, 0), 'std': round(std, 0),
                'return_periods': rp, 'n_years': n,
                'max_obs': round(max_val, 0), 'rains': sorted(rains)}
    except Exception:
        return None


@st.cache_data(show_spinner=False, ttl=7200)
def get_progression_stats(aoi_json, year):
    try:
        aoi_geom = ee.Geometry(json.loads(aoi_json))
        months_ee = ee.List([6, 7, 8, 9, 10])
        def monthly_rain(m):
            m = ee.Number(m).int()
            start = ee.Date.fromYMD(ee.Number(year), m, 1)
            end   = start.advance(1, 'month')
            total = (ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY")
                     .filterDate(start, end).filterBounds(aoi_geom).sum()
                     .reduceRegion(reducer=ee.Reducer.mean(), geometry=aoi_geom, scale=5000))
            return ee.Feature(None, {'month': m, 'rain': total.get('precipitation')})
        data = ee.FeatureCollection(months_ee.map(monthly_rain)).getInfo()
        names = {6:'Jun',7:'Jul',8:'Aug',9:'Sep',10:'Oct'}
        records = [{'Month': names[int(f['properties']['month'])],
                    'month_num': int(f['properties']['month']),
                    'Rain (mm)': round(float(f['properties'].get('rain') or 0), 1)}
                   for f in data['features']]
        records.sort(key=lambda x: x['month_num'])
        return pd.DataFrame(records)
    except Exception:
        return None
