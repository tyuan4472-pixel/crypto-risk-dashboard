"""Celery 客户端 — 从 FastAPI 触发异步任务

用于 API 端点调用 Celery Worker 执行评估任务。
"""

from celery import Celery
from app.config import settings

# 创建与 Worker 共享的 Celery 实例 (只发任务，不执行)
celery_app = Celery(
    "crypto_risk",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
)


def trigger_single_evaluation(symbol: str):
    """触发单币种评估 (异步)"""
    return celery_app.send_task(
        "tasks.evaluate_single",
        args=[symbol],
    )


def trigger_full_scan():
    """触发全量扫描 (异步)"""
    return celery_app.send_task("tasks.run_daily_scan")


def get_task_status(task_id: str) -> dict:
    """查询任务状态"""
    result = celery_app.AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.ready() else None,
    }
