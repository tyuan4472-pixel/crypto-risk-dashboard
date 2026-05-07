"""Celery Worker — 定时评估任务 + 手动触发评估"""

import asyncio
import hashlib
import json
from datetime import datetime, timezone

from celery import Celery
from celery.schedules import crontab

from evaluator import Evaluator


# Celery 应用配置 (Redis 作为 broker)
REDIS_URL = "redis://redis:6379/0"
app = Celery("crypto_risk", broker=REDIS_URL, backend=REDIS_URL)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,       # 单任务 10 分钟超时
    worker_concurrency=10,
)

# ── 定时任务配置 ──
app.conf.beat_schedule = {
    "daily-full-scan": {
        "task": "tasks.run_daily_scan",
        "schedule": crontab(hour=0, minute=0),  # UTC 00:00 = 北京时间 08:00
    },
}

evaluator = Evaluator()


@app.task(name="tasks.run_daily_scan", bind=True)
def run_daily_scan(self):
    """
    每日全量扫描: 拉取 KuCoin 币种列表 → 分批评估 → 写入数据库
    """
    batch_id = hashlib.md5(str(datetime.now(timezone.utc)).encode()).hexdigest()[:8]
    print(f"[scan:{batch_id}] 开始每日全量扫描")

    # 获取币种列表
    tokens = asyncio.run(evaluator.get_token_list())
    total = len(tokens)

    # 分批下发到 worker (每批 50)
    batch_size = 50
    batches = [tokens[i : i + batch_size] for i in range(0, total, batch_size)]

    # 异步评估每个 batch
    results = []
    for i, batch in enumerate(batches):
        # 同步等待每批完成 (避免数据库写入竞争)
        batch_results = asyncio.run(evaluator.evaluate_batch(batch))
        results.extend(batch_results)
        print(f"[scan:{batch_id}] batch {i+1}/{len(batches)} done, {len(batch_results)} tokens")

    # 写入数据库
    asyncio.run(evaluator.save_results(results))

    print(f"[scan:{batch_id}] 扫描完成: {total}/{total}, 失败: {total - len(results)}")
    return {"batch_id": batch_id, "total": total, "completed": len(results)}


@app.task(name="tasks.evaluate_single", bind=True)
def evaluate_single(self, symbol: str):
    """
    手动触发单币种评估
    """
    print(f"[eval] 手动触发评估: {symbol}")
    result = asyncio.run(evaluator.evaluate_single(symbol))
    asyncio.run(evaluator.save_results([result]))
    return {
        "symbol": symbol,
        "task_id": self.request.id,
        "status": "completed",
        "total_score": result.total_score,
        "risk_level": result.risk_level,
    }
