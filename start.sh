#!/bin/sh
# Start FastAPI in background
uvicorn api.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 2 \
    --timeout-keep-alive 30 \
    --limit-max-requests 2000 &

# Start nginx in foreground (port 8080)
nginx -g "daemon off;"
