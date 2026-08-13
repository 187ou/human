"""数据挖掘层模型：因果DAG、隐性模式、漂移检测"""
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, Float, Text, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class CausalDAGNode(Base):
    """因果DAG节点"""
    __tablename__ = "causal_dag_nodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # 节点信息
    node_name: Mapped[str] = mapped_column(String(100), index=True)
    node_type: Mapped[str] = mapped_column(String(30))  # sleep / energy / task_difficulty / impulse / burnout
    description: Mapped[str] = mapped_column(Text, default="")

    # 统计属性
    mean_value: Mapped[float] = mapped_column(Float, default=0.0)
    std_value: Mapped[float] = mapped_column(Float, default=0.0)
    sample_count: Mapped[int] = mapped_column(Integer, default=0)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CausalDAGEdge(Base):
    """因果DAG边（因果关系）"""
    __tablename__ = "causal_dag_edges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # 因果方向：cause → effect
    cause_node: Mapped[str] = mapped_column(String(100))
    effect_node: Mapped[str] = mapped_column(String(100))

    # 因果强度
    causal_strength: Mapped[float] = mapped_column(Float, default=0.0)  # 因果效应强度
    confidence: Mapped[float] = mapped_column(Float, default=0.0)  # 置信度

    # 验证
    support_samples: Mapped[int] = mapped_column(Integer, default=0)
    contradict_samples: Mapped[int] = mapped_column(Integer, default=0)

    # 因果路径
    path_description: Mapped[str] = mapped_column(Text, default="")

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class HiddenPattern(Base):
    """隐性行为模式"""
    __tablename__ = "hidden_patterns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # 模式信息
    pattern_type: Mapped[str] = mapped_column(String(30))  # willpower_dip / payday_impulse / focus_window
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)

    # 触发条件
    trigger: Mapped[dict] = mapped_column(JSON)  # {"time": "21:00-23:00", "condition": "weekday"}
    effect: Mapped[str] = mapped_column(Text)  # 影响描述

    # 统计支撑
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    sample_count: Mapped[int] = mapped_column(Integer, default=0)
    evidence: Mapped[list] = mapped_column(JSON, default=list)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DriftDetectionRecord(Base):
    """漂移检测记录"""
    __tablename__ = "drift_detection_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # 检测维度
    dimension: Mapped[str] = mapped_column(String(20))  # sleep / consume / study / schedule

    # KS检验结果
    ks_statistic: Mapped[float] = mapped_column(Float, default=0.0)
    p_value: Mapped[float] = mapped_column(Float, default=1.0)
    is_drifted: Mapped[bool] = mapped_column(Boolean, default=False)

    # 变化描述
    old_distribution: Mapped[dict] = mapped_column(JSON, default=dict)
    new_distribution: Mapped[dict] = mapped_column(JSON, default=dict)
    drift_description: Mapped[str] = mapped_column(Text, default="")

    # 处置
    action_taken: Mapped[str] = mapped_column(String(30), default="none")  # freeze_rules / reset_weights / re_evolution

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
