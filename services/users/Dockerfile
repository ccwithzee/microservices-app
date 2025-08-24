# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt .
# Upgrade pip + setuptools first, then install deps
RUN pip install --no-cache-dir --upgrade pip setuptools>=78.1.1 && \
    pip install --no-cache-dir -r requirements.txt

# ------------------------
# Test stage
# ------------------------
FROM base AS test
ENV PYTHONPATH=/app
COPY app ./app
COPY tests ./tests
CMD ["pytest", "-q", "--disable-warnings", "--maxfail=1"]

# ------------------------
# Runtime stage
# ------------------------
FROM base AS runtime
ENV PYTHONPATH=/app
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
COPY app ./app
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:8080/healthz || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
