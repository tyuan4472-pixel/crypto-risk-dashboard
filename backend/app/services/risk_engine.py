"""风险评估引擎 — 8 维度评分 + 12 项检查指标

评分规则: 每维度 0-100 分
总分 = 加权求和 (分数越高 = 风险越低 = 越安全)

维度权重:
  1. 市场流动性     15%
  2. 价格波动性     15%
  3. 持仓集中度     12%
  4. 项目基本面     12%
  5. 舆情异常       12%
  6. 交易所合规     12%
  7. 智能合约安全   10%
  8. 宏观关联风险   12%

当某数据源缺失时, 该维度给基准分 50 (中性), 不影响总分偏差。
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import math
from typing import Optional

from app.services.data_fetcher import TokenDataPayload


# ═══════════════════════════════════════════
# 常量
# ═══════════════════════════════════════════

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

# 风险等级阈值 (总分)
RISK_THRESHOLDS = [
    (80, "极低"),
    (65, "低"),
    (45, "中"),
    (25, "高"),
    (0, "极高"),
]


@dataclass
class RiskResult:
    """评估结果"""
    symbol: str
    total_score: float
    risk_level: str
    dimensions: dict            # {dim_name: score}
    indicators: dict            # {indicator_name: value}
    risk_details: list[dict] = field(default_factory=list)
    sentiment_summary: str = ""


# ═══════════════════════════════════════════
# 评估引擎
# ═══════════════════════════════════════════

class RiskEngine:
    """纯规则评估引擎 — 不依赖 LLM, 确定性计算"""

    def evaluate(self, data: TokenDataPayload) -> RiskResult:
        """主入口: 输入 TokenDataPayload, 输出 RiskResult"""
        dimensions = {
            "liquidity": self._clamp(self._score_liquidity(data)),
            "volatility": self._clamp(self._score_volatility(data)),
            "concentration": self._clamp(self._score_concentration(data)),
            "fundamental": self._clamp(self._score_fundamental(data)),
            "sentiment": self._clamp(self._score_sentiment(data)),
            "compliance": self._clamp(self._score_compliance(data)),
            "security": self._clamp(self._score_security(data)),
            "macro": self._clamp(self._score_macro(data)),
        }

        # 加权总分
        total = sum(dimensions[k] * WEIGHTS[k] for k in WEIGHTS)
        total = round(total, 1)

        # 风险等级
        risk_level = "极高"
        for threshold, level in RISK_THRESHOLDS:
            if total >= threshold:
                risk_level = level
                break

        # 12 项检查指标
        indicators = self._build_indicators(data)

        # 风险明细
        risk_details = self._build_risk_details(data, dimensions)

        return RiskResult(
            symbol=data.symbol,
            total_score=total,
            risk_level=risk_level,
            dimensions={k: round(v, 1) for k, v in dimensions.items()},
            indicators=indicators,
            risk_details=risk_details,
            sentiment_summary=data.sentiment_summary or "",
        )

    # ── 维度评分函数 ──

    def _score_liquidity(self, data: TokenDataPayload) -> float:
        """
        市场流动性 (15%):
        - 24h 成交量/市值比 (越高越好)
        - 无市值数据时用成交量绝对值判断
        """
        score = 50  # 无数据时给基准分

        if data.volume_24h_usd and data.market_cap_usd and data.market_cap_usd > 0:
            ratio = data.volume_24h_usd / data.market_cap_usd
            if ratio > 0.5:
                score = 90
            elif ratio > 0.2:
                score = 75
            elif ratio > 0.1:
                score = 60
            elif ratio > 0.05:
                score = 45
            elif ratio > 0.01:
                score = 30
            else:
                score = 15

        elif data.volume_24h_usd:
            # 没有市值但有成交量 → 用绝对值
            vol = data.volume_24h_usd
            if vol > 10_000_000:
                score = 70
            elif vol > 1_000_000:
                score = 55
            elif vol > 100_000:
                score = 40
            else:
                score = 25

        return score

    def _score_volatility(self, data: TokenDataPayload) -> float:
        """
        价格波动性 (15%):
        - 24h 涨跌幅 (越稳定越安全)
        - 7d 涨跌幅
        """
        score = 50

        # 用 24h 变化幅度
        change_24h = abs(data.price_change_24h_pct or 0)
        if change_24h < 2:
            score = 85
        elif change_24h < 5:
            score = 70
        elif change_24h < 10:
            score = 55
        elif change_24h < 20:
            score = 35
        elif change_24h < 50:
            score = 20
        else:
            score = 10

        # 7d 变化修正
        change_7d = abs(data.price_change_7d_pct or 0)
        if change_7d > 50:
            score -= 15
        elif change_7d > 30:
            score -= 10
        elif change_7d < 5:
            score += 5

        return score

    def _score_concentration(self, data: TokenDataPayload) -> float:
        """
        持仓集中度 (12%):
        - 前10地址持仓占比 (越分散越安全)
        - 无数据时给基准分
        """
        ratio = data.top10_holder_ratio
        if ratio is None:
            return 50  # 无数据, 中性

        if ratio < 0.2:
            return 90  # 非常分散
        elif ratio < 0.35:
            return 75
        elif ratio < 0.5:
            return 55
        elif ratio < 0.7:
            return 35
        elif ratio < 0.9:
            return 20
        else:
            return 10  # 极度集中

    def _score_fundamental(self, data: TokenDataPayload) -> float:
        """
        项目基本面 (12%):
        - GitHub 活跃度 (30d commits)
        - 开发者评分 (CoinGecko)
        - 无数据时给基准分
        """
        score = 50

        commits = data.github_commits_30d
        if commits is not None:
            if commits > 100:
                score = 85
            elif commits > 50:
                score = 70
            elif commits > 20:
                score = 55
            elif commits > 5:
                score = 40
            elif commits == 0:
                score = 25

        # CoinGecko 开发者评分修正
        dev_score = data.developer_score
        if dev_score is not None:
            score = score * 0.7 + (dev_score / 100 * 100) * 0.3

        return score

    def _score_sentiment(self, data: TokenDataPayload) -> float:
        """
        舆情异常 (12%):
        - 负面情绪占比
        - AI 情绪分数
        - 异常提及检测
        - 无舆情数据时给基准分 (Phase 2 接入后生效)
        """
        score = 50

        if data.sentiment_score is not None:
            # AI 情绪分 (0-100, 越高越正面)
            score = data.sentiment_score

        neg_pct = data.negative_sentiment_pct
        if neg_pct is not None:
            if neg_pct > 0.6:
                score -= 30
            elif neg_pct > 0.4:
                score -= 20
            elif neg_pct > 0.25:
                score -= 10
            elif neg_pct < 0.1:
                score += 10

        if data.mentions_anomaly:
            score -= 15

        return score

    def _score_compliance(self, data: TokenDataPayload) -> float:
        """
        交易所合规 (12%):
        - 下架/风险提示
        - 上架交易所数量
        """
        score = 70  # 默认还行

        if data.exchange_delist_warning:
            score -= 40

        listings = len(data.exchange_listings)
        if listings > 30:
            score += 15
        elif listings > 15:
            score += 10
        elif listings < 3 and listings > 0:
            score -= 10

        return score

    def _score_security(self, data: TokenDataPayload) -> float:
        """
        智能合约安全 (10%):
        - 合约审计状态
        - 已知风险 (蜜罐、代理合约等)
        """
        score = 50

        if data.contract_audited is True:
            score += 30
        elif data.contract_audited is False:
            score -= 15

        # 每发现一个风险扣分
        risk_count = len(data.contract_risks)
        score -= risk_count * 12

        return score

    def _score_macro(self, data: TokenDataPayload) -> float:
        """
        宏观关联 (12%):
        - 代币解锁事件
        - 解锁金额
        """
        score = 65  # 默认偏安全

        if data.unlock_event_30d:
            amount = data.unlock_amount_usd or 0
            if amount > 50_000_000:
                score -= 40
            elif amount > 10_000_000:
                score -= 25
            elif amount > 1_000_000:
                score -= 15
            else:
                score -= 8

        return score

    # ── 12 项检查指标 ──

    def _build_indicators(self, data: TokenDataPayload) -> dict:
        vol_mcap_ratio = None
        if data.volume_24h_usd and data.market_cap_usd and data.market_cap_usd > 0:
            vol_mcap_ratio = round(data.volume_24h_usd / data.market_cap_usd, 4)

        return {
            "volume_mcap_ratio": vol_mcap_ratio,
            "liquidity_depth": None,  # 需要订单簿深度数据 (Phase 2)
            "vol_7d_exceeded": abs(data.price_change_7d_pct or 0) > 30,
            "top10_holder_ratio": data.top10_holder_ratio,
            "github_commits_30d": data.github_commits_30d,
            "team_verified": False,  # 需额外数据源 (Phase 2)
            "negative_sentiment_pct": data.negative_sentiment_pct,
            "mentions_anomaly_7d": data.mentions_anomaly,
            "exchange_delist_warning": data.exchange_delist_warning,
            "contract_audited": data.contract_audited,
            "unlock_event_30d": data.unlock_event_30d,
            "btc_beta_anomaly": False,  # 需 BTC 相关性计算 (Phase 2)
        }

    # ── 风险明细生成 ──

    def _build_risk_details(self, data: TokenDataPayload, dimensions: dict) -> list[dict]:
        details = []

        # 流动性极低
        if dimensions["liquidity"] < 30:
            details.append({
                "category": "流动性不足",
                "severity": "high",
                "description": f"24h 成交量 ${data.volume_24h_usd:,.0f}" if data.volume_24h_usd else "流动性数据缺失",
                "source": "KuCoin ticker",
            })

        # 波动率异常
        if dimensions["volatility"] < 30:
            details.append({
                "category": "价格剧烈波动",
                "severity": "high",
                "description": f"24h 变化 {data.price_change_24h_pct:.1f}%" if data.price_change_24h_pct else "波动率极高",
                "source": "KuCoin ticker",
            })

        # 舆情异常
        if dimensions["sentiment"] < 35:
            desc = f"负面情绪占比 {data.negative_sentiment_pct:.0%}" if data.negative_sentiment_pct else "舆情评分偏低"
            details.append({
                "category": "舆情异常",
                "severity": "high" if dimensions["sentiment"] < 20 else "medium",
                "description": desc,
                "source": data.sentiment_summary[:100] if data.sentiment_summary else "",
            })

        # 友商下架
        if data.exchange_delist_warning:
            details.append({
                "category": "友商下架/风险提示",
                "severity": "high",
                "description": f"相关交易所: {', '.join(data.delist_sources)}" if data.delist_sources else "存在下架风险",
                "source": "",
            })

        # 合约风险
        for risk in data.contract_risks:
            details.append({
                "category": "合约安全",
                "severity": "high",
                "description": risk,
                "source": "GoPlus Security",
            })

        # 持仓集中
        if data.top10_holder_ratio and data.top10_holder_ratio > 0.7:
            details.append({
                "category": "持仓高度集中",
                "severity": "medium",
                "description": f"前10地址持仓 {data.top10_holder_ratio:.0%}",
                "source": "On-chain data",
            })

        # 代币解锁
        if data.unlock_event_30d:
            amount_str = f"${data.unlock_amount_usd:,.0f}" if data.unlock_amount_usd else "未知数额"
            details.append({
                "category": "代币解锁",
                "severity": "medium" if (data.unlock_amount_usd or 0) < 10_000_000 else "high",
                "description": f"30天内解锁 {amount_str}",
                "source": "Token unlock calendar",
            })

        return details

    # ── 工具函数 ──

    @staticmethod
    def _clamp(value: float, min_val: float = 0, max_val: float = 100) -> float:
        """将分数限制在 [0, 100] 范围"""
        return max(min_val, min(max_val, value))
