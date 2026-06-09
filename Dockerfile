# Multi-stage build: compile the React frontend, then run the FastAPI backend
# which also serves that built frontend (single service, single origin).

# --- Stage 1: build the React frontend -------------------------------------
FROM node:22-slim AS frontend
WORKDIR /frontend
COPY frontend-react/package*.json ./
RUN npm ci
COPY frontend-react/ ./
RUN npm run build          # -> /frontend/dist

# --- Stage 2: Python runtime ------------------------------------------------
FROM python:3.12-slim AS runtime

# onnxruntime (pulled in by fastembed) needs libgomp at runtime.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    COPILOT_HOST=0.0.0.0 \
    COPILOT_SERVE_FRONTEND=true

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Backend source.
COPY app ./app
COPY run.py ./

# Built frontend from stage 1 -> where settings.frontend_dir expects it.
COPY --from=frontend /frontend/dist ./frontend-react/dist

# Render/Railway inject $PORT; default to 8080 locally. Single worker because
# the embedded Qdrant vector store is a single-process resource.
ENV PORT=8080
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1"]
