def get_mca_legend(map_name):
    return f'''
    <script>
    (function() {{
        var legend = L.control({{position: 'bottomleft'}});
        legend.onAdd = function() {{
            var div = document.createElement('div');
            div.style.cssText = 'background:rgba(13,27,42,0.93);border:1.5px solid #00FFFF;color:#e0e1dd;font-size:11.5px;padding:12px 15px;border-radius:10px;backdrop-filter:blur(8px);box-shadow:0 0 20px rgba(0,255,255,0.2);line-height:1.95;min-width:155px;pointer-events:none;';
            div.innerHTML =
                '<div style="color:#00FFFF;font-weight:bold;font-size:12.5px;letter-spacing:1px;border-bottom:1px solid rgba(0,255,255,0.3);padding-bottom:6px;margin-bottom:8px;">&#9672; RISK INDEX</div>' +
                '<span style="display:inline-block;width:12px;height:12px;background:#d73027;border-radius:2px;margin-right:7px;vertical-align:middle;"></span>Very High (5)<br>' +
                '<span style="display:inline-block;width:12px;height:12px;background:#fc8d59;border-radius:2px;margin-right:7px;vertical-align:middle;"></span>High (4)<br>' +
                '<span style="display:inline-block;width:12px;height:12px;background:#ffffbf;border-radius:2px;margin-right:7px;vertical-align:middle;"></span>Moderate (3)<br>' +
                '<span style="display:inline-block;width:12px;height:12px;background:#91cf60;border-radius:2px;margin-right:7px;vertical-align:middle;"></span>Low (2)<br>' +
                '<span style="display:inline-block;width:12px;height:12px;background:#1a9850;border-radius:2px;margin-right:7px;vertical-align:middle;"></span>Very Low (1)';
            return div;
        }};
        legend.addTo({map_name});
    }})();
    </script>
    '''

def get_sar_legend(map_name):
    return f'''
    <script>
    (function() {{
        var legend = L.control({{position: 'bottomleft'}});
        legend.onAdd = function() {{
            var div = document.createElement('div');
            div.style.cssText = 'background:rgba(13,27,42,0.93);border:1.5px solid #00FFFF;color:#e0e1dd;font-size:11.5px;padding:12px 15px;border-radius:10px;backdrop-filter:blur(8px);box-shadow:0 0 20px rgba(0,255,255,0.2);line-height:1.95;min-width:185px;pointer-events:none;';
            div.innerHTML =
                '<div style="color:#00FFFF;font-weight:bold;font-size:12.5px;letter-spacing:1px;border-bottom:1px solid rgba(0,255,255,0.3);padding-bottom:6px;margin-bottom:8px;">&#9672; SAR INDICATORS</div>' +
                '<span style="display:inline-block;width:12px;height:12px;background:#00FFFF;border-radius:2px;margin-right:7px;vertical-align:middle;"></span>Active Flood Mask<br>' +
                '<span style="display:inline-block;width:12px;height:12px;background:#00008B;border-radius:2px;margin-right:7px;vertical-align:middle;"></span>Permanent Water<br>' +
                '<hr style="margin:8px 0;border:0;border-top:1px solid rgba(0,255,255,0.2);">' +
                '<div style="color:rgba(0,255,255,0.6);font-size:10.5px;margin-bottom:5px;letter-spacing:1px;">BACKSCATTER SCALE</div>' +
                '<span style="display:inline-block;width:12px;height:12px;background:#000005;border-radius:2px;margin-right:7px;vertical-align:middle;"></span>Low &minus;25 dB<br>' +
                '<span style="display:inline-block;width:12px;height:12px;background:#2e86c1;border-radius:2px;margin-right:7px;vertical-align:middle;"></span>Medium<br>' +
                '<span style="display:inline-block;width:12px;height:12px;background:#ffffff;border-radius:2px;margin-right:7px;vertical-align:middle;"></span>High 0 dB<br>' +
                '<hr style="margin:8px 0;border:0;border-top:1px solid rgba(0,255,255,0.2);">' +
                '<span style="color:#888;font-style:italic;font-size:10px;">&#9889; Terrain Guard: slope &lt; 8&#176;</span>';
            return div;
        }};
        legend.addTo({map_name});
    }})();
    </script>
    '''


