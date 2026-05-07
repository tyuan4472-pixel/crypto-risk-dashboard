FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 默认 celery worker, 可在 docker-compose 中覆盖
CMD ["celery", "-A", "tasks", "worker", "--loglevel=info", "--concurrency=10"]
