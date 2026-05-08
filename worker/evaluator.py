"""评估执行器 — 数据获取 → 规则评分 → DB 持久化

流程:
  1. KuCoin API 获取币种列表 + 行情
  2. (可选) CMC 获取市值/成交量
  3. RiskEngine 规则打分 (8维度)
  4. 结果写入 PostgreSQL
  5. (Phase 2) AI 增强: 舆情分析, 深度报告
"""

import asyncio
import logging
import sys
import os
from dataclasses import asdict

# PYTHONPATH 已在 Dockerfile 中设置为 /app/backend
# 本地开发时手动加入:
backend_path = os.path.join(os.path.dirname(__file__), "..", "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.services.data_fetcher import DataFetcher, TokenDataPayload
from app.services.risk_engine import RiskEngine, RiskResult
from db import bulk_insert_scores, save_report

logger = logging.getLogger(__name__)


class Evaluator:
    """单个币种的完整评估流程"""

    def __init__(self):
        self.fetcher = DataFetcher()
        self.engine = RiskEngine()

    async def get_token_list(self) -> list[str]:
        """从 KuCoin 获取需要评估的币种列表 (symbol names)"""
        symbols_info = await self.fetcher.get_token_list()
        return [s["symbol"] for s in symbols_info]

    async def evaluate_single(self, symbol: str) -> dict:
        """
        评估单个币种: 获取数据 → 规则打分 → 返回结果 dict。
        """
        try:
            data = await self.fetcher.fetch_token_data(symbol)
            result = self.engine.evaluate(data)
            return self._result_to_dict(result, data)
        except Exception as e:
            logger.error(f"评估 {symbol} 失败: {e}")
            raise

    async def evaluate_batch(self, symbols: list[str]) -> list[dict]:
        """
        批量评估: 先批量拉数据, 再逐个打分。
        优化: 共享 KuCoin ticker 数据, CMC 批量查询。
        """
        # 批量获取数据
        payloads = await self.fetcher.fetch_batch(symbols)

        # 逐个评分
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
        """将评估结果批量写入 PostgreSQL"""
        if not results:
            return 0
        return bulk_insert_scores(results)

    async def generate_report(self, symbol: str, result: dict) -> str:
        """
        对高风险币种生成 AI 深度调研报告 (Phase 2)。
        需要 OPENROUTER_API_KEY 或 DASHSCOPE_API_KEY。

        ⚠️ 占位: 当前返回结构化文本摘要, AI 报告生成待 Key 接入后启用。
        """
        risk_level = result.get("risk_level", "")
        if risk_level not in ("极高", "高"):
            return ""

        # Phase 2: 替换为 AI 模型生成
        # from app.services.model_router import model_router, TaskType
        # prompt = f"""..."""
        # model_result = await model_router.call(TaskType.DEEP_REPORT, prompt)
        # return model_result.content

        # 当前: 生成结构化摘要
        report = f"""# {symbol} 风险评估报告

## 基本信息
- 总分: {result['total_score']}/100
- 风险等级: {risk_level}
- 评估时间: {result.get('evaluated_at', 'N/A')}

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
        for detail in result.get("risk_details", []):
            report += f"- [{detail.get('severity', '')}] {detail.get('category', '')}: {detail.get('description', '')}\n"

        if not result.get("risk_details"):
            report += "- 暂无具体风险明细\n"

        report += "\n## 建议\n- 建议密切关注该币种后续动态\n- 如有链上合约地址，建议补充 GoPlus 安全扫描\n"

        # 存储报告
        save_report(
            symbol=symbol,
            report_type="full",
            title=f"{symbol} 风险评估报告",
            content=report,
            trigger_source="auto",
        )

        return report

    def _result_to_dict(self, result: RiskResult, data: TokenDataPayload) -> dict:
        """将 RiskResult 转换为数据库写入格式"""
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
            "risk_details": result.risk_details,
            "sentiment_summary": result.sentiment_summary,
        }
