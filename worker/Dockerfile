# Worker Dockerfile — built from project root context
# docker compose 中设置 build.context: . + build.dockerfile: worker/Dockerfile

# 国内构建用阿里云镜像，海外部署改回 python:3.12-slim
FROM registry.cn-hangzhou.aliyuncs.com/library/python:3.12-slim

WORKDIR /app

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Worker 依赖
COPY worker/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 复制 backend/app (Worker 复用 services 层: data_fetcher, risk_engine, model_router)
COPY backend/app /app/backend/app/

# 复制 Worker 代码
COPY worker/ /app/

# Python path 配置: 让 import app.services.xxx 正常工作
ENV PYTHONPATH="/app/backend:${PYTHONPATH}"

# 默认: celery worker
CMD ["celery", "-A", "tasks", "worker", "--loglevel=info", "--concurrency=10"]
