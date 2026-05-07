"""Crypto Risk Dashboard — FastAPI 主入口"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.tokens import router as tokens_router
from app.api.health import router as health_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时
    yield
    # 关闭时


app = FastAPI(
    title="Crypto Risk Dashboard API",
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
