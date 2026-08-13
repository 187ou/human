"""物品收纳模型（含层级位置、双阶段预警、闲置识别）"""
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, Boolean, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class StorageLocation(Base):
    """层级存储位置（房屋→房间→柜体→格子）"""
    __tablename__ = "storage_locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # 层级路径
    house: Mapped[str] = mapped_column(String(100), default="默认房屋")  # 房屋
    room: Mapped[str] = mapped_column(String(100), default="默认房间")  # 房间
    cabinet: Mapped[str] = mapped_column(String(100), default="默认柜体")  # 柜体/架子
    grid: Mapped[str | None] = mapped_column(String(100), nullable=True)  # 格子/层

    # 完整路径（自动生成）
    full_path: Mapped[str] = mapped_column(String(300))

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Item(Base):
    """物品"""
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(50))  # food / cosmetic / medicine / card / coupon / document / other

    # 层级位置
    location_id: Mapped[int | None] = mapped_column(ForeignKey("storage_locations.id", ondelete="SET NULL"), nullable=True)
    location_path: Mapped[str] = mapped_column(String(300), default="")  # 冗余存储完整路径

    quantity: Mapped[int] = mapped_column(Integer, default=1)

    # 过期相关
    expire_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expire_remind_days: Mapped[int] = mapped_column(Integer, default=15)  # 初次提醒天数
    second_remind_days: Mapped[int] = mapped_column(Integer, default=7)  # 二次提醒天数
    first_alert_sent: Mapped[bool] = mapped_column(Boolean, default=False)  # 初次提醒已发送
    second_alert_sent: Mapped[bool] = mapped_column(Boolean, default=False)  # 二次提醒已发送

    # 使用追踪
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    use_count: Mapped[int] = mapped_column(Integer, default=0)
    is_idle: Mapped[bool] = mapped_column(Boolean, default=False)
    idle_days_threshold: Mapped[int] = mapped_column(Integer, default=90)  # 90天未用=闲置

    # AI推荐
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)  # 消耗食谱/使用规划
    recommendation_type: Mapped[str | None] = mapped_column(String(20), nullable=True)  # recipe / usage_plan / dispose

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ItemIdleAlert(Base):
    """闲置物品提醒"""
    __tablename__ = "item_idle_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"))
    alert_type: Mapped[str] = mapped_column(String(20))  # idle / duplicate_hoarding
    message: Mapped[str] = mapped_column(Text)
    suggestion: Mapped[str] = mapped_column(Text)  # 清理/转手/丢弃建议
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
