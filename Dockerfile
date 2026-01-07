FROM node:18-slim AS frontend-build
WORKDIR /app/frontend-app
COPY frontend-app/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend-app .
RUN npm run build

FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app

# System deps for openpyxl and sqlite
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=frontend-build /app/frontend-app/dist /app/frontend-app/dist

EXPOSE 8000
CMD ["uvicorn", "iron_view.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
