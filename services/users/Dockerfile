FROM python:3.11-slim AS base
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Test stage
FROM base AS test
ENV PYTHONPATH=/app
COPY app ./app
COPY tests ./tests
RUN pip install --no-cache-dir pytest
CMD ["pytest", "-q"]

# Runtime stage
FROM base AS runtime
ENV PYTHONPATH=/app
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
COPY app ./app
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
