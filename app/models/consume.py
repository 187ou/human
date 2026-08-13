"""消费记账模型"""
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, Float, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ConsumeRecord(Base):
    __tablename__ = "consume_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    amount: Mapped[float] = mapped_column(Float)
    category: Mapped[str] = mapped_column(String(30))  # food / shopping / transport / entertainment / study / rent
    merchant: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 消费来源
    source: Mapped[str] = mapped_column(String(20), default="manual")  # wechat / alipay / bank / manual
    # 是否为冲动消费（演化层判定）
    is_impulse: Mapped[bool | None] = mapped_column(default=None)
    # 是否无效消费
    is_waste: Mapped[bool | None] = mapped_column(default=None)

    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Budget(Base):
    """品类预算（动态）"""
    __tablename__ = "budgets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    category: Mapped[str] = mapped_column(String(30))
    monthly_limit: Mapped[float] = mapped_column(Float)
    # 是否系统自动调整
    auto_tuned: Mapped[bool] = mapped_column(default=False)

    effective_month: Mapped[str] = mapped_column(String(7))  # YYYY-MM
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
