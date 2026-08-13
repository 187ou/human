"""出行模型"""
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, Float, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class TravelPlan(Base):
    __tablename__ = "travel_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    title: Mapped[str] = mapped_column(String(200))
    # 类型：commute / trip / flight / hotel
    travel_type: Mapped[str] = mapped_column(String(20), default="trip")

    origin: Mapped[str | None] = mapped_column(String(200), nullable=True)
    destination: Mapped[str | None] = mapped_column(String(200), nullable=True)

    depart_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    arrive_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # 票务信息
    ticket_no: Mapped[str | None] = mapped_column(String(50), nullable=True)
    carrier: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # 天气与路况风险
    weather_risk: Mapped[str | None] = mapped_column(String(20), nullable=True)  # low / medium / high
    # 建议出门时间
    suggested_leave_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
