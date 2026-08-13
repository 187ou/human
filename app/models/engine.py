"""底层架构模型：分层闭环自演化引擎"""
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, Float, Text, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class EvolutionLayer(Base):
    """演化层级记录"""
    __tablename__ = "evolution_layers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # 层级类型
    layer_type: Mapped[str] = mapped_column(String(20))  # online / nightly / weekly

    # 触发信息
    trigger_event: Mapped[str] = mapped_column(String(100))
    triggered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 演化结果
    rules_affected: Mapped[int] = mapped_column(Integer, default=0)
    rules_created: Mapped[int] = mapped_column(Integer, default=0)
    rules_modified: Mapped[int] = mapped_column(Integer, default=0)
    rules_deprecated: Mapped[int] = mapped_column(Integer, default=0)

    # 效果评估
    effectiveness_score: Mapped[float] = mapped_column(Float, default=0.0)
    token_cost: Mapped[int] = mapped_column(Integer, default=0)

    # 详细信息
    details: Mapped[dict] = mapped_column(JSON, default=dict)


class SandboxSimulation(Base):
    """沙箱仿真记录"""
    __tablename__ = "sandbox_simulations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # 被测试内容
    content_type: Mapped[str] = mapped_column(String(20))  # rule / prompt / plan
    content: Mapped[dict] = mapped_column(JSON)
    content_name: Mapped[str] = mapped_column(String(200))

    # 仿真结果
    is_safe: Mapped[bool] = mapped_column(Boolean, default=True)
    risk_checks: Mapped[dict] = mapped_column(JSON, default=dict)

    # 处置
    action: Mapped[str] = mapped_column(String(20), default="approved")  # approved / rejected / modified

    simulated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class GitSnapshot(Base):
    """Git式快照存档"""
    __tablename__ = "git_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # 快照信息
    commit_hash: Mapped[str] = mapped_column(String(16), index=True)
    parent_hash: Mapped[str | None] = mapped_column(String(16), nullable=True)
    message: Mapped[str] = mapped_column(Text)

    # 快照数据
    rules_snapshot: Mapped[list] = mapped_column(JSON, default=list)
    prompts_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    config_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)

    # 变更统计
    changes_count: Mapped[int] = mapped_column(Integer, default=0)
    rules_added: Mapped[int] = mapped_column(Integer, default=0)
    rules_removed: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MetaEvolutionState(Base):
    """元演化调控状态"""
    __tablename__ = "meta_evolution_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # 演化状态
    current_phase: Mapped[str] = mapped_column(String(20), default="stable")  # exploring / converging / stagnant / resetting
    evolution_speed: Mapped[str] = mapped_column(String(10), default="normal")  # slow / normal / fast

    # 监控指标
    convergence_score: Mapped[float] = mapped_column(Float, default=0.5)  # 收敛度 0-1
    stagnation_counter: Mapped[int] = mapped_column(Integer, default=0)  # 停滞计数器
    exploration_rate: Mapped[float] = mapped_column(Float, default=0.1)  # 探索率

    # 调控决策
    last_decision: Mapped[str] = mapped_column(String(50), default="")
    decision_reason: Mapped[str] = mapped_column(Text, default="")

    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
