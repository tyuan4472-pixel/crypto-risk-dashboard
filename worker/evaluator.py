"""评估执行器 — 数据获取 → 规则评分 → DB 持久化"""

import asyncio
import logging
import sys
import os

backend_path = os.path.join(os.path.dirname(__file__), "..", "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.services.data_fetcher import DataFetcher, TokenDataPayload
from app.services.risk_engine import RiskEngine, RiskResult
from db import bulk_insert_scores, save_report

logger = logging.getLogger(__name__)


class Evaluator:
    def __init__(self):
        self.fetcher = DataFetcher()
        self.engine = RiskEngine()

    async def get_token_list(self) -> list[str]:
        symbols_info = await self.fetcher.get_token_list()
        return [s["symbol"] for s in symbols_info]

    async def evaluate_single(self, symbol: str) -> dict:
        try:
            data = await self.fetcher.fetch_token_data(symbol)
            result = self.engine.evaluate(data)
            return self._result_to_dict(result, data)
        except Exception as e:
            logger.error(f"评估 {symbol} 失败: {e}")
            raise

    async def evaluate_batch(self, symbols: list[str]) -> list[dict]:
        payloads = await self.fetcher.fetch_batch(symbols)
        results = []
        for payload in payloads:
            try:
                result = self.engine.evaluate(payload)
                results.append(self._result_to_dict(result, payload))
            except Exception as e:
                logger.error(f"评估 {payload.symbol} 失败: {e}")
                continue
        return results

    def save_results(self, results: list[dict]) -> int:
        if not results:
            return 0
        return bulk_insert_scores(results)

    async def generate_report(self, symbol: str, result: dict) -> str:
        risk_level = result.get("risk_level", "")
        if risk_level not in ("极高", "高"):
            return ""

        report = f"""# {symbol} 风险评估报告

## 基本信息
- 总分: {result['total_score']}/100
- 风险等级: {risk_level}

## 各维度得分
- 市场流动性: {result.get('liquidity_score', 'N/A')}
- 价格波动性: {result.get('volatility_score', 'N/A')}
- 持仓集中度: {result.get('concentration_score', 'N/A')}
- 项目基本面: {result.get('fundamental_score', 'N/A')}
- 舆情异常: {result.get('sentiment_score', 'N/A')}
- 交易所合规: {result.get('compliance_score', 'N/A')}
- 智能合约安全: {result.get('security_score', 'N/A')}
- 宏观关联: {result.get('macro_score', 'N/A')}

## 风险明细
"""
        rd = result.get("risk_details", [])
        items = rd.get("items", rd) if isinstance(rd, dict) else rd
        for detail in (items if isinstance(items, list) else []):
            sev = detail.get('severity', '')
            cat = detail.get('category', '')
            desc = detail.get('description', '')
            report += f"- [{sev}] {cat}: {desc}\n"

        zombie = result.get("risk_details", {}).get("zombie", {}) if isinstance(result.get("risk_details"), dict) else {}
        if zombie:
            report += f"\n## 🧟 僵尸币检测: {zombie.get('score', 0)}/7\n"
            for flag in zombie.get("flags", []):
                report += f"- {flag}\n"

        report += "\n## 建议\n- 密切关注该币种后续动态\n- 建议补充链上合约安全扫描\n"

        save_report(symbol=symbol, report_type="full", title=f"{symbol} 风险评估报告",
                     content=report, trigger_source="auto")
        return report

    def _result_to_dict(self, result: RiskResult, data: TokenDataPayload) -> dict:
        # 把所有扩展数据打包进 risk_details JSONB
        risk_details_payload = {
            "items": result.risk_details,
            "indicators": result.indicators,
            "zombie": {"score": result.zombie_score, "flags": result.zombie_flags},
            "extra": {
                # 原有字段
                "market_cap_rank": data.market_cap_rank,
                "holder_count": data.holder_count,
                "ath_pct": data.ath_pct,
                "circulating_supply": data.circulating_supply,
                "total_supply": data.total_supply,
                "kucoin_deposit_enabled": data.kucoin_deposit_enabled,
                "kucoin_withdraw_enabled": data.kucoin_withdraw_enabled,
                "github_commits_30d": data.github_commits_30d,
                "developer_score": data.developer_score,
                "community_score": data.community_score,
                "top10_holder_ratio": data.top10_holder_ratio,
                # 交叉验证 (CG vs CMC)
                "cross_validation": {
                    "cg_cmc_divergence_pct": data.cg_cmc_divergence_pct,
                },
                # 交易所分布
                "exchange_distribution": {
                    "exchange_count": data.exchange_count,
                    "cex_count": data.cex_count,
                    "major_exchanges": data.major_exchanges,
                    "kucoin_volume_share": data.kucoin_volume_share,
                },
                # KuCoin 订单簿
                "kucoin_market": {
                    "best_bid": data.kucoin_best_bid,
                    "best_ask": data.kucoin_best_ask,
                    "spread_pct": data.kucoin_spread_pct,
                },
                # CryptoRank 融资数据
                "cryptorank_data": {
                    "rank": data.cryptorank_rank,
                    "fundraise_rounds": data.fundraise_rounds,
                    "fundraise_total_usd": data.fundraise_total_usd,
                    "top_vcs": data.top_vcs,
                },
                # 情绪分析 (由 model_router 在运行时填充)
                "sentiment_analysis": {},
            },
        }
        return {
            "symbol": result.symbol,
            "name": data.name or result.symbol,
            "total_score": result.total_score,
            "risk_level": result.risk_level,
            "liquidity_score": result.dimensions.get("liquidity"),
            "volatility_score": result.dimensions.get("volatility"),
            "concentration_score": result.dimensions.get("concentration"),
            "fundamental_score": result.dimensions.get("fundamental"),
            "sentiment_score": result.dimensions.get("sentiment"),
            "compliance_score": result.dimensions.get("compliance"),
            "security_score": result.dimensions.get("security"),
            "macro_score": result.dimensions.get("macro"),
            "market_cap_usd": data.market_cap_usd,
            "volume_24h_usd": data.volume_24h_usd,
            "price_usd": data.price_usd,
            "risk_details": risk_details_payload,
            "sentiment_summary": result.sentiment_summary,
        }
