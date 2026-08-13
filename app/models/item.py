"""物品收纳模型"""
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(50))  # food / cosmetic / medicine / card / coupon / document / other
    location: Mapped[str] = mapped_column(String(200))  # 存放位置
    quantity: Mapped[int] = mapped_column(Integer, default=1)

    # 过期相关
    expire_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expire_remind_days: Mapped[int] = mapped_column(Integer, default=7)  # 提前几天提醒

    # 使用追踪
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    use_count: Mapped[int] = mapped_column(Integer, default=0)
    # 是否闲置（演化层判定）
    is_idle: Mapped[bool] = mapped_column(Boolean, default=False)
    idle_days_threshold: Mapped[int] = mapped_column(Integer, default=30)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
