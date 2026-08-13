"""出行模型（含开销预估、行李清单、天气联动）"""
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, Float, Text, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class TravelPlan(Base):
    """出行计划"""
    __tablename__ = "travel_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    title: Mapped[str] = mapped_column(String(200))
    travel_type: Mapped[str] = mapped_column(String(20), default="trip")  # commute / trip / flight / hotel

    origin: Mapped[str | None] = mapped_column(String(200), nullable=True)
    destination: Mapped[str | None] = mapped_column(String(200), nullable=True)

    depart_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    arrive_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # 票务信息
    ticket_no: Mapped[str | None] = mapped_column(String(50), nullable=True)
    carrier: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # 天气与路况风险
    weather_risk: Mapped[str | None] = mapped_column(String(20), nullable=True)  # low / medium / high
    weather_condition: Mapped[str | None] = mapped_column(String(50), nullable=True)  # sunny / rainy / snowy
    weather_temp: Mapped[float | None] = mapped_column(Float, nullable=True)  # 温度

    # 开销预估
    estimated_transport_cost: Mapped[float] = mapped_column(Float, default=0)  # 路费
    estimated_meal_cost: Mapped[float] = mapped_column(Float, default=0)  # 餐饮
    estimated_total_cost: Mapped[float] = mapped_column(Float, default=0)  # 总开销

    # 时间预估
    estimated_duration_min: Mapped[int] = mapped_column(Integer, default=0)  # 往返耗时(分钟)
    suggested_leave_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # 行李清单（JSON数组）
    packing_list: Mapped[list] = mapped_column(JSON, default=list)

    # 联动日程调整记录
    cleared_schedule_ids: Mapped[list] = mapped_column(JSON, default=list)  # 被清空的日程
    postponed_task_ids: Mapped[list] = mapped_column(JSON, default=list)  # 被顺延的任务

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
