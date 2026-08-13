"""多Agent协同高级创新模型：状态机、资源调度、预测智能"""
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, Float, Text, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class LifeSceneState(Base):
    """生活场景状态（全局联动）"""
    __tablename__ = "life_scene_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # 当前状态
    current_state: Mapped[str] = mapped_column(String(20), index=True)
    # daily / exam / travel / vacation / sick / overtime

    # 状态参数
    state_params: Mapped[dict] = mapped_column(JSON, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expected_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # 联动调整记录
    adjustments: Mapped[dict] = mapped_column(JSON, default=dict)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ResourceAllocation(Base):
    """资源统一调度记录"""
    __tablename__ = "resource_allocations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    allocation_date: Mapped[str] = mapped_column(String(10), index=True)

    # 四维资源分配
    time_alloc: Mapped[dict] = mapped_column(JSON, default=dict)  # 时间分配
    energy_alloc: Mapped[dict] = mapped_column(JSON, default=dict)  # 精力分配
    money_alloc: Mapped[dict] = mapped_column(JSON, default=dict)  # 金钱分配
    item_alloc: Mapped[dict] = mapped_column(JSON, default=dict)  # 物品分配

    # 调度策略
    strategy: Mapped[str] = mapped_column(String(50), default="balanced")
    total_score: Mapped[float] = mapped_column(Float, default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PredictionRecord(Base):
    """预测记录"""
    __tablename__ = "prediction_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # 预测内容
    prediction_type: Mapped[str] = mapped_column(String(30))
    # overspend / burnout / hoarding / conflict / energy_crash

    description: Mapped[str] = mapped_column(Text)
    probability: Mapped[float] = mapped_column(Float, default=0.0)
    severity: Mapped[str] = mapped_column(String(10), default="medium")  # low / medium / high

    # 预测依据
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)

    # 干预建议
    suggestion: Mapped[str] = mapped_column(Text, default="")

    # 验证
    was_accurate: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