def get_stream_order_legend(map_name):
    return f'''
    <script>
    (function() {{
        var legend = L.control({{position: 'bottomleft'}});
        legend.onAdd = function() {{
            var div = document.createElement('div');
            div.style.cssText = 'background:rgba(13,27,42,0.93);border:1.5px solid #64B5F6;color:#e0e1dd;font-size:11px;padding:12px 15px;border-radius:10px;backdrop-filter:blur(8px);box-shadow:0 0 20px rgba(100,181,246,0.2);line-height:2.0;min-width:170px;pointer-events:none;';
            div.innerHTML =
                '<div style="color:#64B5F6;font-weight:bold;font-size:12px;letter-spacing:1px;border-bottom:1px solid rgba(100,181,246,0.3);padding-bottom:6px;margin-bottom:8px;">&#9672; STREAM ORDER</div>' +
                '<span style="display:inline-block;width:12px;height:12px;background:#b3d9ff;border-radius:2px;margin-right:7px;vertical-align:middle;"></span>Order 1 (Headwater)<br>' +
                '<span style="display:inline-block;width:12px;height:12px;background:#66b3ff;border-radius:2px;margin-right:7px;vertical-align:middle;"></span>Order 2<br>' +
                '<span style="display:inline-block;width:12px;height:12px;background:#3399ff;border-radius:2px;margin-right:7px;vertical-align:middle;"></span>Order 3<br>' +
                '<span style="display:inline-block;width:12px;height:12px;background:#0066cc;border-radius:2px;margin-right:7px;vertical-align:middle;"></span>Order 4<br>' +
                '<span style="display:inline-block;width:12px;height:12px;background:#003366;border-radius:2px;margin-right:7px;vertical-align:middle;"></span>Order 5+ (Major)<br>' +
                '<hr style="margin:6px 0;border:0;border-top:1px solid rgba(100,181,246,0.2);">' +
                '<span style="color:#888;font-style:italic;font-size:9.5px;">Proxy: log10(flow accumulation)</span>';
            return div;
        }};
        legend.addTo({map_name});
    }})();
    </script>
    '''


def get_flow_acc_legend(map_name):
    return f'''
    <script>
    (function() {{
        var legend = L.control({{position: 'bottomleft'}});
        legend.onAdd = function() {{
            var div = document.createElement('div');
            div.style.cssText = 'background:rgba(13,27,42,0.93);border:1.5px solid #64B5F6;color:#e0e1dd;font-size:11px;padding:12px 15px;border-radius:10px;backdrop-filter:blur(8px);box-shadow:0 0 20px rgba(100,181,246,0.2);line-height:2.0;min-width:180px;pointer-events:none;';
            div.innerHTML =
                '<div style="color:#64B5F6;font-weight:bold;font-size:12px;letter-spacing:1px;border-bottom:1px solid rgba(100,181,246,0.3);padding-bottom:6px;margin-bottom:8px;">&#9672; FLOW ACCUMULATION</div>' +
                '<span style="display:inline-block;width:12px;height:12px;background:#f7fbff;border-radius:2px;margin-right:7px;vertical-align:middle;"></span>Very Low (&lt;100)<br>' +
                '<span style="display:inline-block;width:12px;height:12px;background:#c6dbef;border-radius:2px;margin-right:7px;vertical-align:middle;"></span>Low (100-1k)<br>' +
                '<span style="display:inline-block;width:12px;height:12px;background:#6baed6;border-radius:2px;margin-right:7px;vertical-align:middle;"></span>Moderate (1k-10k)<br>' +
                '<span style="display:inline-block;width:12px;height:12px;background:#2171b5;border-radius:2px;margin-right:7px;vertical-align:middle;"></span>High (10k-100k)<br>' +
                '<span style="display:inline-block;width:12px;height:12px;background:#08306b;border-radius:2px;margin-right:7px;vertical-align:middle;"></span>Very High (&gt;100k)<br>' +
                '<hr style="margin:6px 0;border:0;border-top:1px solid rgba(100,181,246,0.2);">' +
                '<span style="color:#888;font-style:italic;font-size:9.5px;">HydroSHEDS 3 arc-sec &middot; log scale</span>';
            return div;
        }};
        legend.addTo({map_name});
    }})();
    </script>
    '''


def get_index_legend(map_name, index_key):
    """Generate a Leaflet JS legend for a spectral index from INDEX_REGISTRY."""
    from gee_functions.indices import INDEX_REGISTRY
    meta = INDEX_REGISTRY[index_key]

    rows = ''
    for (lo, hi, color, label) in meta['classes']:
        rows += (
            f"'<span style=\"display:inline-block;width:12px;height:12px;"
            f"background:{color};border-radius:2px;margin-right:7px;"
            f"vertical-align:middle;\"></span>{label}<br>' + "
        )
    rows = rows.rstrip(' + ')

    return f'''
    <script>
    (function() {{
        var legend = L.control({{position: 'bottomleft'}});
        legend.onAdd = function() {{
            var div = document.createElement('div');
            div.style.cssText = 'background:rgba(13,27,42,0.93);border:1.5px solid #00FFFF;color:#e0e1dd;font-size:11px;padding:12px 15px;border-radius:10px;backdrop-filter:blur(8px);box-shadow:0 0 20px rgba(0,255,255,0.2);line-height:2.0;min-width:220px;pointer-events:none;';
            div.innerHTML =
                '<div style="color:#00FFFF;font-weight:bold;font-size:12px;letter-spacing:1px;border-bottom:1px solid rgba(0,255,255,0.3);padding-bottom:6px;margin-bottom:8px;">&#9672; {index_key}</div>' +
                {rows};
            return div;
        }};
        legend.addTo({map_name});
    }})();
    </script>
    '''
