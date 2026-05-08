"""币种评估 API — 连接真实数据库"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.schemas import (
    TokenListResponse,
    TokenScoreBrief,
    TokenDetailResponse,
    DimensionScores,
    CheckIndicators,
    RiskDetail,
    TriggerResponse,
    RiskLevel,
)
from app.models import crud

router = APIRouter()


@router.get("", response_model=TokenListResponse)
async def list_tokens(
    risk_level: Optional[str] = Query(None, description="按风险等级筛选: 极高/高/中/低/极低"),
    sort_by: str = Query("total_score", description="排序字段"),
    order: str = Query("asc", description="升序 asc / 降序 desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None, description="币种名称/Symbol 搜索"),
    db: AsyncSession = Depends(get_db),
):
    """获取币种评分列表 (支持筛选/排序/分页/搜索)"""
    tokens, total = await crud.get_latest_scores(
        db,
        risk_level=risk_level,
        sort_by=sort_by,
        order=order,
        page=page,
        page_size=page_size,
        search=search,
    )

    return TokenListResponse(
        tokens=[
            TokenScoreBrief(
                symbol=t.symbol,
                name=t.name or t.symbol,
                total_score=float(t.total_score),
                risk_level=t.risk_level,
                price_usd=float(t.price_usd) if t.price_usd else None,
                market_cap_usd=float(t.market_cap_usd) if t.market_cap_usd else None,
                volume_24h_usd=float(t.volume_24h_usd) if t.volume_24h_usd else None,
                evaluated_at=t.evaluated_at,
            )
            for t in tokens
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{symbol}", response_model=TokenDetailResponse)
async def get_token_detail(
    symbol: str,
    db: AsyncSession = Depends(get_db),
):
    """获取单个币种详细评分 (8 维度 + 12 指标 + 风险明细)"""
    token = await crud.get_token_detail(db, symbol)
    if not token:
        raise HTTPException(status_code=404, detail=f"未找到 {symbol.upper()} 的评估数据")

    # 组装 8 维度得分
    dimensions = DimensionScores(
        liquidity=float(token.liquidity_score or 0),
        volatility=float(token.volatility_score or 0),
        concentration=float(token.concentration_score or 0),
        fundamental=float(token.fundamental_score or 0),
        sentiment=float(token.sentiment_score or 0),
        compliance=float(token.compliance_score or 0),
        security=float(token.security_score or 0),
        macro=float(token.macro_score or 0),
    )

    # 解析 risk_details JSON
    risk_details = []
    if token.risk_details:
        for rd in token.risk_details:
            risk_details.append(RiskDetail(
                category=rd.get("category", ""),
                severity=rd.get("severity", "medium"),
                description=rd.get("description", ""),
                source=rd.get("source", ""),
                detected_at=rd.get("detected_at", token.evaluated_at),
            ))

    # 获取 30 天评分历史
    history = await crud.get_token_history(db, symbol, days=30)
    history_30d = [
        {
            "date": h.evaluated_at.isoformat(),
            "total_score": float(h.total_score),
        }
        for h in history
    ]

    return TokenDetailResponse(
        symbol=token.symbol,
        name=token.name or token.symbol,
        total_score=float(token.total_score),
        risk_level=token.risk_level,
        price_usd=float(token.price_usd) if token.price_usd else None,
        market_cap_usd=float(token.market_cap_usd) if token.market_cap_usd else None,
        volume_24h_usd=float(token.volume_24h_usd) if token.volume_24h_usd else None,
        evaluated_at=token.evaluated_at,
        dimensions=dimensions,
        indicators=CheckIndicators(),  # TODO: 从 risk_details 解析 12 项指标
        risk_details=risk_details,
        sentiment_summary=token.sentiment_summary,
        history_30d=history_30d,
    )


@router.post("/{symbol}/trigger", response_model=TriggerResponse)
async def trigger_evaluation(
    symbol: str,
    db: AsyncSession = Depends(get_db),
):
    """
    手动触发单币种风险评估。
    异步下发到 Celery Worker，返回 task_id 用于轮询状态。
    """
    from app.worker_client import trigger_single_evaluation
    task = trigger_single_evaluation(symbol.upper())

    return TriggerResponse(
        symbol=symbol.upper(),
        task_id=task.id if task else "direct",
        status="pending",
    )


@router.get("/{symbol}/report")
async def get_token_report(
    symbol: str,
    report_type: str = Query("full", description="full | summary | alert"),
    db: AsyncSession = Depends(get_db),
):
    """获取币种调研报告"""
    report = await crud.get_token_report(db, symbol, report_type)
    if not report:
        raise HTTPException(
            status_code=404,
            detail=f"未找到 {symbol.upper()} 的 {report_type} 报告，请先手动触发评估",
        )

    return {
        "symbol": report.symbol,
        "report_type": report.report_type,
        "title": report.title,
        "content": report.content,
        "generated_at": report.generated_at.isoformat(),
        "trigger_source": report.trigger_source,
    }
