"""Celery Worker — 定时评估任务 + 手动触发

任务:
  1. run_daily_scan: 每日全量扫描 (UTC 00:00 = 北京 08:00)
  2. evaluate_single: 手动触发单币种评估
"""

import os
import asyncio
import hashlib
import logging
from datetime import datetime, timezone

from celery import Celery
from celery.schedules import crontab

from config import config
from evaluator import Evaluator
from db import create_scan_log, update_scan_log

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════
# Celery 配置
# ═══════════════════════════════════════════

app = Celery("crypto_risk", broker=config.REDIS_URL, backend=config.REDIS_URL)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=900,         # 单任务 15 分钟超时
    task_soft_time_limit=840,    # 软超时 14 分钟 (抛异常, 允许清理)
    worker_concurrency=config.WORKER_CONCURRENCY,
    worker_prefetch_multiplier=1,  # 公平调度
)

# ── 定时任务 ──
app.conf.beat_schedule = {
    "daily-full-scan": {
        "task": "tasks.run_daily_scan",
        "schedule": crontab(hour=0, minute=0),  # UTC 00:00 = 北京 08:00
    },
}


# ═══════════════════════════════════════════
# 任务定义
# ═══════════════════════════════════════════

evaluator = Evaluator()


@app.task(name="tasks.run_daily_scan", bind=True)
def run_daily_scan(self):
    """
    每日全量扫描:
    1. KuCoin 拉取币种列表
    2. 分批评估 (BATCH_SIZE 个/批)
    3. 批量写入数据库
    4. 高风险币种生成报告
    """
    batch_id = hashlib.md5(
        str(datetime.now(timezone.utc)).encode()
    ).hexdigest()[:12]

    logger.info(f"[scan:{batch_id}] === 开始每日全量扫描 ===")

    # 1. 获取币种列表
    tokens = asyncio.run(evaluator.get_token_list())
    total = len(tokens)
    logger.info(f"[scan:{batch_id}] 获取到 {total} 个 KuCoin 现货币种")

    # 记录扫描开始
    create_scan_log(batch_id, total)

    # 2. 分批评估
    batch_size = config.BATCH_SIZE
    max_scan = int(os.getenv("MAX_SCAN_TOKENS", str(len(tokens))))
    tokens = tokens[:max_scan]
    total = len(tokens)
    batches = [tokens[i:i + batch_size] for i in range(0, total, batch_size)]

    completed = 0
    failed = 0
    high_risk_symbols = []

    for i, batch in enumerate(batches):
        logger.info(f"[scan:{batch_id}] batch {i+1}/{len(batches)} ({len(batch)} tokens)")

        try:
            # 异步评估
            results = asyncio.run(evaluator.evaluate_batch(batch))

            # 写入数据库
            inserted = evaluator.save_results(results)
            completed += inserted
            failed += len(batch) - inserted

            # 收集高风险币种
            for r in results:
                if r["risk_level"] in ("极高", "高"):
                    high_risk_symbols.append(r["symbol"])

            # 更新扫描进度
            update_scan_log(batch_id, completed, failed, "running")

        except Exception as e:
            logger.error(f"[scan:{batch_id}] batch {i+1} error: {e}")
            failed += len(batch)
            update_scan_log(batch_id, completed, failed, "running")
            continue

    # 3. 高风险币种生成报告 (前 20 个)
    report_count = 0
    for sym in high_risk_symbols[:20]:
        try:
            # 找到对应的评估结果, 生成报告
            result_data = next(
                (r for batch_results in [asyncio.run(evaluator.evaluate_batch([sym]))]
                 for r in batch_results if r["symbol"] == sym),
                None,
            )
            if result_data:
                asyncio.run(evaluator.generate_report(sym, result_data))
                report_count += 1
        except Exception as e:
            logger.warning(f"[scan:{batch_id}] 报告生成失败 {sym}: {e}")

    # 4. 完成
    final_status = "completed" if failed == 0 else "completed"  # 部分失败也算完成
    update_scan_log(batch_id, completed, failed, final_status)

    summary = {
        "batch_id": batch_id,
        "total": total,
        "completed": completed,
        "failed": failed,
        "high_risk": len(high_risk_symbols),
        "reports_generated": report_count,
    }
    logger.info(f"[scan:{batch_id}] === 扫描完成 === {summary}")
    return summary


@app.task(name="tasks.evaluate_single", bind=True)
def evaluate_single(self, symbol: str):
    """
    手动触发单币种评估。
    同步评估 + 写入 DB + 生成报告 (如高风险)。
    """
    logger.info(f"[eval] 手动触发评估: {symbol}")

    # 评估
    result = asyncio.run(evaluator.evaluate_single(symbol))

    # 写入数据库
    evaluator.save_results([result])

    # 高风险则生成报告
    if result["risk_level"] in ("极高", "高"):
        asyncio.run(evaluator.generate_report(symbol, result))

    return {
        "symbol": symbol,
        "task_id": self.request.id,
        "status": "completed",
        "total_score": result["total_score"],
        "risk_level": result["risk_level"],
    }
