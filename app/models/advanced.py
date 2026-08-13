"""高级智能能力模型：隐性习惯、难度缩放、稳态维持、个性化Prompt、负反馈学习"""
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, Float, Text, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class HiddenHabit(Base):
    """隐性习惯（用户自己不知道的规律）"""
    __tablename__ = "hidden_habits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # 习惯描述
    habit_type: Mapped[str] = mapped_column(String(30))  # slump_timed / procrastinate_trigger / energy_dip
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)

    # 触发条件
    trigger_condition: Mapped[dict] = mapped_column(JSON)  # {"time_range": "20:00-23:00", "day_type": "weekday"}
    effect_description: Mapped[str] = mapped_column(Text)  # 影响描述

    # 统计支撑
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    sample_count: Mapped[int] = mapped_column(Integer, default=0)
    evidence: Mapped[list] = mapped_column(JSON, default=list)  # 证据样本

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TaskDifficultyLog(Base):
    """任务难度自适应记录"""
    __tablename__ = "task_difficulty_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    task_date: Mapped[str] = mapped_column(String(10), index=True)

    # 原始参数
    original_difficulty: Mapped[float] = mapped_column(Float, default=5.0)  # 1-10
    original_count: Mapped[int] = mapped_column(Integer, default=5)

    # 调整后参数
    adjusted_difficulty: Mapped[float] = mapped_column(Float, default=5.0)
    adjusted_count: Mapped[int] = mapped_column(Integer, default=5)

    # 调整原因
    adjustment_reason: Mapped[str] = mapped_column(Text, default="")
    adjustment_factors: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class LifeStabilityState(Base):
    """生活稳态状态"""
    __tablename__ = "life_stability_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    state_date: Mapped[str] = mapped_column(String(10), index=True)

    # 稳态指标
    stability_score: Mapped[float] = mapped_column(Float, default=50.0)  # 0-100
    pressure_level: Mapped[str] = mapped_column(String(10), default="normal")  # low / normal / high / critical

    # 连续状态计数
    consecutive_slump_days: Mapped[int] = mapped_column(Integer, default=0)  # 连续摆烂天数
    consecutive_high_days: Mapped[int] = mapped_column(Integer, default=0)  # 连续高压天数

    # 干预措施
    intervention: Mapped[str | None] = mapped_column(String(50), nullable=True)  # reduce_pressure / add_rest / boost_mood
    intervention_applied: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PersonalPrompt(Base):
    """个性化Prompt（千人千模型）"""
    __tablename__ = "personal_prompts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # Prompt类型
    agent_type: Mapped[str] = mapped_column(String(20))  # time_plan / consume / study / travel / item

    # Prompt内容
    system_prompt: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)

    # 进化信息
    evolved_from: Mapped[str | None] = mapped_column(Text, nullable=True)  # 进化原因
    performance_score: Mapped[float] = mapped_column(Float, default=0.5)  # 效果评分

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class NegativeFeedback(Base):
    """行为负反馈学习记录"""
    __tablename__ = "negative_feedbacks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # 负反馈类型
    feedback_type: Mapped[str] = mapped_column(String(20))  # delay / cancel / fail / skip / waste

    # 关联信息
    dimension: Mapped[str] = mapped_column(String(20))  # time / study / consume / item
    related_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # 详情
    description: Mapped[str] = mapped_column(Text)
    severity: Mapped[int] = mapped_column(Integer, default=5)  # 1-10

    # 根因分析
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    lesson: Mapped[str | None] = mapped_column(Text, nullable=True)  # 教训

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
