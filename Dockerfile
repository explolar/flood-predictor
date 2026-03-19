# Stage 1: Build React frontend
FROM node:20-alpine AS frontend-build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# Stage 2: Python API + static frontend
FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential nginx \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/ ./api/
COPY gee_functions/ ./gee_functions/
COPY ml_models/ ./ml_models/
COPY utils/ ./utils/
COPY ui_components/ ./ui_components/
COPY training/ ./training/

COPY --from=frontend-build /app/dist /var/www/html

COPY nginx.conf /etc/nginx/conf.d/default.conf
RUN rm -f /etc/nginx/sites-enabled/default

COPY start.sh /app/start.sh
RUN sed -i 's/\r$//' /app/start.sh && chmod +x /app/start.sh
RUN sed -i 's/\r$//' /etc/nginx/conf.d/default.conf

EXPOSE 8080

CMD ["/bin/sh", "/app/start.sh"]
