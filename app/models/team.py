"""多智能体协同演化模型"""
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, Float, Text, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AgentPerformance(Base):
    """Agent个体表现记录"""
    __tablename__ = "agent_performances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # Agent信息
    agent_name: Mapped[str] = mapped_column(String(20))  # time_plan / consume / study / travel / item

    # 表现指标
    total_tasks: Mapped[int] = mapped_column(Integer, default=0)
    success_tasks: Mapped[int] = mapped_column(Integer, default=0)
    avg_quality: Mapped[float] = mapped_column(Float, default=0.5)

    # Prompt版本
    prompt_version: Mapped[int] = mapped_column(Integer, default=1)
    prompt_content: Mapped[str] = mapped_column(Text, default="")

    # 优化记录
    last_optimized_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    optimization_notes: Mapped[str] = mapped_column(Text, default="")

    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class InteractionProtocol(Base):
    """Agent间交互协议"""
    __tablename__ = "interaction_protocols"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # 交互双方
    source_agent: Mapped[str] = mapped_column(String(20))
    target_agent: Mapped[str] = mapped_column(String(20))

    # 协议内容
    trigger_condition: Mapped[str] = mapped_column(Text)  # 触发条件
    action_type: Mapped[str] = mapped_column(String(30))  # notify / request / sync / negotiate
    protocol_config: Mapped[dict] = mapped_column(JSON, default=dict)

    # 效果
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    fail_count: Mapped[int] = mapped_column(Integer, default=0)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class GraphNodeConfig(Base):
    """LangGraph节点配置（动态）"""
    __tablename__ = "graph_node_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # 节点信息
    node_name: Mapped[str] = mapped_column(String(50))
    node_type: Mapped[str] = mapped_column(String(20))  # router / agent / tool / noop

    # 动态配置
    weight: Mapped[float] = mapped_column(Float, default=1.0)  # 调度权重
    priority: Mapped[int] = mapped_column(Integer, default=1)  # 优先级
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # 条件配置
    condition_expr: Mapped[str] = mapped_column(Text, default="")  # 分支条件

    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
