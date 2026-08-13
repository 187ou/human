"""系统自演化高级机制模型：风险自检、偏好漂移、A/B测试"""
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, Float, Text, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class RiskCheckResult(Base):
    """风险自检结果"""
    __tablename__ = "risk_check_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # 被检测的规则
    rule_name: Mapped[str] = mapped_column(String(200))
    rule_expr: Mapped[dict] = mapped_column(JSON)

    # 风险类型
    risk_type: Mapped[str] = mapped_column(String(30))  # task_overload / budget_collapse / schedule_disruption
    risk_level: Mapped[str] = mapped_column(String(10))  # low / medium / high / critical

    # 检测结果
    is_safe: Mapped[bool] = mapped_column(Boolean, default=True)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    details: Mapped[str] = mapped_column(Text, default="")

    # 处置
    action_taken: Mapped[str] = mapped_column(String(20), default="approved")  # approved / blocked / modified

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PreferenceDriftRecord(Base):
    """用户偏好漂移记录"""
    __tablename__ = "preference_drift_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # 漂移信息
    drift_type: Mapped[str] = mapped_column(String(50))  # slump_to_discipline / homebody_to_social / etc
    dimension: Mapped[str] = mapped_column(String(20))  # study / consume / schedule / social

    # 变化幅度
    drift_score: Mapped[float] = mapped_column(Float, default=0.0)  # 漂移程度 0-1
    old_pattern: Mapped[str] = mapped_column(Text, default="")
    new_pattern: Mapped[str] = mapped_column(Text, default="")

    # 处置
    rules_reset: Mapped[list] = mapped_column(JSON, default=list)  # 被重置的规则ID列表
    is_handled: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RuleABTest(Base):
    """规则A/B测试"""
    __tablename__ = "rule_ab_tests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # 测试主题
    test_name: Mapped[str] = mapped_column(String(200))
    dimension: Mapped[str] = mapped_column(String(20))

    # A版本
    rule_a_id: Mapped[int | None] = mapped_column(ForeignKey("user_rules.id"), nullable=True)
    rule_a_expr: Mapped[dict] = mapped_column(JSON)
    a_score: Mapped[float] = mapped_column(Float, default=0.0)
    a_samples: Mapped[int] = mapped_column(Integer, default=0)

    # B版本
    rule_b_id: Mapped[int | None] = mapped_column(ForeignKey("user_rules.id"), nullable=True)
    rule_b_expr: Mapped[dict] = mapped_column(JSON)
    b_score: Mapped[float] = mapped_column(Float, default=0.0)
    b_samples: Mapped[int] = mapped_column(Integer, default=0)

    # 测试状态
    status: Mapped[str] = mapped_column(String(15), default="running")  # running / a_wins / b_wins / tie
    winner: Mapped[str | None] = mapped_column(String(1), nullable=True)  # A / B / None

    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
