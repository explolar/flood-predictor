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
