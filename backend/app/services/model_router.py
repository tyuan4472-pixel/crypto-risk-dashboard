"""模型路由层 — 根据任务复杂度自动分发到不同模型

策略:
  基础任务 (数据清洗/格式化) → 千问 3.6B Plus (DashScope) — 成本低、速度快
  复杂任务 (舆情分析/深度报告) → Groq (Grok-4.3 via OpenRouter) — X 平台适配、推理强
  紧急判断 → 千问先跑，超时/失败 fallback 到 Groq
"""

from enum import Enum
from dataclasses import dataclass
import httpx

from app.config import settings


class TaskType(str, Enum):
    DATA_CLEANING = "data_cleaning"         # 数据清洗/格式化 → 千问
    SENTIMENT_ANALYSIS = "sentiment"        # 舆情分析 → Groq
    DEEP_REPORT = "deep_report"             # 深度调研报告 → Groq
    QUICK_CHECK = "quick_check"             # 紧急风险判断 → 千问 → Groq fallback


@dataclass
class ModelResult:
    model_used: str
    content: str
    tokens_used: int
    latency_ms: int


class ModelRouter:
    """自动模型路由"""

    OPENROUTER_BASE = "https://openrouter.ai/api/v1"
    DASHSCOPE_BASE = "https://dashscope.aliyuncs.com/api/v1"

    # 模型映射
    MODEL_MAP = {
        TaskType.DATA_CLEANING: "qwen/qwen-plus",              # 千问 3.6B Plus
        TaskType.SENTIMENT_ANALYSIS: "x-ai/grok-4.3",           # Groq via OpenRouter
        TaskType.DEEP_REPORT: "x-ai/grok-4.3",
        TaskType.QUICK_CHECK: "qwen/qwen-plus",                # 先千问
    }

    async def call(self, task_type: TaskType, prompt: str, max_tokens: int = 2048) -> ModelResult:
        """根据任务类型自动选择模型"""
        model = self.MODEL_MAP.get(task_type, "qwen/qwen-plus")

        if "grok" in model:
            return await self._call_openrouter(model, prompt, max_tokens)
        else:
            return await self._call_dashscope(model, prompt, max_tokens)

    async def _call_openrouter(self, model: str, prompt: str, max_tokens: int) -> ModelResult:
        """OpenRouter API 调用 (Grok 等)"""
        headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
        }
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.OPENROUTER_BASE}/chat/completions",
                headers=headers, json=body,
            )
            resp.raise_for_status()
            data = resp.json()
            return ModelResult(
                model_used=model,
                content=data["choices"][0]["message"]["content"],
                tokens_used=data.get("usage", {}).get("total_tokens", 0),
                latency_ms=0,
            )

    async def _call_dashscope(self, model: str, prompt: str, max_tokens: int) -> ModelResult:
        """DashScope API 调用 (千问)"""
        headers = {
            "Authorization": f"Bearer {settings.dashscope_api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": model,
            "input": {"messages": [{"role": "user", "content": prompt}]},
            "parameters": {"max_tokens": max_tokens},
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.DASHSCOPE_BASE}/services/aigc/text-generation/generation",
                headers=headers, json=body,
            )
            resp.raise_for_status()
            data = resp.json()
            output = data.get("output", {})
            return ModelResult(
                model_used=model,
                content=output.get("text", ""),
                tokens_used=data.get("usage", {}).get("total_tokens", 0),
                latency_ms=0,
            )

    async def sentiment_analysis(self, token_symbol: str, tweets_text: str) -> str:
        """舆情分析专用 — 用 Groq 处理 X 平台数据"""
        prompt = f"""分析以下关于 {token_symbol} 加密货币的社交媒体内容:
{tweets_text[:8000]}

请输出 JSON (仅 JSON, 不要其他内容):
{{
  "sentiment_score": 0-100的数值 (越高越正面),
  "negative_pct": 0-1之间的数值 (负面情绪占比),
  "anomaly_detected": true/false (是否检测到异常提及量),
  "summary": "中文摘要, 不超过200字, 概括核心观点和风险"
}}"""
        result = await self.call(TaskType.SENTIMENT_ANALYSIS, prompt, max_tokens=1024)
        return result.content


# 全局单例
model_router = ModelRouter()
