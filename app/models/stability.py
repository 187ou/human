"""生活稳态维持演化目标函数模型"""
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, Float, Text, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class StabilityObjective(Base):
    """稳态目标函数配置"""
    __tablename__ = "stability_objectives"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # 目标权重（动态调整）
    efficiency_weight: Mapped[float] = mapped_column(Float, default=0.3)
    well_being_weight: Mapped[float] = mapped_column(Float, default=0.3)
    sustainability_weight: Mapped[float] = mapped_column(Float, default=0.25)
    growth_weight: Mapped[float] = mapped_column(Float, default=0.15)

    # 稳态阈值
    max_consecutive_high_days: Mapped[int] = mapped_column(Integer, default=3)
    max_consecutive_slump_days: Mapped[int] = mapped_column(Integer, default=5)
    budget_imbalance_threshold: Mapped[float] = mapped_column(Float, default=1.2)

    # 干预策略
    rest_day_frequency: Mapped[int] = mapped_column(Integer, default=7)
    task_ramp_up_rate: Mapped[float] = mapped_column(Float, default=0.1)
    budget_adjust_rate: Mapped[float] = mapped_column(Float, default=0.15)

    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class StabilityIntervention(Base):
    """稳态干预记录"""
    __tablename__ = "stability_interventions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # 干预类型
    intervention_type: Mapped[str] = mapped_column(String(30))
    # rest_insert / task_reduce / task_ramp_up / budget_smooth / schedule_rebalance

    # 触发原因
    trigger: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(10))  # low / medium / high

    # 干预措施
    action_taken: Mapped[str] = mapped_column(Text)
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)

    # 效果
    was_effective: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
