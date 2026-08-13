"""学习督导模型"""
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, Float, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class StudyPlan(Base):
    __tablename__ = "study_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    title: Mapped[str] = mapped_column(String(200))
    subject: Mapped[str] = mapped_column(String(50))  # 学科/方向
    target_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 难度与状态
    difficulty: Mapped[int] = mapped_column(Integer, default=5)  # 1-10
    status: Mapped[str] = mapped_column(String(20), default="active")  # active / paused / done

    # 时间规划
    planned_start: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    planned_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    estimated_hours: Mapped[float] = mapped_column(Float, default=1.0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class StudyRecord(Base):
    """学习记录（演化层核心数据源）"""
    __tablename__ = "study_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    plan_id: Mapped[int | None] = mapped_column(ForeignKey("study_plans.id", ondelete="SET NULL"), nullable=True)

    subject: Mapped[str] = mapped_column(String(50))
    content: Mapped[str | None] = mapped_column(Text, nullable=True)

    start_time: Mapped[datetime] = mapped_column(DateTime)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=0)

    # 效率评估
    efficiency: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0-1
    # 是否拖延后完成
    is_delayed: Mapped[bool] = mapped_column(Boolean, default=False)
    # 完成质量自评 1-5
    quality: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
