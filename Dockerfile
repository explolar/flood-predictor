FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install deps first for Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

# MODE=api → FastAPI, default → Streamlit
ENV MODE=streamlit
CMD if [ "$MODE" = "api" ]; then \
        uvicorn api.main:app --host 0.0.0.0 --port 8080; \
    else \
        streamlit run app.py --server.port=8080 --server.address=0.0.0.0; \
    fi
