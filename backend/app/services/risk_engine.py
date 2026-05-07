"""风险评估引擎 — 8 维度评分 + 12 项检查指标

评分规则: 每维度 0-100 分，总分 = 加权求和（分数越高 = 风险越低 = 越安全）

维度权重 (可根据历史回测调整):
  1. 市场流动性     15%
  2. 价格波动性     15%
  3. 持仓集中度     12%
  4. 项目基本面     12%
  5. 舆情异常       12%
  6. 交易所合规     12%
  7. 智能合约安全   10%
  8. 宏观关联风险   12%
"""

from dataclasses import dataclass, field
from datetime import datetime
import math

from app.services.data_fetcher import TokenDataPayload


# 维度权重
WEIGHTS = {
    "liquidity": 0.15,
    "volatility": 0.15,
    "concentration": 0.12,
    "fundamental": 0.12,
    "sentiment": 0.12,
    "compliance": 0.12,
    "security": 0.10,
    "macro": 0.12,
}


@dataclass
class RiskResult:
    symbol: str
    total_score: float
    risk_level: str         # 极高 / 高 / 中 / 低 / 极低
    dimensions: dict        # {dim_name: score}
    indicators: dict        # {indicator_name: value}
    risk_details: list[dict] = field(default_factory=list)
    sentiment_summary: str = ""


