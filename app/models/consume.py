"""消费记账模型（含账单导入、AI打标、弹性预算、复盘报告）"""
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, Float, Text, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ConsumeRecord(Base):
    """消费记录"""
    __tablename__ = "consume_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    amount: Mapped[float] = mapped_column(Float)
    category: Mapped[str] = mapped_column(String(30))
    merchant: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 消费来源
    source: Mapped[str] = mapped_column(String(20), default="manual")  # wechat / alipay / bank / manual
    raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # 原始账单数据

    # AI自动打标
    tag: Mapped[str | None] = mapped_column(String(20), nullable=True)  # necessity / impulse / hoarding / fixed
    is_impulse: Mapped[bool | None] = mapped_column(Boolean, default=None)
    is_waste: Mapped[bool | None] = mapped_column(Boolean, default=None)

    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Budget(Base):
    """品类预算（动态+弹性）"""
    __tablename__ = "budgets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    category: Mapped[str] = mapped_column(String(30))
    monthly_limit: Mapped[float] = mapped_column(Float)
    auto_tuned: Mapped[bool] = mapped_column(default=False)

    # 弹性预算：是否允许从其他品类划拨
    is_flexible: Mapped[bool] = mapped_column(Boolean, default=False)
    # 弹性来源品类（如娱乐额度可划拨给医疗）
    flex_source_categories: Mapped[list | None] = mapped_column(JSON, nullable=True)

    effective_month: Mapped[str] = mapped_column(String(7))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class BudgetTransfer(Base):
    """预算划拨记录"""
    __tablename__ = "budget_transfers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    from_category: Mapped[str] = mapped_column(String(30))  # 来源品类
    to_category: Mapped[str] = mapped_column(String(30))  # 目标品类
    amount: Mapped[float] = mapped_column(Float)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    effective_month: Mapped[str] = mapped_column(String(7))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MonthlyReview(Base):
    """月度消费复盘报告"""
    __tablename__ = "monthly_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    month: Mapped[str] = mapped_column(String(7))  # YYYY-MM

    # 统计数据
    total_spent: Mapped[float] = mapped_column(Float, default=0)
    total_budget: Mapped[float] = mapped_column(Float, default=0)
    surplus: Mapped[float] = mapped_column(Float, default=0)

    # 分类统计
    category_breakdown: Mapped[dict] = mapped_column(JSON, default=dict)
    tag_breakdown: Mapped[dict] = mapped_column(JSON, default=dict)

    # AI生成内容
    waste_items: Mapped[list] = mapped_column(JSON, default=list)
    suggestions: Mapped[list] = mapped_column(JSON, default=list)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class BudgetAlert(Base):
    """预算提醒记录"""
    __tablename__ = "budget_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    category: Mapped[str] = mapped_column(String(30))
    alert_type: Mapped[str] = mapped_column(String(20))  # warning(80%) / critical(95%) / exceeded(100%)
    current_amount: Mapped[float] = mapped_column(Float)
    budget_limit: Mapped[float] = mapped_column(Float)
    percentage: Mapped[float] = mapped_column(Float)
    effective_month: Mapped[str] = mapped_column(String(7))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
