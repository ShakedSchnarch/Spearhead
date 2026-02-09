# syntax=docker/dockerfile:1.7

FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend-app
COPY frontend-app/package*.json ./
RUN npm ci
COPY frontend-app/ ./
RUN npm run build

FROM python:3.11-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src
ENV PORT=8080
ENV APP__ENABLE_LEGACY_ROUTES=false

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

COPY --from=frontend-builder /app/frontend-app/dist ./frontend-app/dist
RUN mkdir -p /app/data

EXPOSE 8080
CMD ["sh", "-c", "uvicorn spearhead.api.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
