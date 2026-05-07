"""评估执行器 — 数据获取 → 规则评分 → 模型增强 → 结果存储"""

import asyncio
import sys
import os

# 把 backend 代码加入 path, 复用 services 层
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.services.data_fetcher import DataFetcher, TokenDataPayload
from app.services.risk_engine import RiskEngine, RiskResult
from app.services.model_router import model_router, TaskType


class Evaluator:
    """单个币种的完整评估流程"""

    def __init__(self):
        self.fetcher = DataFetcher()
        self.engine = RiskEngine()

    async def get_token_list(self) -> list[str]:
        """从 KuCoin 获取需要评估的币种列表"""
        return await self.fetcher.get_token_list()

    async def evaluate_single(self, symbol: str) -> RiskResult:
        """评估单个币种: 获取数据 → 规则打分 → (可选)AI 增强"""
        data = await self.fetcher.fetch_token_data(symbol)
        result = self.engine.evaluate(data)
        return result

    async def evaluate_batch(self, symbols: list[str]) -> list[RiskResult]:
        """并发评估一批币种"""
        tasks = [self.evaluate_single(s) for s in symbols]
        return await asyncio.gather(*tasks, return_exceptions=False)

    async def save_results(self, results: list[RiskResult]):
        """将评估结果写入 PostgreSQL"""
        # TODO: 实际数据库写入 — SQLAlchemy bulk insert
        for r in results:
            print(f"  [{r.symbol}] score={r.total_score} level={r.risk_level}")

    async def generate_report(self, symbol: str, result: RiskResult) -> str:
        """对高风险币种生成 AI 深度调研报告"""
        if result.risk_level in ("极高", "高"):
            prompt = f"""为加密货币 {symbol} 生成一份风险调研报告。
当前评分: {result.total_score}/100, 风险等级: {result.risk_level}
各维度得分: {result.dimensions}
风险明细: {result.risk_details}

请输出中文报告，包含:
1. 项目概述
2. 各维度风险分析
3. 近期重大事件
4. 综合建议"""
            model_result = await model_router.call(TaskType.DEEP_REPORT, prompt, max_tokens=4096)
            return model_result.content
        return ""
