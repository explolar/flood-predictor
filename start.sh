#!/bin/sh
# Start FastAPI
uvicorn api.main:app \
    --host 127.0.0.1 \
    --port 8000 \
    --workers 2 \
    --timeout-keep-alive 30 \
    --limit-max-requests 2000 &

# Wait for uvicorn to be ready (python is always available)
for i in $(seq 1 60); do
    if python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" 2>/dev/null; then
        break
    fi
    sleep 1
done

# Start nginx in foreground
nginx -g "daemon off;"
