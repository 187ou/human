"""记忆与经验模型：分层记忆、技能封装、失败复盘"""
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, Float, Text, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class EpisodicMemory(Base):
    """情景记忆（近3个月行为轨迹）"""
    __tablename__ = "episodic_memories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # 记忆内容
    memory_type: Mapped[str] = mapped_column(String(30))  # success / failure / milestone
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)

    # 关联数据
    dimension: Mapped[str] = mapped_column(String(20))
    related_data: Mapped[dict] = mapped_column(JSON, default=dict)

    # 重要性评分
    importance: Mapped[float] = mapped_column(Float, default=0.5)
    emotional_valence: Mapped[float] = mapped_column(Float, default=0.0)  # -1负面 ~ +1正面

    # 压缩标记
    is_compressed: Mapped[bool] = mapped_column(Boolean, default=False)
    compressed_to_rule_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class LifeSkill(Base):
    """生活技能（可复用任务工作流）"""
    __tablename__ = "life_skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # 技能信息
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    skill_type: Mapped[str] = mapped_column(String(30))  # consume_review / travel_pack / study_plan

    # 技能定义
    steps: Mapped[list] = mapped_column(JSON, default=list)  # 步骤列表
    tools_required: Mapped[list] = mapped_column(JSON, default=list)  # 所需工具

    # 使用统计
    use_count: Mapped[int] = mapped_column(Integer, default=0)
    success_rate: Mapped[float] = mapped_column(Float, default=0.5)
    avg_duration_min: Mapped[float] = mapped_column(Float, default=0)

    # 元数据
    source: Mapped[str] = mapped_column(String(20), default="auto")  # auto / manual
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FailureMemory(Base):
    """失败记忆（专项复盘）"""
    __tablename__ = "failure_memories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # 失败信息
    failure_type: Mapped[str] = mapped_column(String(30))  # delay / cancel / overspend / burnout
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)

    # 根因分析
    root_cause: Mapped[str] = mapped_column(Text, default="")
    trigger_conditions: Mapped[dict] = mapped_column(JSON, default=dict)

    # 规避策略
    avoidance_strategy: Mapped[str] = mapped_column(Text, default="")
    counter_rule_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # 严重程度
    severity: Mapped[int] = mapped_column(Integer, default=5)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
