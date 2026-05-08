"""CRUD 操作 — token_scores / token_reports / scan_logs"""

from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select, func, desc, asc, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import TokenScore, TokenReport, ScanLog


# ═══════════════════════════════════════════
# Token Scores
# ═══════════════════════════════════════════

async def get_latest_scores(
    db: AsyncSession,
    risk_level: Optional[str] = None,
    sort_by: str = "total_score",
    order: str = "asc",
    page: int = 1,
    page_size: int = 50,
    search: Optional[str] = None,
) -> tuple[list[TokenScore], int]:
    """
    获取每个币种的最新评分 (去重: 同一 symbol 只取最新一条)
    支持: 风险等级筛选、排序、分页、搜索
    """
    # 子查询: 每个 symbol 的最新 evaluated_at
    latest_subq = (
        select(
            TokenScore.symbol,
            func.max(TokenScore.evaluated_at).label("max_eval")
        )
        .group_by(TokenScore.symbol)
        .subquery()
    )

    # 主查询: JOIN 子查询获取最新记录
    query = (
        select(TokenScore)
        .join(
            latest_subq,
            and_(
                TokenScore.symbol == latest_subq.c.symbol,
                TokenScore.evaluated_at == latest_subq.c.max_eval,
            )
        )
    )

    # 筛选
    if risk_level:
        query = query.where(TokenScore.risk_level == risk_level)

    if search:
        search_pattern = f"%{search.upper()}%"
        query = query.where(
            or_(
                TokenScore.symbol.ilike(search_pattern),
                TokenScore.name.ilike(search_pattern),
            )
        )

    # 计数 (用于分页)
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # 排序
    sort_column = getattr(TokenScore, sort_by, TokenScore.total_score)
    if order == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))

    # 分页
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    tokens = result.scalars().all()

    return list(tokens), total


async def get_token_detail(db: AsyncSession, symbol: str) -> Optional[TokenScore]:
    """获取单个币种最新评分"""
    query = (
        select(TokenScore)
        .where(TokenScore.symbol == symbol.upper())
        .order_by(desc(TokenScore.evaluated_at))
        .limit(1)
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_token_history(
    db: AsyncSession,
    symbol: str,
    days: int = 30,
) -> list[TokenScore]:
    """获取币种评分历史 (近 N 天)"""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    query = (
        select(TokenScore)
        .where(
            and_(
                TokenScore.symbol == symbol.upper(),
                TokenScore.evaluated_at >= since,
            )
        )
        .order_by(asc(TokenScore.evaluated_at))
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def upsert_token_score(db: AsyncSession, data: dict) -> TokenScore:
    """写入评分结果 (每次评估一条新记录，不覆盖历史)"""
    score = TokenScore(**data)
    db.add(score)
    await db.flush()
    return score


async def bulk_insert_scores(db: AsyncSession, records: list[dict]) -> int:
    """批量写入评分 (Worker 用)"""
    objects = [TokenScore(**r) for r in records]
    db.add_all(objects)
    await db.flush()
    return len(objects)


# ═══════════════════════════════════════════
# Token Reports
# ═══════════════════════════════════════════

async def get_token_report(
    db: AsyncSession,
    symbol: str,
    report_type: str = "full",
) -> Optional[TokenReport]:
    """获取最新报告"""
    query = (
        select(TokenReport)
        .where(
            and_(
                TokenReport.symbol == symbol.upper(),
                TokenReport.report_type == report_type,
            )
        )
        .order_by(desc(TokenReport.generated_at))
        .limit(1)
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def save_report(db: AsyncSession, data: dict) -> TokenReport:
    """保存报告"""
    report = TokenReport(**data)
    db.add(report)
    await db.flush()
    return report


# ═══════════════════════════════════════════
# Scan Logs
# ═══════════════════════════════════════════

async def create_scan_log(db: AsyncSession, batch_id: str, total_tokens: int) -> ScanLog:
    """创建扫描日志"""
    log = ScanLog(batch_id=batch_id, total_tokens=total_tokens)
    db.add(log)
    await db.flush()
    return log


async def update_scan_log(
    db: AsyncSession,
    batch_id: str,
    completed: int = 0,
    failed: int = 0,
    status: str = "running",
) -> Optional[ScanLog]:
    """更新扫描进度"""
    query = (
        select(ScanLog)
        .where(ScanLog.batch_id == batch_id)
        .order_by(desc(ScanLog.started_at))
        .limit(1)
    )
    result = await db.execute(query)
    log = result.scalar_one_or_none()
    if log:
        log.completed = completed
        log.failed = failed
        log.status = status
        if status in ("completed", "failed"):
            log.finished_at = datetime.now(timezone.utc)
        await db.flush()
    return log


async def get_latest_scan_log(db: AsyncSession) -> Optional[ScanLog]:
    """获取最近一次扫描日志"""
    query = select(ScanLog).order_by(desc(ScanLog.started_at)).limit(1)
    result = await db.execute(query)
    return result.scalar_one_or_none()
