"""用户模型"""
from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(128), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255))

    # 用户画像
    user_type: Mapped[str] = mapped_column(String(20), default="general")  # student / worker / general
    wake_hour: Mapped[int] = mapped_column(Integer, default=7)  # 起床小时
    sleep_hour: Mapped[int] = mapped_column(Integer, default=23)  # 睡觉小时
    commute_minutes: Mapped[int] = mapped_column(Integer, default=30)  # 每日通勤时长(分钟)

    # 沟通风格 (演化层学习)
    comm_style: Mapped[str] = mapped_column(String(20), default="balanced")  # concise / detailed / balanced
    tone: Mapped[str] = mapped_column(String(20), default="friendly")  # serious / friendly

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
