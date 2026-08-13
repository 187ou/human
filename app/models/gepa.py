"""GEPA遗传帕累托Prompt进化模型"""
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, Float, Text, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class PromptVariant(Base):
    """Prompt变体（种群个体）"""
    __tablename__ = "prompt_variants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # Prompt内容
    agent_type: Mapped[str] = mapped_column(String(20))  # time_plan / consume / study / travel / item
    prompt_content: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)

    # 来源
    origin: Mapped[str] = mapped_column(String(20), default="generated")  # generated / crossover / mutation
    parent_ids: Mapped[list] = mapped_column(JSON, default=list)

    # 帕累托评分（多目标）
    completion_score: Mapped[float] = mapped_column(Float, default=0.5)  # 完成率
    conciseness_score: Mapped[float] = mapped_column(Float, default=0.5)  # 简洁度
    empathy_score: Mapped[float] = mapped_column(Float, default=0.5)  # 共情适配
    accuracy_score: Mapped[float] = mapped_column(Float, default=0.5)  # 准确率（反幻觉）

    # 帕累托等级
    pareto_rank: Mapped[int] = mapped_column(Integer, default=0)  # 0=最优
    is_dominated: Mapped[bool] = mapped_column(Boolean, default=False)

    # 适应度
    fitness_score: Mapped[float] = mapped_column(Float, default=0.5)
    generation: Mapped[int] = mapped_column(Integer, default=1)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PromptEvolutionRecord(Base):
    """Prompt进化记录"""
    __tablename__ = "prompt_evolution_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # 进化信息
    agent_type: Mapped[str] = mapped_column(String(20))
    generation: Mapped[int] = mapped_column(Integer, default=1)

    # 种群统计
    population_size: Mapped[int] = mapped_column(Integer, default=0)
    pareto_front_size: Mapped[int] = mapped_column(Integer, default=0)

    # 最优个体
    best_variant_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    best_fitness: Mapped[float] = mapped_column(Float, default=0.0)

    # 进化参数
    crossover_rate: Mapped[float] = mapped_column(Float, default=0.3)
    mutation_rate: Mapped[float] = mapped_column(Float, default=0.15)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
