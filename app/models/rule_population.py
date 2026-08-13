"""规则体系模型：遗传演化、A/B测试、生命周期"""
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, Float, Text, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class RuleIndividual(Base):
    """规则个体（遗传算法种群）"""
    __tablename__ = "rule_individuals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # 规则基因（编码）
    name: Mapped[str] = mapped_column(String(200))
    dimension: Mapped[str] = mapped_column(String(20))
    rule_expr: Mapped[dict] = mapped_column(JSON)

    # 基因来源
    origin: Mapped[str] = mapped_column(String(20), default="generated")  # generated / crossover / mutation
    parent_ids: Mapped[list] = mapped_column(JSON, default=list)  # 父代ID

    # 适应度
    fitness_score: Mapped[float] = mapped_column(Float, default=0.5)
    generation: Mapped[int] = mapped_column(Integer, default=1)

    # 生命周期
    status: Mapped[str] = mapped_column(String(15), default="active")  # active / dormant / eliminated
    confidence: Mapped[float] = mapped_column(Float, default=0.5)

    # 统计
    total_samples: Mapped[int] = mapped_column(Integer, default=0)
    success_samples: Mapped[int] = mapped_column(Integer, default=0)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RuleABExperiment(Base):
    """规则A/B对照实验"""
    __tablename__ = "rule_ab_experiments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # 实验名称
    experiment_name: Mapped[str] = mapped_column(String(200))
    dimension: Mapped[str] = mapped_column(String(20))

    # 对照组（成熟规则）
    control_rule_id: Mapped[int] = mapped_column(ForeignKey("rule_individuals.id"))
    control_score: Mapped[float] = mapped_column(Float, default=0.0)
    control_samples: Mapped[int] = mapped_column(Integer, default=0)

    # 实验组（新规则）
    experiment_rule_id: Mapped[int] = mapped_column(ForeignKey("rule_individuals.id"))
    experiment_score: Mapped[float] = mapped_column(Float, default=0.0)
    experiment_samples: Mapped[int] = mapped_column(Integer, default=0)

    # 实验状态
    status: Mapped[str] = mapped_column(String(15), default="running")  # running / control_wins / experiment_wins / tie
    winner: Mapped[str | None] = mapped_column(String(1), nullable=True)  # C / E / None

    # 观测指标
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)

    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class RuleLifecycleRecord(Base):
    """规则生命周期记录"""
    __tablename__ = "rule_lifecycle_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    rule_id: Mapped[int] = mapped_column(Integer, index=True)

    # 生命周期阶段
    stage: Mapped[str] = mapped_column(String(15))  # born / active / iterating / dormant / expired / eliminated
    action: Mapped[str] = mapped_column(String(50))
    reason: Mapped[str] = mapped_column(Text, default="")

    # 快照
    rule_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
