"""核心创新模型：因果挖掘、精力建模、状态记忆、规则生命周期、博弈协商"""
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, Float, Text, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class CausalEdge(Base):
    """行为因果边（因果推理引擎产出）"""
    __tablename__ = "causal_edges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # 因果关系：cause → effect
    cause_event: Mapped[str] = mapped_column(String(100))  # 因事件
    effect_event: Mapped[str] = mapped_column(String(100))  # 果事件

    # 因果强度
    confidence: Mapped[float] = mapped_column(Float, default=0.0)  # 因果置信度 0-1
    correlation: Mapped[float] = mapped_column(Float, default=0.0)  # 相关系数

    # 因果类型
    causal_type: Mapped[str] = mapped_column(String(20), default="direct")  # direct / indirect / spurious

    # 验证数据
    support_count: Mapped[int] = mapped_column(Integer, default=0)  # 支持样本数
    contradict_count: Mapped[int] = mapped_column(Integer, default=0)  # 反驳样本数

    # 结论描述
    conclusion: Mapped[str] = mapped_column(Text, default="")

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EnergyRecord(Base):
    """用户精力值记录（每日一条）"""
    __tablename__ = "energy_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    record_date: Mapped[str] = mapped_column(String(10), index=True)  # YYYY-MM-DD

    # 四维精力模型
    sleep_score: Mapped[float] = mapped_column(Float, default=0.0)  # 睡眠质量 0-100
    load_score: Mapped[float] = mapped_column(Float, default=0.0)  # 昨日负荷 0-100
    completion_score: Mapped[float] = mapped_column(Float, default=0.0)  # 完成率 0-100
    focus_score: Mapped[float] = mapped_column(Float, default=0.0)  # 专注度 0-100

    # 综合精力值
    total_energy: Mapped[float] = mapped_column(Float, default=0.0)  # 综合精力 0-100
    energy_level: Mapped[str] = mapped_column(String(10), default="medium")  # low / medium / high

    # 影响因素分析
    factors: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class LifeStateSnapshot(Base):
    """生活状态快照（全局上下文记忆）"""
    __tablename__ = "life_state_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    snapshot_date: Mapped[str] = mapped_column(String(10), index=True)

    # 人生阶段判定
    life_phase: Mapped[str] = mapped_column(String(20), default="normal")  # exam / slump / busy / vacation / normal
    phase_confidence: Mapped[float] = mapped_column(Float, default=0.0)

    # 状态指标
    avg_study_minutes: Mapped[float] = mapped_column(Float, default=0)
    avg_consume_amount: Mapped[float] = mapped_column(Float, default=0)
    schedule_density: Mapped[float] = mapped_column(Float, default=0)  # 日程密度
    social_activity_count: Mapped[int] = mapped_column(Integer, default=0)

    # 趋势
    trend: Mapped[str] = mapped_column(String(10), default="stable")  # rising / declining / stable

    # 状态描述
    summary: Mapped[str] = mapped_column(Text, default="")
    context_memory: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RuleLifecycleLog(Base):
    """规则生命周期日志"""
    __tablename__ = "rule_lifecycle_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("user_rules.id", ondelete="CASCADE"), index=True)

    # 生命周期阶段
    stage: Mapped[str] = mapped_column(String(20))  # born / active / iterating / expiring / expired / eliminated
    action: Mapped[str] = mapped_column(String(50))

    # 详情
    reason: Mapped[str] = mapped_column(Text, nullable=True)
    snapshot: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AgentNegotiation(Base):
    """多智能体博弈协商记录"""
    __tablename__ = "agent_negotiations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # 协商主题
    topic: Mapped[str] = mapped_column(String(200))
    conflict_type: Mapped[str] = mapped_column(String(50))

    # 各方诉求
    proposals: Mapped[dict] = mapped_column(JSON, default=dict)  # {agent: proposal}

    # 协商结果
    final_decision: Mapped[dict] = mapped_column(JSON, default=dict)
    winner_agent: Mapped[str | None] = mapped_column(String(20), nullable=True)
    compromise_score: Mapped[float] = mapped_column(Float, default=0.0)  # 折中程度 0-1

    # 协商过程
    rounds: Mapped[int] = mapped_column(Integer, default=0)
    negotiation_log: Mapped[list] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
