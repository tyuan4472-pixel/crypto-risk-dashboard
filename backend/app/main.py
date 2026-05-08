"""Crypto Risk Dashboard — FastAPI 主入口"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.api.tokens import router as tokens_router
from app.api.health import router as health_router
from app.api.scheduler import router as scheduler_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期 — 启动时建表 (如不存在)"""
    if settings.environment == "development":
        await init_db()
    yield


app = FastAPI(
    title="Crypto Risk Dashboard API",
    description="加密货币风控评估系统 — 基于 KuCoin 现货币种",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — 内部工具，允许所有来源
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(health_router, tags=["Health"])
app.include_router(tokens_router, prefix="/api/tokens", tags=["Tokens"])
app.include_router(scheduler_router, prefix="/api/scheduler", tags=["Scheduler"])
