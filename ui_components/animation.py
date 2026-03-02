"""
Feature 14: Time-Lapse Animation.
Generates JavaScript-based Leaflet animation cycling through monthly SAR tile URLs.
"""


def generate_timelapse_html(tile_urls, map_center, labels, zoom=11):
    """
    Generate an HTML/JS animation that cycles through tile layer URLs.

    Args:
        tile_urls: List of tile URL strings (one per frame).
        map_center: [lat, lon] for map center.
        labels: List of label strings for each frame (e.g., "Jun 2024").
        zoom: Map zoom level.

    Returns:
        HTML string for embedding via st.components.html().
    """
    # Build JS array of tile URLs
    urls_js = ', '.join(f'"{u}"' for u in tile_urls)
    labels_js = ', '.join(f'"{l}"' for l in labels)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <style>
            body {{ margin:0; padding:0; background:#0a0f1a; }}
            #map {{ width:100%; height:100vh; }}
            .controls {{
                position:absolute; bottom:20px; left:50%; transform:translateX(-50%);
                z-index:1000; display:flex; gap:10px; align-items:center;
                background:rgba(10,15,26,0.9); padding:8px 16px; border-radius:8px;
                border:1px solid rgba(0,255,255,0.2); font-family:monospace;
            }}
            .controls button {{
                background:rgba(0,255,255,0.1); border:1px solid rgba(0,255,255,0.3);
                color:#00FFFF; padding:6px 14px; border-radius:4px; cursor:pointer;
                font-family:monospace; font-size:12px;
            }}
            .controls button:hover {{ background:rgba(0,255,255,0.2); }}
            .controls .label {{
                color:#00FFFF; font-size:13px; letter-spacing:2px; min-width:100px;
                text-align:center;
            }}
            .controls .frame-counter {{
                color:rgba(0,255,255,0.5); font-size:11px;
            }}
        </style>
    </head>
    <body>
        <div id="map"></div>
        <div class="controls">
            <button id="prevBtn" onclick="prevFrame()">&#9664;</button>
            <button id="playBtn" onclick="togglePlay()">&#9654; PLAY</button>
            <button id="nextBtn" onclick="nextFrame()">&#9654;</button>
            <div class="label" id="frameLabel">—</div>
            <div class="frame-counter" id="frameCounter">0/0</div>
        </div>
        <script>
            var tileUrls = [{urls_js}];
            var labels = [{labels_js}];
            var currentFrame = 0;
            var playing = false;
            var interval = null;
            var currentLayer = null;

            var map = L.map('map', {{
                center: [{map_center[0]}, {map_center[1]}],
                zoom: {zoom},
                zoomControl: false
            }});
            L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
                attribution: 'CartoDB'
            }}).addTo(map);

            function showFrame(idx) {{
                if (currentLayer) map.removeLayer(currentLayer);
                if (tileUrls[idx]) {{
                    currentLayer = L.tileLayer(tileUrls[idx], {{opacity: 0.85}}).addTo(map);
                }}
                document.getElementById('frameLabel').textContent = labels[idx] || '';
                document.getElementById('frameCounter').textContent = (idx+1) + '/' + tileUrls.length;
                currentFrame = idx;
            }}

            function nextFrame() {{
                showFrame((currentFrame + 1) % tileUrls.length);
            }}

            function prevFrame() {{
                showFrame((currentFrame - 1 + tileUrls.length) % tileUrls.length);
            }}

            function togglePlay() {{
                playing = !playing;
                document.getElementById('playBtn').innerHTML = playing ? '&#9646;&#9646; PAUSE' : '&#9654; PLAY';
                if (playing) {{
                    interval = setInterval(nextFrame, 1500);
                }} else {{
                    clearInterval(interval);
                }}
            }}

            if (tileUrls.length > 0) showFrame(0);
        </script>
    </body>
    </html>
    """
    return html
