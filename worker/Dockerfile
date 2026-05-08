# Worker Dockerfile — built from project root context
# docker compose 中设置 build.context: . + build.dockerfile: worker/Dockerfile

FROM python:3.12-slim

WORKDIR /app

# 国内 apt 源加速
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null; \
    sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list 2>/dev/null; true

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# pip 国内源
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip config set global.trusted-host mirrors.aliyun.com

# Worker 依赖
COPY worker/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 复制 backend/app (Worker 复用 services 层)
COPY backend/app /app/backend/app/

# 复制 Worker 代码
COPY worker/ /app/

# Python path: import app.services.xxx
ENV PYTHONPATH="/app/backend:${PYTHONPATH}"

# 默认: celery worker
CMD ["celery", "-A", "tasks", "worker", "--loglevel=info", "--concurrency=10"]
