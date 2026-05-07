"""币种评估 API"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from app.models.schemas import (
    TokenScoreResponse,
    TokenDetailResponse,
    TokenListResponse,
    TriggerResponse,
    RiskLevel,
)
from app.services.risk_engine import RiskEngine
from app.services.data_fetcher import DataFetcher

router = APIRouter()
risk_engine = RiskEngine()
data_fetcher = DataFetcher()


@router.get("", response_model=TokenListResponse)
async def list_tokens(
    risk_level: Optional[RiskLevel] = Query(None, description="按风险等级筛选"),
    sort_by: str = Query("total_score", description="排序字段"),
    order: str = Query("asc", description="升序 asc / 降序 desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None, description="币种名称/Symbol 搜索"),
):
    """
    获取币种评分列表。
    支持按风险等级筛选、排序、分页和搜索。
    """
    return {
        "tokens": [],
        "total": 0,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{symbol}", response_model=TokenDetailResponse)
async def get_token_detail(symbol: str):
    """
    获取单个币种详细评分报告。
    包含 8 维度得分、12 项检查指标、风险点明细。
    """
    # TODO: 从数据库查询
    return {
        "symbol": symbol.upper(),
        "total_score": 0,
        "risk_level": RiskLevel.medium,
    }


@router.post("/{symbol}/trigger", response_model=TriggerResponse)
async def trigger_evaluation(symbol: str):
    """
    手动触发单币种风险评估。
    同步执行并返回最新结果。
    """
    # TODO: 触发 Celery 任务
    return {
        "symbol": symbol.upper(),
        "task_id": "",
        "status": "pending",
    }


@router.get("/{symbol}/report")
async def get_token_report(
    symbol: str,
    report_type: str = Query("full", description="full | summary | alert"),
):
    """
    获取币种调研报告（完整版/摘要版/告警版）。
    高风险币种会生成详细网页报告。
    """
    return {
        "symbol": symbol.upper(),
        "report_type": report_type,
        "content": "",
    }
