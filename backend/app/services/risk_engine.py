"""风险评估引擎 — 8 维度评分 + 僵尸币检测

数据源升级后:
  1. 市场流动性 — CoinGecko 市值/成交量
  2. 价格波动性 — CG 24h/7d/30d 涨跌
  3. 持仓集中度 — GoPlus 前10地址占比
  4. 项目基本面 — CG 开发者/社区数据 + GitHub
  5. 舆情异常 — LLM 情绪分析 (Phase 2)
  6. 交易所合规 — KuCoin 充提状态
  7. 智能合约安全 — GoPlus 安全检测
  8. 宏观关联 — CG 流通率/供应量
"""

from dataclasses import dataclass, field
import math
from typing import Optional

from app.services.data_fetcher import TokenDataPayload


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

RISK_THRESHOLDS = [
    (80, "极低"),
    (65, "低"),
    (45, "中"),
    (25, "高"),
    (0, "极高"),
]


@dataclass
class RiskResult:
    symbol: str
    total_score: float
    risk_level: str
    dimensions: dict
    indicators: dict
    risk_details: list[dict] = field(default_factory=list)
    sentiment_summary: str = ""
    zombie_score: int = 0  # 僵尸币检测得分 (0-7)
    zombie_flags: list[str] = field(default_factory=list)


