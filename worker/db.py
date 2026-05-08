"""Worker 数据库操作 (同步, 基于 psycopg 3.x)

Worker 是 Celery 进程, 使用同步 DB 连接 (非 async)。
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from config import config

logger = logging.getLogger(__name__)


@contextmanager
def get_connection():
    """获取 PostgreSQL 连接 (with 语句自动关闭)"""
    conn = psycopg.connect(config.database_url)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def bulk_insert_scores(records: list[dict]) -> int:
    """
    批量写入评分结果到 token_scores 表。
    每次评估写新记录 (保留历史, 不覆盖)。
    """
    if not records:
        return 0

    columns = [
        "symbol", "name", "total_score", "risk_level",
        "liquidity_score", "volatility_score", "concentration_score",
        "fundamental_score", "sentiment_score", "compliance_score",
        "security_score", "macro_score",
        "market_cap_usd", "volume_24h_usd", "price_usd",
        "risk_details", "sentiment_summary", "evaluated_at",
    ]

    placeholders = ', '.join(['%s'] * len(columns))
    sql = f"INSERT INTO token_scores ({', '.join(columns)}) VALUES ({placeholders})"

    values = []
    for r in records:
        values.append((
            r["symbol"],
            r.get("name", r["symbol"]),
            r["total_score"],
            r["risk_level"],
            r.get("liquidity_score"),
            r.get("volatility_score"),
            r.get("concentration_score"),
            r.get("fundamental_score"),
            r.get("sentiment_score"),
            r.get("compliance_score"),
            r.get("security_score"),
            r.get("macro_score"),
            r.get("market_cap_usd"),
            r.get("volume_24h_usd"),
            r.get("price_usd"),
            json.dumps(r.get("risk_details", []), ensure_ascii=False),
            r.get("sentiment_summary", ""),
            datetime.now(timezone.utc),
        ))

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(sql, values)
            inserted = cur.rowcount

    logger.info(f"DB: inserted {inserted} token scores")
    return inserted


def create_scan_log(batch_id: str, total_tokens: int) -> None:
    """记录扫描开始"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO scan_logs (batch_id, total_tokens, status, completed, failed) VALUES (%s, %s, %s, %s, %s)",
                (batch_id, total_tokens, "running", 0, 0),
            )


def update_scan_log(batch_id: str, completed: int, failed: int, status: str) -> None:
    """更新扫描进度"""
    finished = datetime.now(timezone.utc) if status in ("completed", "failed") else None
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE scan_logs
                   SET completed = %s, failed = %s, status = %s, finished_at = %s
                   WHERE batch_id = %s""",
                (completed, failed, status, finished, batch_id),
            )


def save_report(symbol: str, report_type: str, title: str, content: str, trigger_source: str = "scheduled") -> None:
    """保存调研报告"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO token_reports (symbol, report_type, title, content, trigger_source)
                   VALUES (%s, %s, %s, %s, %s)""",
                (symbol, report_type, title, content, trigger_source),
            )