class RiskEngine:
    """评估引擎 — 纯规则计算，不依赖 LLM"""

    # ── 1. 市场流动性 (15%) ──
    def _score_liquidity(self, data: TokenDataPayload) -> float:
        """成交量/市值比 + 流动性深度"""
        score = 50  # 基准分
        if data.volume_24h_usd and data.market_cap_usd and data.market_cap_usd > 0:
            ratio = data.volume_24h_usd / data.market_cap_usd
            if ratio > 0.3: score += 30   # 高流动性
            elif ratio > 0.1: score += 15
            elif ratio < 0.02: score -= 30
            elif ratio < 0.05: score -= 15
        return max(0, min(100, score))

    # ── 2. 价格波动性 (15%) ──
    def _score_volatility(self, data: TokenDataPayload) -> float:
        """波动率越低越安全"""
        score = 50
        vol = data.volatility_30d or 0
        if vol < 0.3: score += 35       # 低波动
        elif vol < 0.6: score += 15
        elif vol > 1.5: score -= 35     # 极高波动
        elif vol > 1.0: score -= 20
        return max(0, min(100, score))

    # ── 3. 持仓集中度 (12%) ──
    def _score_concentration(self, data: TokenDataPayload) -> float:
        """前10地址持仓越分散越安全"""
        score = 50
        ratio = data.top10_holder_ratio or 0
        if ratio < 0.3: score += 35
        elif ratio < 0.5: score += 15
        elif ratio > 0.9: score -= 40
        elif ratio > 0.7: score -= 20
        return max(0, min(100, score))

    # ── 4. 项目基本面 (12%) ──
    def _score_fundamental(self, data: TokenDataPayload) -> float:
        """开发活跃度 + 团队可信度"""
        score = 50
        commits = data.github_commits_30d or 0
        if commits > 100: score += 30
        elif commits > 30: score += 15
        elif commits == 0: score -= 20
        dev_score = data.developer_score or 0
        score += min(dev_score / 2, 20)  # CoinGecko dev score 归一化
        return max(0, min(100, score))

    # ── 5. 舆情异常 (12%) ──
    def _score_sentiment(self, data: TokenDataPayload) -> float:
        """负面情绪 + 异常提及量"""
        score = 50
        neg_pct = data.negative_sentiment_pct or 0
        if neg_pct > 0.5: score -= 35
        elif neg_pct > 0.3: score -= 20
        elif neg_pct < 0.15: score += 20
        if data.mentions_anomaly: score -= 15
        sent = data.sentiment_score or 50
        score += (sent - 50) * 0.4  # 舆情 AI 评分修正
        return max(0, min(100, score))

    # ── 6. 交易所合规 (12%) ──
    def _score_compliance(self, data: TokenDataPayload) -> float:
        """交易所下架风险"""
        score = 80  # 默认合规
        if data.exchange_delist_warning:
            score -= 50
        # 上架交易所越多越安全
        listings = len(data.exchange_listings)
        if listings > 20: score += 10
        elif listings < 3: score -= 10
        return max(0, min(100, score))

    # ── 7. 智能合约安全 (10%) ──
    def _score_security(self, data: TokenDataPayload) -> float:
        """合约审计状态 + 安全风险"""
        score = 50
        if data.contract_audited: score += 30
        else: score -= 20
        for _ in data.contract_risks:
            score -= 10
        return max(0, min(100, score))

    # ── 8. 宏观关联 (12%) ──
    def _score_macro(self, data: TokenDataPayload) -> float:
        """BTC 相关性异常 + 解锁事件"""
        score = 60
        if data.unlock_event_30d:
            amount = data.unlock_amount_usd or 0
            if amount > 10_000_000: score -= 30
            elif amount > 1_000_000: score -= 15
        return max(0, min(100, score))

    # ── 综合评估 ──
    def evaluate(self, data: TokenDataPayload) -> RiskResult:
        dimensions = {
            "liquidity": round(self._score_liquidity(data), 1),
            "volatility": round(self._score_volatility(data), 1),
            "concentration": round(self._score_concentration(data), 1),
            "fundamental": round(self._score_fundamental(data), 1),
            "sentiment": round(self._score_sentiment(data), 1),
            "compliance": round(self._score_compliance(data), 1),
            "security": round(self._score_security(data), 1),
            "macro": round(self._score_macro(data), 1),
        }

        total = sum(dimensions[k] * WEIGHTS[k] for k in WEIGHTS)
        total = round(total, 1)

        # 风险等级判定
        if total >= 80: level = "极低"
        elif total >= 65: level = "低"
        elif total >= 45: level = "中"
        elif total >= 25: level = "高"
        else: level = "极高"

        # 风险明细
        risk_details = self._build_risk_details(data, dimensions)

        return RiskResult(
            symbol=data.symbol,
            total_score=total,
            risk_level=level,
            dimensions=dimensions,
            indicators=self._build_indicators(data),
            risk_details=risk_details,
            sentiment_summary=data.sentiment_summary or "",
        )

    def _build_indicators(self, data: TokenDataPayload) -> dict:
        return {
            "volume_mcap_ratio": (
                round(data.volume_24h_usd / data.market_cap_usd, 4)
                if data.volume_24h_usd and data.market_cap_usd else None
            ),
            "liquidity_depth": None,  # 需 CMC depth API
            "vol_7d_exceeded": (data.volatility_30d or 0) > 1.0,
            "top10_holder_ratio": data.top10_holder_ratio,
            "github_commits_30d": data.github_commits_30d,
            "team_verified": False,  # 需额外数据源
            "negative_sentiment_pct": data.negative_sentiment_pct,
            "mentions_anomaly_7d": data.mentions_anomaly,
            "exchange_delist_warning": data.exchange_delist_warning,
            "contract_audited": data.contract_audited,
            "unlock_event_30d": data.unlock_event_30d,
            "btc_beta_anomaly": False,  # 需计算 BTC Beta
        }

    def _build_risk_details(self, data: TokenDataPayload, dimensions: dict) -> list[dict]:
        """根据各维度得分生成风险明细"""
        details = []

        # 舆情异常
        if dimensions["sentiment"] < 40:
            details.append({
                "category": "舆情异常",
                "severity": "high" if dimensions["sentiment"] < 25 else "medium",
                "description": f"负面情绪占比高 ({data.negative_sentiment_pct:.0%})" if data.negative_sentiment_pct else "舆情评分偏低",
                "source": data.sentiment_summary or "",
            })

        # 友商下架
        if data.exchange_delist_warning:
            details.append({
                "category": "友商下架",
                "severity": "high",
                "description": f"交易所下架/风险提示: {', '.join(data.delist_sources)}",
                "source": "",
            })

        # 合约风险
        if data.contract_risks:
            for risk in data.contract_risks:
                details.append({
                    "category": "合约安全",
                    "severity": "high",
                    "description": risk,
                    "source": "",
                })

        # 代币解锁
        if data.unlock_event_30d:
            amount_str = f"${data.unlock_amount_usd:,.0f}" if data.unlock_amount_usd else "未知"
            details.append({
                "category": "代币解锁",
                "severity": "medium" if (data.unlock_amount_usd or 0) < 5_000_000 else "high",
                "description": f"30d 内解锁 {amount_str}",
                "source": "",
            })

        return details
