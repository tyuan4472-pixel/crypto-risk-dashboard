"""调度器 API — 查看/触发扫描任务"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import crud
from app.worker_client import trigger_full_scan, get_task_status

router = APIRouter()


@router.get("/status")
async def scheduler_status(db: AsyncSession = Depends(get_db)):
    """获取最近一次扫描状态"""
    log = await crud.get_latest_scan_log(db)
    if not log:
        return {"status": "no_scans", "message": "尚未执行过扫描"}

    return {
        "batch_id": log.batch_id,
        "status": log.status,
        "total_tokens": log.total_tokens,
        "completed": log.completed,
        "failed": log.failed,
        "started_at": log.started_at.isoformat(),
        "finished_at": log.finished_at.isoformat() if log.finished_at else None,
    }


@router.post("/trigger")
async def trigger_scan():
    """手动触发全量扫描"""
    task = trigger_full_scan()
    return {
        "task_id": task.id if task else "unknown",
        "status": "submitted",
        "message": "全量扫描已提交，通过 GET /api/scheduler/status 查看进度",
    }


@router.get("/task/{task_id}")
async def task_status(task_id: str):
    """查询单个任务状态"""
    return get_task_status(task_id)
