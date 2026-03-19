#!/bin/sh
# Start FastAPI in background
uvicorn api.main:app --host 127.0.0.1 --port 8000 --workers 2 &

# Start nginx in foreground
nginx -g "daemon off;"
