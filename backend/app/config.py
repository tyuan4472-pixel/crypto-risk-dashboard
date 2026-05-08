import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 数据库
    db_host: str = "postgres"
    db_port: int = 5432
    db_user: str = "risk"
    db_password: str = "changeme"
    db_name: str = "crypto_risk"

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def database_url_sync(self) -> str:
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # 外部 API
    cmc_api_key: str = ""
    coingecko_api_key: str = ""
    goplus_api_key: str = ""
    kucoin_api_key: str = ""
    kucoin_api_secret: str = ""
    kucoin_api_passphrase: str = ""
    x_bearer_token: str = ""

    # AI 模型
    openrouter_api_key: str = ""
    dashscope_api_key: str = ""

    # 应用
    environment: str = "development"
    log_level: str = "info"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
