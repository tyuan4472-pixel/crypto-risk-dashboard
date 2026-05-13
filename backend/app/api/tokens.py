"""币种评估 API — 连接真实数据库"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.schemas import (
    TokenListResponse, TokenScoreBrief, TokenDetailResponse,
    DimensionScores, CheckIndicators, RiskDetail, TriggerResponse,
    RiskLevel, ZombieDetection, ExtraData, SentimentData,
    LLMAnalysis, LLMRecommendation,
)
from app.models import crud

router = APIRouter()


@router.get("", response_model=TokenListResponse)
async def list_tokens(
    risk_level: Optional[str] = Query(None),
    sort_by: str = Query("total_score"),
    order: str = Query("asc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    tokens, total, risk_counts = await crud.get_latest_scores(
        db, risk_level=risk_level, sort_by=sort_by, order=order,
        page=page, page_size=page_size, search=search,
    )
    return TokenListResponse(
        tokens=[
            TokenScoreBrief(
                symbol=t.symbol, name=t.name or t.symbol,
                total_score=float(t.total_score), risk_level=t.risk_level,
                price_usd=float(t.price_usd) if t.price_usd else None,
                market_cap_usd=float(t.market_cap_usd) if t.market_cap_usd else None,
                volume_24h_usd=float(t.volume_24h_usd) if t.volume_24h_usd else None,
                evaluated_at=t.evaluated_at,
            ) for t in tokens
        ],
        total=total, page=page, page_size=page_size,
        risk_counts=risk_counts,
    )


def _parse_extra(rd: dict) -> ExtraData:
    """从 risk_details JSONB 解析扩展数据 (含嵌套新字段)"""
    extra = rd.get("extra", {}) if isinstance(rd, dict) else {}

    # 嵌套子字段
    exchange_dist = extra.get("exchange_distribution") or {}
    cross_val = extra.get("cross_validation") or {}
    cr_data = extra.get("cryptorank_data") or {}
    kc_mkt = extra.get("kucoin_market") or {}
    sentiment_raw = extra.get("sentiment_analysis") or {}

    sentiment = None
    if sentiment_raw and any(sentiment_raw.get(k) is not None for k in ("positive_pct", "negative_pct", "summary")):
        sentiment = SentimentData(
            positive_pct=sentiment_raw.get("positive_pct"),
            negative_pct=sentiment_raw.get("negative_pct"),
            summary=sentiment_raw.get("summary"),
            risks_found=sentiment_raw.get("risks_found", []),
        )

    # LLM 分析数据
    llm_raw = rd.get("llm_analysis") if isinstance(rd, dict) else None
    llm_analysis = None
    if llm_raw:
        recs = llm_raw.get("recommendations") or []
        llm_analysis = LLMAnalysis(
            summary=llm_raw.get("summary"),
            key_risks=llm_raw.get("key_risks", []),
            safe_factors=llm_raw.get("safe_factors", []),
            recommendations=[LLMRecommendation(**r) for r in recs if isinstance(r, dict)],
        )

    return ExtraData(
        # 原有字段
        market_cap_rank=extra.get("market_cap_rank"),
        holder_count=extra.get("holder_count"),
        ath_pct=extra.get("ath_pct"),
        circulating_supply=extra.get("circulating_supply"),
        total_supply=extra.get("total_supply"),
        kucoin_deposit_enabled=extra.get("kucoin_deposit_enabled"),
        kucoin_withdraw_enabled=extra.get("kucoin_withdraw_enabled"),
        github_commits_30d=extra.get("github_commits_30d"),
        developer_score=extra.get("developer_score"),
        community_score=extra.get("community_score"),
        top10_holder_ratio=extra.get("top10_holder_ratio"),
        # 交易所分布
        exchange_count=exchange_dist.get("exchange_count"),
        cex_count=exchange_dist.get("cex_count"),
        major_exchanges=exchange_dist.get("major_exchanges", []),
        kucoin_volume_share=exchange_dist.get("kucoin_volume_share"),
        # 交叉验证
        cg_cmc_divergence_pct=cross_val.get("cg_cmc_divergence_pct"),
        # CryptoRank
        cryptorank_rank=cr_data.get("rank"),
        fundraise_total_usd=cr_data.get("fundraise_total_usd"),
        fundraise_rounds=cr_data.get("fundraise_rounds"),
        top_vcs=cr_data.get("top_vcs", []),
        # KuCoin 订单簿
        kucoin_best_bid=kc_mkt.get("best_bid"),
        kucoin_best_ask=kc_mkt.get("best_ask"),
        kucoin_spread_pct=kc_mkt.get("spread_pct"),
        # 情绪分析
        sentiment=sentiment,
        # LLM 分析
        llm_analysis=llm_analysis,
    )


def _parse_indicators(rd: dict) -> CheckIndicators:
    """从 risk_details JSONB 解析 12+ 项检查指标"""
    ind = rd.get("indicators", {}) if isinstance(rd, dict) else {}
    extra = rd.get("extra", {}) if isinstance(rd, dict) else {}
    return CheckIndicators(
        volume_mcap_ratio=ind.get("volume_mcap_ratio"),
        market_cap_rank=extra.get("market_cap_rank"),
        liquidity_depth=ind.get("liquidity_depth"),
        vol_30d_exceeded=ind.get("vol_30d_exceeded", False),
        top10_holder_ratio=extra.get("top10_holder_ratio"),
        holder_count=extra.get("holder_count"),
        github_commits_30d=extra.get("github_commits_30d"),
        developer_score=extra.get("developer_score"),
        community_score=extra.get("community_score"),
        contract_audited=ind.get("contract_audited"),
        is_honeypot=ind.get("is_honeypot", False),
        is_proxy=ind.get("is_proxy", False),
        unlock_event_30d=ind.get("unlock_event_30d", False),
        kucoin_deposit_enabled=extra.get("kucoin_deposit_enabled"),
        kucoin_withdraw_enabled=extra.get("kucoin_withdraw_enabled"),
        ath_pct=extra.get("ath_pct"),
        circulating_supply=extra.get("circulating_supply"),
        total_supply=extra.get("total_supply"),
    )


def _parse_zombie(rd: dict) -> ZombieDetection:
    zombie = rd.get("zombie", {}) if isinstance(rd, dict) else {}
    return ZombieDetection(
        score=zombie.get("score", 0),
        flags=zombie.get("flags", []),
    )


def _parse_risk_details(rd) -> list[RiskDetail]:
    """从 risk_details 解析详细信息列表"""
    items = rd.get("items", rd) if isinstance(rd, dict) else rd
    if not isinstance(items, list):
        items = rd if isinstance(rd, list) else []
    result = []
    for item in items:
        if isinstance(item, dict) and item.get("category"):
            result.append(RiskDetail(
                category=item.get("category", ""),
                severity=item.get("severity", "medium"),
                description=item.get("description", ""),
                source=item.get("source", ""),
            ))
    return result


@router.get("/{symbol}", response_model=TokenDetailResponse)
async def get_token_detail(symbol: str, db: AsyncSession = Depends(get_db)):
    token = await crud.get_token_detail(db, symbol)
    if not token:
        raise HTTPException(status_code=404, detail=f"未找到 {symbol.upper()} 的评估数据")

    rd = token.risk_details or {}

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

    history = await crud.get_token_history(db, symbol, days=30)
    history_30d = [{"date": h.evaluated_at.isoformat(), "total_score": float(h.total_score)} for h in history]

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
        indicators=_parse_indicators(rd),
        zombie=_parse_zombie(rd),
        risk_details=_parse_risk_details(rd),
        extra=_parse_extra(rd),
        sentiment_summary=token.sentiment_summary,
        history_30d=history_30d,
    )


@router.post("/{symbol}/trigger", response_model=TriggerResponse)
async def trigger_evaluation(symbol: str, db: AsyncSession = Depends(get_db)):
    from app.worker_client import trigger_single_evaluation
    task = trigger_single_evaluation(symbol.upper())
    return TriggerResponse(symbol=symbol.upper(), task_id=task.id if task else "direct", status="pending")


@router.get("/{symbol}/report")
async def get_token_report(symbol: str, report_type: str = Query("full"), db: AsyncSession = Depends(get_db)):
    report = await crud.get_token_report(db, symbol, report_type)
    if not report:
        raise HTTPException(status_code=404, detail=f"未找到 {symbol.upper()} 的 {report_type} 报告")
    return {
        "symbol": report.symbol, "report_type": report.report_type,
        "title": report.title, "content": report.content,
        "generated_at": report.generated_at.isoformat(), "trigger_source": report.trigger_source,
    }
