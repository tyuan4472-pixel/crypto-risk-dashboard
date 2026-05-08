"""Worker 配置 — 从环境变量读取

与 backend/app/config.py 保持一致的 Key 定义，
但 Worker 运行时独立于 FastAPI 进程。
"""

import os
from dotenv import load_dotenv

# 加载 backend/.env
env_path = os.path.join(os.path.dirname(__file__), '..', 'backend', '.env')
load_dotenv(env_path, override=True)

# 本地开发强制兜底：Docker 内网主机名 → localhost
_redis = os.getenv("REDIS_URL", "")
if not _redis or "redis:6379" in _redis or "postgres:" in _redis:
    os.environ["REDIS_URL"] = "redis://localhost:6379/0"
    print(f"[Worker] REDIS_URL fixed → redis://localhost:6379/0 (was: {_redis!r})")

_db = os.getenv("DB_HOST", "")
if not _db or _db in ("postgres", "redis"):
    os.environ["DB_HOST"] = "localhost"
    print(f"[Worker] DB_HOST fixed → localhost (was: {_db!r})")


class WorkerConfig:
    # 数据库
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_USER = os.getenv("DB_USER", "risk")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "changeme")
    DB_NAME = os.getenv("DB_NAME", "crypto_risk")

    @property
    def database_url(self) -> str:
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # Redis
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # 外部 API
    CMC_API_KEY = os.getenv("CMC_API_KEY", "")
    COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY", "")
    GOPLUS_API_KEY = os.getenv("GOPLUS_API_KEY", "")
    KUCOIN_API_KEY = os.getenv("KUCOIN_API_KEY", "")
    KUCOIN_API_SECRET = os.getenv("KUCOIN_API_SECRET", "")
    KUCOIN_API_PASSPHRASE = os.getenv("KUCOIN_API_PASSPHRASE", "")

    # AI 模型
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")

    # 调度参数
    WORKER_CONCURRENCY = int(os.getenv("WORKER_CONCURRENCY", "10"))
    BATCH_SIZE = int(os.getenv("BATCH_SIZE", "50"))


config = WorkerConfig()
