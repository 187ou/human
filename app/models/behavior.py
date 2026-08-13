"""行为观测日志（演化层数据源）"""
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, Float, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class BehaviorLog(Base):
    """用户行为采集日志（含结果反馈字段）"""
    __tablename__ = "behavior_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(index=True)
    dimension: Mapped[str] = mapped_column(String(20), index=True)  # time/study/consume/item/travel
    event_type: Mapped[str] = mapped_column(String(50))

    # --- 通用字段 ---
    event_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    hour_of_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    day_of_week: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    # --- 结果反馈字段 ---
    # 日程维度：完成状态 / 实际耗时(分钟) / 用户自评(1-5)
    schedule_completed: Mapped[bool | None] = mapped_column(nullable=True)
    schedule_duration_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    schedule_self_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5
    schedule_is_delayed: Mapped[bool | None] = mapped_column(default=None, nullable=True)

    # 学习维度：正确率(0-1) / 专注时长(分钟)
    study_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    study_focus_min: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # 消费维度：是否刚需 / 是否冲动
    consume_is_necessity: Mapped[bool | None] = mapped_column(default=None, nullable=True)
    consume_is_impulse: Mapped[bool | None] = mapped_column(default=None, nullable=True)

    # 物品维度：使用记录
    item_action: Mapped[str | None] = mapped_column(String(20), nullable=True)  # use/expire/discard

    # --- 演化结果记录 ---
    rule_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 关联的规则ID
    rule_applied: Mapped[bool] = mapped_column(default=False)  # 是否应用了规则
    result_note: Mapped[str | None] = mapped_column(Text, nullable=True)  # 备注
