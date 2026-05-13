"""深度风控报告生成器 — 基于 LLM 生成结构化风险评估报告

报告模板: 6 章 + P0-P3 处置建议
  1. 项目基本面与背景
  2. KuCoin 站内风控检测 (多链)
  3. 近期 CEX 下架时间轴
  4. CEX 分布与独占风险 (Tier 1/2/3)
  5. 链上流通量超发验证
  6. 舆情与存活度 (🧟 僵尸币 7 项检测)
  💡 综合结论与处置建议 (P0-P3)
"""

import json
import logging
from typing import Optional, Any

from app.services.model_router import model_router, TaskType

logger = logging.getLogger(__name__)


def build_deep_report_prompt(symbol: str, token_data: dict) -> str:
    """按模板格式构建 LLM prompt"""

    data = json.dumps(token_data, ensure_ascii=False, indent=2, default=str)

    return f"""你是一个顶级交易所 (KuCoin) 的加密货币风控分析师。请为代币 {symbol} 生成一份结构化的风险评估报告。

可用数据:
{data[:12000]}

请严格按照以下 7 个章节生成报告。每章必须有数据支撑，数据缺失时标注「数据不可用」而非猜测。

---

🚨 {symbol} — 风险评估报告

1. 项目基本面与背景
- 简介: [一句话描述]
- 市值: [市值 + CG/CMC 排名]
- 价格: [当前价格]
- 流通量: [流通量 / 总供应 / 最大供应 + 流通率%]
- 未解锁压力: [未解锁比例 + 解锁价值/市值比 + ⚠️轻重判断]
- 价格表现: 24h / 7d / 30d / 1y 涨跌幅
- ATH: [ATH 价格 + 日期 + 当前距ATH跌幅]
- GitHub: [Stars + Forks + 4周提交数 + ⚠️活跃度判断]

2. KuCoin 站内风控检测 (多链)
逐链列出 现货/合约/杠杆/充值/提现 状态。重点标出 🔴 提现关闭 或 ⚠️ 部分限制 的链。
- 24h 成交量 (KuCoin 站内)
- Top10 买盘深度 / 卖盘深度
- 关键风险信号: [逐条列出, 如流动性枯竭/单边抛压/价差异常]

3. 近期 CEX 下架时间轴 (90天)
逐交易所列出 (KuCoin / Gate.io / MEXC / Bitget / Bybit / Binance / OKX):
  交易状态 / 充值 / 提现 / 24h成交 / 状态
判断: [是否有下架前兆信号, 例如提现关闭/交易量归零/其他所已下架]

4. CEX 分布与独占风险
- 一级所 (Binance/OKX/Bybit/Coinbase/Kraken) 上线情况
- 二级所 (Gate.io/HTX/MEXC/Bitget/Crypto.com) 上线情况
- 三级所 (Upbit/Bithumb/Bitmart) 上线情况
- 独占性判定: [独占/类独占/广泛上线 — 加理由]

5. 链上流通量超发验证
- 多链供应量分析 (逐链 totalSupply + 说明)
- CEX 持仓分析 (逐所逐链持币量 + 占流通量%)
- Top Holders (前5地址 + 持仓量 + 占比 + 标签)
- DEX 流动性 (逐DEX + 链 + 流动性USD + 24h成交量)
- 超发计算: Ratio = (CEX持仓 + DEX流动性) / 流通量
- 判定: 🟢正常 / 🟡可疑 / 🔴超发  + 理由

6. 舆情与存活度
🧟 僵尸币判定 (≥3 项触发):
  ① 市值 < $500K? [值 + ✅/❌]
  ② KuCoin 24h成交量 < $10K? [值 + ✅/❌]
  ③ Top10 深度 < $500? [值 + ✅/❌]
  ④ GitHub 4周提交 = 0? [值 + ✅/❌]
  ⑤ 官方X >30天无代币更新? [✅/❌]
  ⑥ 价格 vs ATH 跌幅 >95%? [值 + ✅/❌]
  ⑦ 开发者评分 = 0 或 None? [值 + ✅/❌]
判定: [触发X/7项 → 结论]

舆情扫描: 官方X/项目网站/负面舆情/下架公告/历史新闻 逐项结果
舆情结论: [一句话总结]

---

💡 综合结论与处置建议

风险等级: 🟢 低 / 🟡 中 / 🟠 高 / 🔴 极高

核心风险因子:
[按严重程度递减列出, 每条 1 句话 + 数据支撑]

非风险因子:
[列出已排除的担忧点]

处置建议:
P0: [立即行动建议 + 理由]
P1: [24-48h 行动建议 + 理由]
P2: [1-2周行动建议 + 理由]
P3: [长期监控建议 + 理由]

---

⚠️ 重要: 每章必须包含具体数据 (价格/百分比/数量), 不能空洞。数据缺失的字段标注「数据不可用」。
输出纯文本报告, 不要 markdown 代码块。"""


