cat <<EOF > app.py
from flask import Flask
import ee
import os

app = Flask(__name__)

@app.route('/')
def hello():
    return "Bihar Hydro-Climatic Risk Atlas - Flask Backend Active"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
EOF