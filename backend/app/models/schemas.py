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


# ── 8 维度得分 ──
class DimensionScores(BaseModel):
    liquidity: float = 0       # 市场流动性
    volatility: float = 0      # 价格波动性
    concentration: float = 0   # 持仓集中度
    fundamental: float = 0     # 项目基本面
    sentiment: float = 0       # 舆情异常
    compliance: float = 0      # 交易所合规
    security: float = 0        # 智能合约安全
    macro: float = 0           # 宏观关联风险


# ── 12 项检查指标 ──
class CheckIndicators(BaseModel):
    volume_mcap_ratio: Optional[float] = None        # 24h成交量/市值比
    liquidity_depth: Optional[float] = None           # ±2% 流动性深度
    vol_7d_exceeded: bool = False                     # 7d 波动率超阈值
    top10_holder_ratio: Optional[float] = None        # 前10地址持仓占比
    github_commits_30d: Optional[int] = None          # GitHub 近30天 commit
    team_verified: bool = False                       # 团队身份验证
    negative_sentiment_pct: Optional[float] = None    # 负面情绪占比
    mentions_anomaly_7d: bool = False                 # 近7d 异常提及
    exchange_delist_warning: bool = False             # 交易所下架风险
    contract_audited: bool = False                    # 合约审计状态
    unlock_event_30d: bool = False                    # 30d 内代币解锁
    btc_beta_anomaly: bool = False                    # BTC Beta 异常


# ── 风险明细条目 ──
class RiskDetail(BaseModel):
    category: str          # 舆情异常 / 友商下架 / 合约漏洞 等
    severity: str          # high / medium / low
    description: str
    source: str            # 来源链接
    detected_at: datetime


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
    risk_details: list[RiskDetail] = []
    sentiment_summary: Optional[str] = None


class TokenListResponse(BaseModel):
    tokens: list[TokenScoreBrief]
    total: int
    page: int
    page_size: int


class TokenDetailResponse(TokenScoreResponse):
    history_30d: list[dict] = []   # 近 30 天评分趋势


class TriggerResponse(BaseModel):
    symbol: str
    task_id: str
    status: str


class ExportRequest(BaseModel):
    symbols: Optional[list[str]] = None
    risk_level: Optional[RiskLevel] = None
    format: str = "csv"  # csv | pdf
