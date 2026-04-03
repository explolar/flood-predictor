#!/bin/sh
PORT="${PORT:-8080}"
exec uvicorn api.main:app \
    --host 0.0.0.0 \
    --port "$PORT" \
    --workers 2 \
    --timeout-keep-alive 30 \
    --limit-max-requests 2000
