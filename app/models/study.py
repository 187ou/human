"""学习督导模型（含知识点、错题、效率统计、动态调整）"""
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, Float, Text, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class StudyPlan(Base):
    """学习计划"""
    __tablename__ = "study_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    title: Mapped[str] = mapped_column(String(200))
    subject: Mapped[str] = mapped_column(String(50))
    target_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    difficulty: Mapped[int] = mapped_column(Integer, default=5)
    status: Mapped[str] = mapped_column(String(20), default="active")

    planned_start: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    planned_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    estimated_hours: Mapped[float] = mapped_column(Float, default=1.0)

    # 动态调整
    daily_new_knowledge_target: Mapped[int] = mapped_column(Integer, default=5)  # 每日新知识点目标
    daily_review_target: Mapped[int] = mapped_column(Integer, default=10)  # 每日复习目标
    current_difficulty_level: Mapped[float] = mapped_column(Float, default=1.0)  # 当前难度系数(动态调整)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class StudyRecord(Base):
    """学习记录"""
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
    efficiency: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_delayed: Mapped[bool] = mapped_column(Boolean, default=False)
    quality: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # 专注时长 vs 挂机时长
    focus_minutes: Mapped[int] = mapped_column(Integer, default=0)  # 有效专注时长
    idle_minutes: Mapped[int] = mapped_column(Integer, default=0)  # 挂机/走神时长
    accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)  # 做题正确率

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class KnowledgePoint(Base):
    """知识点清单"""
    __tablename__ = "knowledge_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    subject: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 掌握程度
    mastery_level: Mapped[int] = mapped_column(Integer, default=0)  # 0-100
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # 正确率统计
    total_attempts: Mapped[int] = mapped_column(Integer, default=0)
    correct_attempts: Mapped[int] = mapped_column(Integer, default=0)
    accuracy_rate: Mapped[float] = mapped_column(Float, default=0.0)

    # 来源
    source: Mapped[str] = mapped_column(String(20), default="manual")  # manual / import / auto

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WrongQuestion(Base):
    """错题记录"""
    __tablename__ = "wrong_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    subject: Mapped[str] = mapped_column(String(50))
    question: Mapped[str] = mapped_column(Text)
    correct_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    my_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    analysis: Mapped[str | None] = mapped_column(Text, nullable=True)  # 错误分析

    # 关联知识点
    knowledge_point_id: Mapped[int | None] = mapped_column(ForeignKey("knowledge_points.id", ondelete="SET NULL"), nullable=True)

    # 复习追踪
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_mastered: Mapped[bool] = mapped_column(Boolean, default=False)

    difficulty: Mapped[int] = mapped_column(Integer, default=5)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class StudyStreak(Base):
    """学习连续记录（用于休息日判定）"""
    __tablename__ = "study_streaks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    study_date: Mapped[str] = mapped_column(String(10))  # YYYY-MM-DD
    intensity: Mapped[str] = mapped_column(String(10))  # light / normal / high
    total_minutes: Mapped[int] = mapped_column(Integer, default=0)
    is_rest_day: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
