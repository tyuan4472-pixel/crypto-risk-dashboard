"""评估执行器 — 数据获取 → 规则评分 (+ LLM增强) → DB 持久化 → LLM深度报告"""

import asyncio
import json
import logging
import sys
import os

backend_path = os.path.join(os.path.dirname(__file__), "..", "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.services.data_fetcher import DataFetcher, TokenDataPayload
from app.services.risk_engine import RiskEngine, RiskResult, WEIGHTS
from app.services.deep_report import generate_deep_report, generate_simple_evaluation
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
        """评估单个币种 — 完整数据管线 + 规则评分"""
        try:
            results = await self.fetcher.fetch_batch([symbol])
            data = results[0]
            result = self.engine.evaluate(data)
            return self._result_to_dict(result, data)
        except Exception as e:
            logger.error(f"评估 {symbol} 失败: {e}")
            raise

    async def evaluate_single_llm(self, symbol: str) -> dict:
        """LLM 增强评估 — 规则评分作为基础, LLM 补充深度分析和报告"""
        try:
            # 1. 数据获取
            results = await self.fetcher.fetch_batch([symbol])
            data = results[0]

            # 2. 规则引擎评分 (作为 baseline)
            rule_result = self.engine.evaluate(data)
            base_dict = self._result_to_dict(rule_result, data)

            # 3. LLM 轻量评估 (补充评分 + 处置建议)
            llm_data = self._build_llm_data_dict(base_dict, data)
            llm_result = await generate_simple_evaluation(symbol, llm_data)
            if llm_result:
                # LLM 增强: 覆盖部分评分 (weighted blend: 70% rules + 30% LLM)
                llm_dims = llm_result.get("dimensions", {})
                if llm_dims:
                    for dim in ("liquidity", "volatility", "concentration", "fundamental",
                                "sentiment", "compliance", "security", "macro"):
                        dim_key = f"{dim}_score"
                        if dim in llm_dims and dim_key in base_dict:
                            base_dict[dim_key] = round(
                                float(base_dict[dim_key] or 50) * 0.7 + float(llm_dims[dim]) * 0.3, 1
                            )

                # 重算总分
                total = round(sum(
                    base_dict.get(f"{k}_score", 50) * WEIGHTS.get(k, 0.125)
                    for k in WEIGHTS
                ), 1)
                base_dict["total_score"] = total

                # 风险等级重算
                risk_level = "极高"
                for threshold, level in [(80, "极低"), (65, "低"), (45, "中"), (25, "高"), (0, "极高")]:
                    if total >= threshold:
                        risk_level = level
                        break
                base_dict["risk_level"] = risk_level

                # LLM 风险详情合并
                llm_risk_details = llm_result.get("risk_details", [])
                if llm_risk_details:
                    existing_details = base_dict.get("risk_details", {}).get("items", []) if isinstance(base_dict.get("risk_details"), dict) else []
                    base_dict["risk_details"] = {
                        "items": existing_details + llm_risk_details,
                        "indicators": base_dict.get("risk_details", {}).get("indicators", {}) if isinstance(base_dict.get("risk_details"), dict) else {},
                        "zombie": base_dict.get("risk_details", {}).get("zombie", {"score": 0, "flags": []}) if isinstance(base_dict.get("risk_details"), dict) else {"score": 0, "flags": []},
                        "llm_analysis": {
                            "summary": llm_result.get("summary", ""),
                            "key_risks": llm_result.get("key_risks", []),
                            "safe_factors": llm_result.get("safe_factors", []),
                            "recommendations": llm_result.get("recommendations", []),
                        },
                        "extra": base_dict.get("risk_details", {}).get("extra", {}) if isinstance(base_dict.get("risk_details"), dict) else {},
                    }
                    # 更新 sentiment summary
                    if llm_result.get("summary"):
                        base_dict["sentiment_summary"] = llm_result["summary"]

            return base_dict
        except Exception as e:
            logger.error(f"LLM 增强评估 {symbol} 失败, 回退规则评分: {e}")
            return await self.evaluate_single(symbol)

    async def evaluate_batch(self, symbols: list[str]) -> list[dict]:
        """批量评估 — 规则引擎, 小批量时尝试 LLM 增强"""
        payloads = await self.fetcher.fetch_batch(symbols)
        use_llm = len(symbols) <= 5  # 小批量用 LLM 增强

        results = []
        for payload in payloads:
            try:
                if use_llm:
                    result = await self.evaluate_single_llm(payload.symbol)
                else:
                    result_engine = self.engine.evaluate(payload)
                    result = self._result_to_dict(result_engine, payload)
                results.append(result)
            except Exception as e:
                logger.error(f"评估 {payload.symbol} 失败: {e}")
                continue
        return results

    def save_results(self, results: list[dict]) -> int:
        if not results:
            return 0
        return bulk_insert_scores(results)

    async def generate_report(self, symbol: str, result: dict) -> str:
        """生成深度风控报告 — LLM 7 章节 + P0-P3 处置建议"""
        risk_level = result.get("risk_level", "")

        # 高风险币种走 LLM 深度报告
        if risk_level in ("极高", "高"):
            report = await generate_deep_report(symbol, result)
            if report:
                save_report(
                    symbol=symbol, report_type="full",
                    title=f"{symbol} 深度风控评估报告",
                    content=report, trigger_source="auto",
                )
                return report

        # 中等风险: 生成简化报告
        if risk_level == "中":
            lines = [
                f"# {symbol} 风险评估报告",
                f"\n## 综合评级",
                f"风险等级: {risk_level} — 总分 {result.get('total_score', 'N/A')}/100",
                f"\n## 各维度得分",
            ]
            for dim, label in [
                ("liquidity_score", "市场流动性"), ("volatility_score", "价格波动性"),
                ("concentration_score", "持仓集中度"), ("fundamental_score", "项目基本面"),
                ("sentiment_score", "舆情异常"), ("compliance_score", "交易所合规"),
                ("security_score", "智能合约安全"), ("macro_score", "宏观关联"),
            ]:
                lines.append(f"- {label}: {result.get(dim, 'N/A')}")
            lines.append(f"\n## 风险明细")
            rd = result.get("risk_details", {})
            items = rd.get("items", rd) if isinstance(rd, dict) else rd
            for detail in (items if isinstance(items, list) else []):
                if isinstance(detail, dict):
                    lines.append(f"- [{detail.get('severity', '')}] {detail.get('category', '')}: {detail.get('description', '')}")
            report = "\n".join(lines)
            save_report(
                symbol=symbol, report_type="full",
                title=f"{symbol} 风险评估报告",
                content=report, trigger_source="auto",
            )
            return report

        return ""

    def _build_llm_data_dict(self, base_dict: dict, data: TokenDataPayload) -> dict:
        """构建传给 LLM 的结构化数据字典"""
        return {
            "symbol": base_dict.get("symbol"),
            "name": base_dict.get("name"),
            "price_usd": base_dict.get("price_usd"),
            "market_cap_usd": base_dict.get("market_cap_usd"),
            "volume_24h_usd": base_dict.get("volume_24h_usd"),
            "risk_level_rules": base_dict.get("risk_level"),
            "total_score_rules": base_dict.get("total_score"),
            "dimensions_rules": {
                "liquidity": base_dict.get("liquidity_score"),
                "volatility": base_dict.get("volatility_score"),
                "concentration": base_dict.get("concentration_score"),
                "fundamental": base_dict.get("fundamental_score"),
                "sentiment": base_dict.get("sentiment_score"),
                "compliance": base_dict.get("compliance_score"),
                "security": base_dict.get("security_score"),
                "macro": base_dict.get("macro_score"),
            },
            "market_cap_rank": data.market_cap_rank,
            "ath_pct": data.ath_pct,
            "circulating_supply": data.circulating_supply,
            "total_supply": data.total_supply,
            "circulation_ratio": round(data.circulating_supply / data.total_supply, 4) if data.circulating_supply and data.total_supply else None,
            "kucoin_deposit_enabled": data.kucoin_deposit_enabled,
            "kucoin_withdraw_enabled": data.kucoin_withdraw_enabled,
            "github_commits_30d": data.github_commits_30d,
            "developer_score": data.developer_score,
            "community_score": data.community_score,
            "top10_holder_ratio": data.top10_holder_ratio,
            "holder_count": data.holder_count,
            "contract_audited": data.contract_audited,
            "is_honeypot": data.is_honeypot,
            "is_proxy": data.is_proxy,
            "contract_risks": data.contract_risks,
            "cex_count": data.cex_count,
            "exchange_count": data.exchange_count,
            "major_exchanges": data.major_exchanges,
            "kucoin_volume_share": data.kucoin_volume_share,
            "cg_cmc_divergence_pct": data.cg_cmc_divergence_pct,
            "kucoin_best_bid": data.kucoin_best_bid,
            "kucoin_best_ask": data.kucoin_best_ask,
            "kucoin_spread_pct": data.kucoin_spread_pct,
            "cryptorank_rank": data.cryptorank_rank,
            "fundraise_rounds": data.fundraise_rounds,
            "fundraise_total_usd": data.fundraise_total_usd,
            "top_vcs": data.top_vcs,
        }

    def _result_to_dict(self, result: RiskResult, data: TokenDataPayload) -> dict:
        """把 RiskResult + TokenDataPayload 转成字典"""
        risk_details_payload = {
            "items": result.risk_details,
            "indicators": result.indicators,
            "zombie": {"score": result.zombie_score, "flags": result.zombie_flags},
            "extra": {
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
                "cross_validation": {
                    "cg_cmc_divergence_pct": data.cg_cmc_divergence_pct,
                },
                "exchange_distribution": {
                    "exchange_count": data.exchange_count,
                    "cex_count": data.cex_count,
                    "major_exchanges": data.major_exchanges,
                    "kucoin_volume_share": data.kucoin_volume_share,
                },
                "kucoin_market": {
                    "best_bid": data.kucoin_best_bid,
                    "best_ask": data.kucoin_best_ask,
                    "spread_pct": data.kucoin_spread_pct,
                },
                "cryptorank_data": {
                    "rank": data.cryptorank_rank,
                    "fundraise_rounds": data.fundraise_rounds,
                    "fundraise_total_usd": data.fundraise_total_usd,
                    "top_vcs": data.top_vcs,
                },
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
