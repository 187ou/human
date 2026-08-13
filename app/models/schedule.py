"""日程与时间规划模型"""
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, Float, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Schedule(Base):
    """日程（日历视图）"""
    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(30), default="other")  # fixed / flexible / study / sport

    start_time: Mapped[datetime] = mapped_column(DateTime)
    end_time: Mapped[datetime] = mapped_column(DateTime)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    source: Mapped[str] = mapped_column(String(20), default="manual")  # manual / recurring / auto
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completion_quality: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_paused: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否暂停（突发场景）
    original_start: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # 暂停前原始时间

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ScheduleItem(Base):
    """碎片任务 / 微任务"""
    __tablename__ = "schedule_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=15)
    priority: Mapped[int] = mapped_column(Integer, default=5)  # 1-10
    slot_type: Mapped[str] = mapped_column(String(30), default="fragment")  # commute / lunch / evening / fragment

    is_done: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class RecurringException(Base):
    """周期性例外日程"""
    __tablename__ = "recurring_exceptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 周期规则（JSON）：{"days_of_week": [1,2,3,4,5], "start_time": "19:00", "end_time": "21:00", "action": "add/pause/skip"}
    rule_expr: Mapped[dict] = mapped_column(JSON)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    effective_from: Mapped[datetime] = mapped_column(DateTime)
    effective_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