class RiskEngine:

    def evaluate(self, data: TokenDataPayload) -> RiskResult:
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

        total = round(sum(dimensions[k] * WEIGHTS[k] for k in WEIGHTS), 1)

        risk_level = "极高"
        for threshold, level in RISK_THRESHOLDS:
            if total >= threshold:
                risk_level = level
                break

        indicators = self._build_indicators(data)
        risk_details = self._build_risk_details(data, dimensions)
        zombie_score, zombie_flags = self._detect_zombie(data)

        return RiskResult(
            symbol=data.symbol,
            total_score=total,
            risk_level=risk_level,
            dimensions={k: round(v, 1) for k, v in dimensions.items()},
            indicators=indicators,
            risk_details=risk_details,
            sentiment_summary=data.sentiment_summary or "",
            zombie_score=zombie_score,
            zombie_flags=zombie_flags,
        )

    # ═══ 维度评分 ═══

    def _score_liquidity(self, data: TokenDataPayload) -> float:
        """市场流动性 — CG 成交量/市值比 + 绝对成交量"""
        score = 50

        if data.volume_24h_usd and data.market_cap_usd and data.market_cap_usd > 0:
            ratio = data.volume_24h_usd / data.market_cap_usd
            if ratio > 0.5: score = 90
            elif ratio > 0.2: score = 75
            elif ratio > 0.1: score = 60
            elif ratio > 0.05: score = 45
            elif ratio > 0.01: score = 30
            else: score = 15
        elif data.volume_24h_usd:
            vol = data.volume_24h_usd
            if vol > 50_000_000: score = 85
            elif vol > 10_000_000: score = 70
            elif vol > 1_000_000: score = 55
            elif vol > 100_000: score = 40
            elif vol > 10_000: score = 25
            else: score = 10

        # CG liquidity score 修正 (0-100, 越高越好)
        if data.liquidity_score_cg is not None:
            score = score * 0.6 + data.liquidity_score_cg * 0.4

        return score

    def _score_volatility(self, data: TokenDataPayload) -> float:
        """价格波动性 — 多时间窗口"""
        score = 50

        changes = []
        if data.price_change_24h_pct is not None:
            changes.append(("24h", abs(data.price_change_24h_pct)))
        if data.price_change_7d_pct is not None:
            changes.append(("7d", abs(data.price_change_7d_pct)))
        if data.price_change_30d_pct is not None:
            changes.append(("30d", abs(data.price_change_30d_pct)))

        if not changes:
            return 50

        # 取最极端变化作为主评分
        max_change = max(c[1] for c in changes)

        if max_change < 2: score = 85
        elif max_change < 5: score = 70
        elif max_change < 10: score = 55
        elif max_change < 20: score = 35
        elif max_change < 50: score = 20
        else: score = 10

        # ATH 跌幅修正
        if data.ath_pct is not None:
            ath_drop = abs(data.ath_pct)
            if ath_drop > 90: score -= 20
            elif ath_drop > 80: score -= 15
            elif ath_drop > 70: score -= 10

        return score

    def _score_concentration(self, data: TokenDataPayload) -> float:
        """持仓集中度 — GoPlus 前10地址占比"""
        if data.top10_holder_ratio is None:
            return 50

        ratio = data.top10_holder_ratio
        if ratio < 0.2: return 90
        elif ratio < 0.35: return 75
        elif ratio < 0.5: return 55
        elif ratio < 0.7: return 35
        elif ratio < 0.9: return 20
        else: return 10

    def _score_fundamental(self, data: TokenDataPayload) -> float:
        """项目基本面 — CG 开发者/社区 + GitHub"""
        score = 50
        signals = 0

        # GitHub 活跃度
        if data.github_commits_30d is not None:
            signals += 1
            commits = data.github_commits_30d
            if commits > 100: score += 30
            elif commits > 50: score += 20
            elif commits > 20: score += 10
            elif commits > 5: score += 5
            elif commits == 0: score -= 20

        # CG 开发者评分 (normalized 0-100)
        if data.developer_score is not None:
            signals += 1
            dev = data.developer_score
            if dev > 80: score += 25
            elif dev > 60: score += 15
            elif dev > 40: score += 5
            elif dev < 20: score -= 15

        # CG 社区评分
        if data.community_score is not None:
            signals += 1
            comm = data.community_score
            if comm > 60: score += 10
            elif comm < 10: score -= 5

        # 公众关注度
        if data.public_interest_score is not None:
            signals += 1
            if data.public_interest_score > 0.5: score += 10

        # 如果没有任何信号，保持中性 50
        if signals == 0:
            return 50

        return score

    def _score_sentiment(self, data: TokenDataPayload) -> float:
        """舆情异常 — 当前基于已有数据，Phase 2 接入 LLM"""
        score = 50

        if data.sentiment_score is not None:
            score = data.sentiment_score

        neg_pct = data.negative_sentiment_pct
        if neg_pct is not None:
            if neg_pct > 0.6: score -= 30
            elif neg_pct > 0.4: score -= 20
            elif neg_pct > 0.25: score -= 10
            elif neg_pct < 0.1: score += 10

        if data.mentions_anomaly:
            score -= 15

        return score

    def _score_exchange_distribution(self, data: TokenDataPayload) -> float:
        """交易所分布评分 — 基于 CEX 数量与主流交易所覆盖"""
        if data.cex_count is None and data.exchange_count is None:
            return 50  # 无数据，中性

        score = 40

        # CEX 数量
        cex = data.cex_count or 0
        if cex >= 30: score += 45
        elif cex >= 20: score += 35
        elif cex >= 10: score += 25
        elif cex >= 5: score += 15
        elif cex >= 3: score += 5
        elif cex == 0: score -= 20

        # 主流交易所覆盖 (13 家基准)
        major_count = len(data.major_exchanges)
        if major_count >= 8: score += 15
        elif major_count >= 5: score += 10
        elif major_count >= 3: score += 5
        elif major_count == 0: score -= 10

        return score

    def _cross_validate(self, data: TokenDataPayload) -> bool:
        """交叉验证 — 检测 CG vs CMC 数据差异 > 10% (数据操纵信号)"""
        if data.cg_cmc_divergence_pct is None:
            return False
        return data.cg_cmc_divergence_pct > 10.0

    def _score_compliance(self, data: TokenDataPayload) -> float:
        """交易所合规 — KuCoin 充提状态 + 交易所分布 + 下架预警"""
        score = 70

        # KuCoin 充提状态 (最关键)
        if data.kucoin_deposit_enabled is False and data.kucoin_withdraw_enabled is False:
            score -= 40  # 充提全关 ≈ 即将下架
        elif data.kucoin_deposit_enabled is False:
            score -= 20
        elif data.kucoin_withdraw_enabled is False:
            score -= 30

        # 下架预警
        if data.exchange_delist_warning:
            score -= 30

        # 上架所数量 (legacy exchange_listings)
        listings = len(data.exchange_listings)
        if listings > 30: score += 15
        elif listings > 15: score += 10
        elif listings < 3 and listings > 0: score -= 10

        # 交易所分布评分加权整合 (占 compliance 的 30%)
        dist_score = self._score_exchange_distribution(data)
        score = score * 0.7 + dist_score * 0.3

        return score

    def _score_security(self, data: TokenDataPayload) -> float:
        """智能合约安全 — GoPlus 检测结果"""
        score = 50

        # 蜜罐 = 直接 0 分
        if data.is_honeypot:
            return 10

        if data.contract_audited is True:
            score += 25
        elif data.contract_audited is False:
            score -= 10

        # 代理合约风险
        if data.is_proxy:
            score -= 15

        # 每项合约风险扣分 (GoPlus)
        risk_count = len(data.contract_risks)
        score -= risk_count * 10

        return score

    def _score_macro(self, data: TokenDataPayload) -> float:
        """宏观关联 — 流通率 + 解锁风险"""
        score = 65

        # 流通率 (低流通率 = 高解锁风险)
        if data.circulating_supply and data.total_supply and data.total_supply > 0:
            ratio = data.circulating_supply / data.total_supply
            if ratio < 0.2: score -= 30
            elif ratio < 0.4: score -= 20
            elif ratio < 0.6: score -= 10
            elif ratio > 0.9: score += 10

        # 代币解锁事件
        if data.unlock_event_30d:
            amount = data.unlock_amount_usd or 0
            if amount > 50_000_000: score -= 40
            elif amount > 10_000_000: score -= 25
            elif amount > 1_000_000: score -= 15
            else: score -= 8

        # ATH 跌幅暗示宏观表现
        if data.ath_pct is not None and data.ath_pct < -90:
            score -= 15
        elif data.ath_pct is not None and data.ath_pct < -80:
            score -= 10

        return score

    # ═══ 僵尸币检测 ═══

    def _detect_zombie(self, data: TokenDataPayload) -> tuple[int, list[str]]:
        """7 项僵尸币指标"""
        flags = []

        # 1. 市值 < $500K
        if data.market_cap_usd and data.market_cap_usd < 500_000:
            flags.append("市值 < $500K")

        # 2. 24h 成交量 < $10K
        if data.volume_24h_usd and data.volume_24h_usd < 10_000:
            flags.append("24h成交量 < $10K")

        # 3. 成交量/市值比 < 1%
        if data.volume_24h_usd and data.market_cap_usd and data.market_cap_usd > 0:
            if data.volume_24h_usd / data.market_cap_usd < 0.01:
                flags.append("成交量/市值比 < 1%")

        # 4. GitHub 30天无提交
        if data.github_commits_30d is not None and data.github_commits_30d == 0:
            flags.append("GitHub 30天无提交")

        # 5. KuCoin 充值关闭
        if data.kucoin_deposit_enabled is False:
            flags.append("KuCoin 充值关闭")

        # 6. 开发者评分为 0 或 None
        if data.developer_score is None or data.developer_score == 0:
            flags.append("无开发者评分")

        # 7. 社区评分为 0
        if data.community_score is not None and data.community_score == 0:
            flags.append("社区评分为0")

        return len(flags), flags

    # ═══ 12 项检查指标 ═══

    def _build_indicators(self, data: TokenDataPayload) -> dict:
        vol_mcap_ratio = None
        if data.volume_24h_usd and data.market_cap_usd and data.market_cap_usd > 0:
            vol_mcap_ratio = round(data.volume_24h_usd / data.market_cap_usd, 4)

        return {
            "volume_mcap_ratio": vol_mcap_ratio,
            "market_cap_rank": data.market_cap_rank,
            "liquidity_depth": data.liquidity_score_cg,
            "vol_30d_exceeded": (data.price_change_30d_pct or 0) > 30 if data.price_change_30d_pct else False,
            "top10_holder_ratio": data.top10_holder_ratio,
            "holder_count": data.holder_count,
            "github_commits_30d": data.github_commits_30d,
            "developer_score": data.developer_score,
            "community_score": data.community_score,
            "contract_audited": data.contract_audited,
            "is_honeypot": data.is_honeypot,
            "is_proxy": data.is_proxy,
            "unlock_event_30d": data.unlock_event_30d,
            "kucoin_deposit_enabled": data.kucoin_deposit_enabled,
            "kucoin_withdraw_enabled": data.kucoin_withdraw_enabled,
            "zombie_score": None,  # 由 zombie detector 填充
        }

    # ═══ 风险明细生成 ═══

    def _build_risk_details(self, data: TokenDataPayload, dimensions: dict) -> list[dict]:
        details = []

        if dimensions["liquidity"] < 30:
            vol_str = f"${data.volume_24h_usd:,.0f}" if data.volume_24h_usd else "未知"
            details.append({
                "category": "流动性不足",
                "severity": "high",
                "description": f"24h 成交量 {vol_str}",
                "source": "CoinGecko",
            })

        if dimensions["volatility"] < 30:
            change = data.price_change_24h_pct or data.price_change_7d_pct or 0
            details.append({
                "category": "价格剧烈波动",
                "severity": "high",
                "description": f"最大涨跌幅 {abs(change):.1f}%",
                "source": "CoinGecko",
            })

        if data.is_honeypot:
            details.append({
                "category": "合约安全",
                "severity": "critical",
                "description": "蜜罐代币 — 只能买不能卖",
                "source": "GoPlus Security",
            })

        for risk in data.contract_risks:
            details.append({
                "category": "合约安全",
                "severity": "high",
                "description": risk,
                "source": "GoPlus Security",
            })

        if data.kucoin_deposit_enabled is False:
            details.append({
                "category": "KuCoin 风控",
                "severity": "high",
                "description": "充值已关闭 (下架前兆)",
                "source": "KuCoin",
            })

        if data.kucoin_withdraw_enabled is False:
            details.append({
                "category": "KuCoin 风控",
                "severity": "high",
                "description": "提现已关闭",
                "source": "KuCoin",
            })

        if data.top10_holder_ratio and data.top10_holder_ratio > 0.7:
            details.append({
                "category": "持仓高度集中",
                "severity": "medium",
                "description": f"前10地址持仓 {data.top10_holder_ratio:.0%}",
                "source": "GoPlus",
            })

        if data.unlock_event_30d:
            amount = f"${data.unlock_amount_usd:,.0f}" if data.unlock_amount_usd else "未知"
            details.append({
                "category": "代币解锁",
                "severity": "medium" if (data.unlock_amount_usd or 0) < 10_000_000 else "high",
                "description": f"30天内解锁 {amount}",
                "source": "Token Unlocks",
            })

        if data.github_commits_30d == 0 and data.github_commits_30d is not None:
            details.append({
                "category": "项目停滞",
                "severity": "medium",
                "description": "GitHub 30天无代码提交",
                "source": "GitHub",
            })

        if data.ath_pct is not None and data.ath_pct < -90:
            details.append({
                "category": "深度套牢",
                "severity": "medium",
                "description": f"距 ATH 下跌 {abs(data.ath_pct):.0f}%",
                "source": "CoinGecko",
            })

        # ── 交易所分布风险 ──
        if data.cex_count is not None and data.cex_count <= 3:
            details.append({
                "category": "交易所覆盖不足",
                "severity": "high" if data.cex_count <= 1 else "medium",
                "description": f"仅上线 {data.cex_count} 家 CEX，流动性高度依赖单一平台，下架连锁风险大",
                "source": "CoinGecko Tickers",
            })

        if data.cex_count is not None and data.cex_count > 3:
            major_count = len(data.major_exchanges)
            if major_count == 0:
                details.append({
                    "category": "主流交易所缺失",
                    "severity": "medium",
                    "description": f"上线 {data.cex_count} 家 CEX 但无主流交易所 (Binance/Coinbase 等)，信誉背书弱",
                    "source": "CoinGecko Tickers",
                })

        # ── 下架连锁风险 ──
        if (data.kucoin_deposit_enabled is False or data.exchange_delist_warning) and (
            data.cex_count is not None and data.cex_count <= 5
        ):
            details.append({
                "category": "下架连锁风险",
                "severity": "high",
                "description": "KuCoin 已限制充提且上架所数量少，若下架将导致严重流动性危机",
                "source": "KuCoin + CoinGecko Tickers",
            })

        # ── 数据交叉验证异常 ──
        if self._cross_validate(data):
            details.append({
                "category": "数据一致性异常",
                "severity": "medium",
                "description": f"CoinGecko vs CMC 流通量差异 {data.cg_cmc_divergence_pct:.1f}% (>10%)，可能存在数据操纵或双重计算",
                "source": "CG + CMC 交叉验证",
            })

        return details

    @staticmethod
    def _clamp(value: float, min_val: float = 0, max_val: float = 100) -> float:
        return max(min_val, min(max_val, value))