async def generate_deep_report(symbol: str, token_data: dict) -> Optional[str]:
    """调用 LLM 生成深度风控报告

    Args:
        symbol: 币种符号
        token_data: TokenDetail 格式的 JSON 数据 (包含所有维度)

    Returns:
        格式化的中文报告文本, 失败返回 None
    """
    if not model_router.is_configured():
        logger.warning("未配置 AI Key，无法生成深度报告")
        return None

    prompt = build_deep_report_prompt(symbol, token_data)

    try:
        result = await model_router.call(
            TaskType.DEEP_REPORT,
            prompt,
            max_tokens=4096,
        )
        logger.info(f"深度报告 {symbol}: {result.model_used} {result.tokens_used} tokens {result.latency_ms}ms")
        return result.content
    except Exception as e:
        logger.error(f"深度报告生成失败 {symbol}: {e}")
        return None


def build_simple_evaluation_prompt(symbol: str, token_data: dict) -> str:
    """轻量评估 prompt — 用于批量快速评分 (替代纯规则引擎)

    返回 JSON: {{total_score, risk_level, dimensions, risk_details, zombie, recommendations}}
    """
    data = json.dumps(token_data, ensure_ascii=False, indent=2, default=str)

    return f"""你是加密货币风控分析系统。请根据以下数据评估代币 {symbol} 的风险。

数据:
{data[:8000]}

输出纯 JSON (不要 markdown 代码块):

{{
  "total_score": 0-100 风险分 (越高越危险, 85+极高, 65-85高, 35-65中, 15-35低, 0-15极低),
  "risk_level": "极高/高/中/低/极低",
  "summary": "中文一句话结论,30字",
  "dimensions": {{
    "liquidity": 0-100 (越低越危险, 基于成交量/市值比和深度),
    "volatility": 0-100 (越低越危险, 基于多周期价格波动率),
    "concentration": 0-100 (越低越危险, 基于top10持仓占比),
    "fundamental": 0-100 (越低越危险, 基于开发者活跃度和社区参与),
    "sentiment": 0-100 (越低越危险, 基于舆论情绪),
    "compliance": 0-100 (越低越危险, 基于充提状态和交易所分布),
    "security": 0-100 (越低越危险, 基于合约审计和风险项),
    "macro": 0-100 (越低越危险, 基于流通率和ATH跌幅)
  }},
  "risk_details": [
    {{"category": "...", "severity": "critical/high/medium/low", "description": "...", "source": "..."}}
  ],
  "zombie_flags": ["标记1", "标记2"],
  "zombie_score": 0-7,
  "key_risks": ["核心风险1", "核心风险2"],
  "safe_factors": ["排除的担忧1"],
  "recommendations": [
    {{"priority": "P0/P1/P2/P3", "action": "建议", "reason": "理由"}}
  ]
}}

评估规则:
1. 流动性: 24h成交量<$10K → 90分; <$100K → 70分; >$10M → 15分
2. 波动性: 30d涨跌>50% → 85分; <5% → 20分; ATH跌幅>95% → +20
3. 集中度: top10>70% → 85分; <20% → 15分
4. 基本面: GitHub 30d=0 → 70分; 开发者分<20 → 60分
5. 合规: 提现关闭 → +30; 充值关闭 → +20
6. 安全: 蜜罐 → 100分; 代理合约 → +15
7. 如果KuCoin是唯一上线CEX → 独占风险 +25
8. 成交量/市值比 < 1% → 僵尸盘标志
⚠️ 必须输出纯 JSON, 不要 ``` 包裹。"""


async def generate_simple_evaluation(symbol: str, token_data: dict) -> Optional[dict]:
    """轻量 LLM 评估 (替代规则引擎, 用于高质量评分)"""
    if not model_router.is_configured():
        return None

    prompt = build_simple_evaluation_prompt(symbol, token_data)

    try:
        result = await model_router.call(
            TaskType.QUICK_CHECK,
            prompt,
            max_tokens=1500,
        )
        content = result.content.strip()
        # 清理可能的 markdown 包裹
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            if content.endswith("```"):
                content = content[:-3]
        return json.loads(content)
    except (json.JSONDecodeError, Exception) as e:
        logger.warning(f"轻量评估解析失败 {symbol}: {e}")
        return None
