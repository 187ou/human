"""用户专属规则库（演化层输出）"""
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, Float, Text, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class UserRule(Base):
    """从行为数据中挖掘出的用户专属规则"""
    __tablename__ = "user_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(index=True)
    dimension: Mapped[str] = mapped_column(String(20), index=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    rule_expr: Mapped[dict] = mapped_column(JSON)

    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    sample_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=1)  # 1=低 2=中 3=高

    version: Mapped[int] = mapped_column(Integer, default=1)
    evolved_from_id: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
