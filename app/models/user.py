"""用户模型（含完整画像字段）"""
from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, Integer, Float, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(128), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255))

    # === 基础画像 ===
    user_type: Mapped[str] = mapped_column(String(20), default="general")  # student / worker / general
    wake_hour: Mapped[int] = mapped_column(Integer, default=7)
    sleep_hour: Mapped[int] = mapped_column(Integer, default=23)
    commute_minutes: Mapped[int] = mapped_column(Integer, default=30)

    # === 作息类型 ===
    # early_bird(早鸟型) / night_owl(夜猫型) / regular(规律型) / irregular(不规律型)
    chronotype: Mapped[str] = mapped_column(String(20), default="regular")

    # === 经济状况 ===
    monthly_income: Mapped[float] = mapped_column(Float, default=0)  # 月收入(元)
    # conservative(保守型) / moderate(稳健型) / aggressive(宽松型)
    spending_concept: Mapped[str] = mapped_column(String(20), default="moderate")

    # === 学习目标 ===
    study_goal: Mapped[str | None] = mapped_column(Text, nullable=True)  # 长期学习目标描述
    study_subject: Mapped[str | None] = mapped_column(String(100), nullable=True)  # 主要学习方向

    # === 居住环境 ===
    # studio(单间) / shared(合租) / apartment(整租) / house(自有住房)
    living_env: Mapped[str] = mapped_column(String(20), default="apartment")
    has_kitchen: Mapped[bool] = mapped_column(Boolean, default=True)  # 是否有厨房

    # === 沟通风格 (演化层学习) ===
    comm_style: Mapped[str] = mapped_column(String(20), default="balanced")
    tone: Mapped[str] = mapped_column(String(20), default="friendly")

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
