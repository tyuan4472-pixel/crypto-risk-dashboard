"""Pydantic 数据模型"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel


class RiskLevel(str, Enum):
    extreme = "极高"
    high = "高"
    medium = "中"
    low = "低"
    minimal = "极低"


class DimensionScores(BaseModel):
    liquidity: float = 0
    volatility: float = 0
    concentration: float = 0
    fundamental: float = 0
    sentiment: float = 0
    compliance: float = 0
    security: float = 0
    macro: float = 0


class CheckIndicators(BaseModel):
    volume_mcap_ratio: Optional[float] = None
    market_cap_rank: Optional[int] = None
    liquidity_depth: Optional[float] = None
    vol_30d_exceeded: bool = False
    top10_holder_ratio: Optional[float] = None
    holder_count: Optional[int] = None
    github_commits_30d: Optional[int] = None
    developer_score: Optional[float] = None
    community_score: Optional[float] = None
    team_verified: bool = False
    negative_sentiment_pct: Optional[float] = None
    mentions_anomaly_7d: bool = False
    exchange_delist_warning: bool = False
    contract_audited: Optional[bool] = None
    is_honeypot: bool = False
    is_proxy: bool = False
    unlock_event_30d: bool = False
    btc_beta_anomaly: bool = False
    kucoin_deposit_enabled: Optional[bool] = None
    kucoin_withdraw_enabled: Optional[bool] = None
    ath_pct: Optional[float] = None
    circulating_supply: Optional[float] = None
    total_supply: Optional[float] = None


class ZombieDetection(BaseModel):
    score: int = 0
    flags: list[str] = []


class RiskDetail(BaseModel):
    category: str
    severity: str
    description: str
    source: str
    detected_at: Optional[datetime] = None


class SentimentData(BaseModel):
    positive_pct: Optional[float] = None
    negative_pct: Optional[float] = None
    summary: Optional[str] = None
    risks_found: list[str] = []


class LLMRecommendation(BaseModel):
    priority: str = ""
    action: str = ""
    reason: str = ""


class LLMAnalysis(BaseModel):
    summary: Optional[str] = None
    key_risks: list[str] = []
    safe_factors: list[str] = []
    recommendations: list[LLMRecommendation] = []


class ExtraData(BaseModel):
    market_cap_rank: Optional[int] = None
    holder_count: Optional[int] = None
    ath_pct: Optional[float] = None
    circulating_supply: Optional[float] = None
    total_supply: Optional[float] = None
    kucoin_deposit_enabled: Optional[bool] = None
    kucoin_withdraw_enabled: Optional[bool] = None
    github_commits_30d: Optional[int] = None
    developer_score: Optional[float] = None
    community_score: Optional[float] = None
    top10_holder_ratio: Optional[float] = None
    # Exchange distribution
    exchange_count: Optional[int] = None
    cex_count: Optional[int] = None
    major_exchanges: list[str] = []
    kucoin_volume_share: Optional[float] = None
    # Cross-validation (CG vs CMC)
    cg_cmc_divergence_pct: Optional[float] = None
    # CryptoRank fundraising
    cryptorank_rank: Optional[int] = None
    fundraise_total_usd: Optional[float] = None
    fundraise_rounds: Optional[int] = None
    top_vcs: list[str] = []
    # KuCoin orderbook
    kucoin_best_bid: Optional[float] = None
    kucoin_best_ask: Optional[float] = None
    kucoin_spread_pct: Optional[float] = None
    # Sentiment analysis
    sentiment: Optional[SentimentData] = None
    # LLM analysis
    llm_analysis: Optional[LLMAnalysis] = None


# ── API 响应模型 ──
class TokenScoreBrief(BaseModel):
    symbol: str
    name: str
    total_score: float
    risk_level: RiskLevel
    price_usd: Optional[float] = None
    market_cap_usd: Optional[float] = None
    volume_24h_usd: Optional[float] = None
    evaluated_at: datetime


class TokenScoreResponse(TokenScoreBrief):
    dimensions: DimensionScores
    indicators: CheckIndicators
    zombie: ZombieDetection = ZombieDetection()
    risk_details: list[RiskDetail] = []
    sentiment_summary: Optional[str] = None


class TokenListResponse(BaseModel):
    tokens: list[TokenScoreBrief]
    total: int
    page: int
    page_size: int


class TokenDetailResponse(TokenScoreResponse):
    extra: ExtraData = ExtraData()
    history_30d: list[dict] = []


class TriggerResponse(BaseModel):
    symbol: str
    task_id: str
    status: str


class ExportRequest(BaseModel):
    symbols: Optional[list[str]] = None
    risk_level: Optional[RiskLevel] = None
    format: str = "csv"
