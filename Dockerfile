# syntax=docker/dockerfile:1

# --- Frontend build ---
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- Python runtime ---
FROM python:3.11-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_ROOT=/app

WORKDIR /app

# Build deps for hdbscan / umap-learn wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY app/ ./app/
COPY main.py .
COPY data/ ./data/
COPY scripts/start.sh ./scripts/start.sh
RUN chmod +x ./scripts/start.sh

COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Persistent dirs (override with Railway volumes via DATA_DIR / OUTPUTS_DIR)
RUN mkdir -p /app/data /app/data/uploads /app/outputs /app/logs

EXPOSE 8000

CMD ["./scripts/start.sh"]
