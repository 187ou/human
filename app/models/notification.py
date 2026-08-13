"""通知消息模型"""
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Notification(Base):
    """通知消息（聚合所有模块的提醒）"""
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # 通知类型
    type: Mapped[str] = mapped_column(String(30), index=True)
    # schedule_reminder / item_expire / budget_alert / study_checkin / system

    # 来源模块
    source: Mapped[str] = mapped_column(String(20))  # schedule / consume / item / study / system

    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)

    # 关联数据
    related_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    related_type: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # 优先级
    priority: Mapped[str] = mapped_column(String(10), default="normal")  # low / normal / high / urgent

    # 状态
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    is_pushed: Mapped[bool] = mapped_column(Boolean, default=False)

    # 定时推送
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
