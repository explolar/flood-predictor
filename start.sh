#!/bin/sh
# Start FastAPI with optimized settings
uvicorn api.main:app \
    --host 127.0.0.1 \
    --port 8000 \
    --workers 4 \
    --timeout-keep-alive 30 \
    --limit-max-requests 2000 &

# Start nginx in foreground
nginx -g "daemon off;"
