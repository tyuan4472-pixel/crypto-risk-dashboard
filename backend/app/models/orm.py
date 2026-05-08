"""SQLAlchemy ORM 模型 — 对应 docker/init.sql 表结构"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Numeric, Boolean, Text, DateTime, JSON, Index, text, func
)
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


class TokenScore(Base):
    """币种评分主表 — 每次评估写入一条记录"""

    __tablename__ = "token_scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    name = Column(String(100))
    total_score = Column(Numeric(5, 2), nullable=False)
    risk_level = Column(String(10), nullable=False)

    # 8 维度得分 (0-100)
    liquidity_score = Column(Numeric(5, 2))
    volatility_score = Column(Numeric(5, 2))
    concentration_score = Column(Numeric(5, 2))
    fundamental_score = Column(Numeric(5, 2))
    sentiment_score = Column(Numeric(5, 2))
    compliance_score = Column(Numeric(5, 2))
    security_score = Column(Numeric(5, 2))
    macro_score = Column(Numeric(5, 2))

    # 市场数据
    market_cap_usd = Column(Numeric(20, 2))
    volume_24h_usd = Column(Numeric(20, 2))
    price_usd = Column(Numeric(20, 8))

    # 风险明细 (JSONB)
    risk_details = Column(JSONB, default=[])
    sentiment_summary = Column(Text)

    # 时间戳
    evaluated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_token_scores_risk_level", "risk_level"),
        Index("idx_token_scores_evaluated_at", "evaluated_at"),
        Index("idx_token_scores_total", total_score.desc()),
    )


class TokenReport(Base):
    """币种调研报告表"""

    __tablename__ = "token_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    report_type = Column(String(20), nullable=False, default="full")  # full | summary | alert
    title = Column(String(200))
    content = Column(Text, nullable=False)
    generated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    trigger_source = Column(String(20), default="scheduled")  # scheduled | manual


class ScanLog(Base):
    """调度任务日志"""

    __tablename__ = "scan_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(String(36), nullable=False)
    total_tokens = Column(Integer, nullable=False)
    completed = Column(Integer, nullable=False, server_default=text("0"))
    failed = Column(Integer, nullable=False, server_default=text("0"))
    status = Column(String(20), nullable=False, default="running")  # running | completed | failed
    started_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    finished_at = Column(DateTime(timezone=True))
