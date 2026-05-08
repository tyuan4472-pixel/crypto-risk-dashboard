"""模型路由层 — 根据任务复杂度自动分发到不同模型

当前可用:
  Claude (Anthropic 原生 API) — 舆情分析 / 深度报告 / 风险判断
  (DashScope 千问账户欠费, 待充值后启用)

策略:
  所有任务 → Claude (Anthropic 原生)
"""

from enum import Enum
from dataclasses import dataclass
import time
import logging
import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class TaskType(str, Enum):
    DATA_CLEANING = "data_cleaning"
    SENTIMENT_ANALYSIS = "sentiment"
    DEEP_REPORT = "deep_report"
    QUICK_CHECK = "quick_check"


@dataclass
class ModelResult:
    model_used: str
    content: str
    tokens_used: int
    latency_ms: int


class ModelRouter:
    """自动模型路由"""

    ANTHROPIC_BASE = "https://api.anthropic.com/v1"

    # 根据任务复杂度选模型大小
    TASK_MODEL_MAP = {
        TaskType.DATA_CLEANING: "claude-haiku-4-5",       # 轻量任务
        TaskType.SENTIMENT_ANALYSIS: "claude-haiku-4-5",  # 批量舆情分析 → 快速便宜
        TaskType.DEEP_REPORT: "claude-sonnet-4-6",        # 深度报告 → 高质量
        TaskType.QUICK_CHECK: "claude-haiku-4-5",         # 快速判断
    }

    def is_configured(self) -> bool:
        return bool(settings.anthropic_api_key or settings.openrouter_api_key)

    async def call(self, task_type: TaskType, prompt: str, max_tokens: int = 2048) -> ModelResult:
        model = self.TASK_MODEL_MAP.get(task_type, "claude-haiku-4-5")

        # 优先 Anthropic 原生 API
        if settings.anthropic_api_key:
            return await self._call_anthropic(model, prompt, max_tokens)

        # 兜底 OpenRouter
        if settings.openrouter_api_key:
            return await self._call_openrouter(model, prompt, max_tokens)

        raise RuntimeError("未配置 AI 模型 Key (ANTHROPIC_API_KEY 或 OPENROUTER_API_KEY)")

    async def _call_anthropic(self, model: str, prompt: str, max_tokens: int) -> ModelResult:
        """Anthropic 原生 API 调用"""
        headers = {
            "x-api-key": settings.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        body = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        t0 = time.time()
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.ANTHROPIC_BASE}/messages",
                headers=headers, json=body,
            )
            resp.raise_for_status()
            data = resp.json()
            latency = int((time.time() - t0) * 1000)
            return ModelResult(
                model_used=model,
                content=data["content"][0]["text"],
                tokens_used=data.get("usage", {}).get("input_tokens", 0) + data.get("usage", {}).get("output_tokens", 0),
                latency_ms=latency,
            )

    async def _call_openrouter(self, model: str, prompt: str, max_tokens: int) -> ModelResult:
        """OpenRouter API 调用 (兜底)"""
        headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": f"anthropic/{model}",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
        }
        t0 = time.time()
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers, json=body,
            )
            resp.raise_for_status()
            data = resp.json()
            latency = int((time.time() - t0) * 1000)
            return ModelResult(
                model_used=model,
                content=data["choices"][0]["message"]["content"],
                tokens_used=data.get("usage", {}).get("total_tokens", 0),
                latency_ms=latency,
            )

    async def sentiment_analysis(self, token_symbol: str, context: str) -> str:
        """舆情分析 — 基于可用数据评估情绪"""
        prompt = f"""你是一个加密货币风险分析师。以下是关于加密货币 {token_symbol} 的市场数据:

{context[:6000]}

请根据这些数据判断该币种的市场情绪。输出纯 JSON (不要 markdown 代码块):

{{
  "sentiment_score": 0-100 (越高越正面/健康),
  "negative_signals": ["具体负面信号1", "具体负面信号2"],
  "positive_signals": ["具体正面信号1"],
  "anomaly_detected": true/false (是否有数据异常),
  "summary": "中文摘要, 100字以内, 核心判断和风险"
}}"""
        result = await self.call(TaskType.SENTIMENT_ANALYSIS, prompt, max_tokens=800)
        return result.content

    async def sentiment_batch(self, tokens_text: str) -> str:
        """批量情绪分析 — 多币种社区数据 + 价格变化 + 成交量"""
        prompt = f"""你是一个加密货币风险分析师。以下是多个代币的社区和市场数据:

{tokens_text[:8000]}

请对每个代币进行情绪分析。输出纯 JSON (不要 markdown 代码块):
{{
  "tokens": {{
    "SYMBOL": {{
      "positive_pct": 0-100,
      "negative_pct": 0-100,
      "summary": "中文摘要, 30字以内, 核心结论",
      "risks_found": ["风险信号1", "风险信号2"]
    }}
  }}
}}"""
        result = await self.call(TaskType.SENTIMENT_ANALYSIS, prompt, max_tokens=2000)
        return result.content

    async def generate_risk_report(self, symbol: str, token_data: dict) -> str:
        """生成深度风险报告"""
        prompt = f"""你是一个加密货币风控专家。请为以下币种生成结构化风险评估报告。

币种: {symbol}
数据:
{str(token_data)[:8000]}

请按以下格式输出中文报告:

## 综合评级
[风险等级: 极高/高/中/低/极低] — [一句话核心判断]

## 关键风险点
1. [风险1 — 具体描述 + 数据支撑]
2. [风险2]
...

## 市场健康度
- 流动性: [评估 + 数据]
- 开发者活跃度: [评估 + 数据]
- 合约安全: [评估 + 数据]

## 处置建议
1. [短期建议 (24-48h)]
2. [中期建议 (1-2周)]
3. [长期建议]

报告长度: 300-500字"""
        result = await self.call(TaskType.DEEP_REPORT, prompt, max_tokens=2000)
        return result.content


# 全局单例
model_router = ModelRouter()
