"""演化快照与同步模型"""
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, Boolean, JSON, Float
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class EvolutionSnapshot(Base):
    """演化快照（全量演化时自动保存）"""
    __tablename__ = "evolution_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # 快照信息
    version: Mapped[int] = mapped_column(Integer, index=True)
    snapshot_type: Mapped[str] = mapped_column(String(20), default="full")  # full / incremental

    # 快照数据
    rules_snapshot: Mapped[list] = mapped_column(JSON, default=list)  # 规则快照
    preferences_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)  # 偏好快照
    behavior_summary: Mapped[dict] = mapped_column(JSON, default=dict)  # 行为摘要

    # 元数据
    rules_count: Mapped[int] = mapped_column(Integer, default=0)
    confidence_avg: Mapped[float] = mapped_column(default=0.0)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SyncRecord(Base):
    """多设备同步记录"""
    __tablename__ = "sync_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # 设备信息
    device_id: Mapped[str] = mapped_column(String(64), index=True)
    device_name: Mapped[str] = mapped_column(String(100))
    device_type: Mapped[str] = mapped_column(String(20))  # pc / mobile / tablet

    # 同步数据
    last_sync_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    sync_token: Mapped[str] = mapped_column(String(64))
    changes_count: Mapped[int] = mapped_column(Integer, default=0)

    # 同步状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)


class LLMRejectLog(Base):
    """LLM生成内容驳回记录"""
    __tablename__ = "llm_reject_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # 驳回内容
    content_type: Mapped[str] = mapped_column(String(30))  # schedule / rule / plan
    original_content: Mapped[dict] = mapped_column(JSON)
    reject_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 修正后内容
    corrected_content: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_corrected: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class LargeExpenseRecord(Base):
    """大额支出记录与重核算"""
    __tablename__ = "large_expense_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # 支出信息
    amount: Mapped[float] = mapped_column(Float)
    category: Mapped[str] = mapped_column(String(30))
    merchant: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # 阈值判定
    threshold_amount: Mapped[float] = mapped_column(Float)  # 触发阈值
    is_large: Mapped[bool] = mapped_column(Boolean, default=True)

    # 重核算结果
    original_budget: Mapped[float] = mapped_column(Float, default=0)
    adjusted_budget: Mapped[float] = mapped_column(Float, default=0)
    adjustment_plan: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
