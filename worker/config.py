"""Worker 配置 — 从环境变量读取

与 backend/app/config.py 保持一致的 Key 定义，
但 Worker 运行时独立于 FastAPI 进程。
"""

import os


class WorkerConfig:
    # 数据库 (同步, Worker 不用 async)
    DB_HOST = os.getenv("DB_HOST", "postgres")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_USER = os.getenv("DB_USER", "risk")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "changeme")
    DB_NAME = os.getenv("DB_NAME", "crypto_risk")

    @property
    def database_url(self) -> str:
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # Redis
    REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

    # 外部 API (供 data_fetcher 使用)
    # ⚠️ 填入 .env，不硬编码
    CMC_API_KEY = os.getenv("CMC_API_KEY", "")
    COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY", "")
    KUCOIN_API_KEY = os.getenv("KUCOIN_API_KEY", "")
    KUCOIN_API_SECRET = os.getenv("KUCOIN_API_SECRET", "")
    KUCOIN_API_PASSPHRASE = os.getenv("KUCOIN_API_PASSPHRASE", "")

    # AI 模型 (Phase 2)
    # ⚠️ 填入 .env
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")

    # 调度参数
    WORKER_CONCURRENCY = int(os.getenv("WORKER_CONCURRENCY", "10"))
    BATCH_SIZE = int(os.getenv("BATCH_SIZE", "50"))


config = WorkerConfig()
