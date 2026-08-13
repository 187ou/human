"""物品收纳API（含层级位置、双阶段预警、闲置识别、智能推荐）"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schedules import _parse_dt
from app.api.deps import get_session, get_current_user
from app.models.item import Item, StorageLocation, ItemIdleAlert
from app.models.user import User
from app.services.behavior_collector import BehaviorCollector
from app.services.item_manager import ItemManager

router = APIRouter()


class ItemCreate(BaseModel):
    name: str
    category: str
    location_path: str = ""  # 层级位置路径
    location_id: int | None = None
    quantity: int = 1
    expire_at: datetime | None = None
    expire_remind_days: int = 15
    second_remind_days: int = 7
    notes: str | None = None

    @field_validator("expire_at", mode="before")
    @classmethod
    def validate_expire(cls, v):
        if v is None or v == "":
            return None
        return _parse_dt(v)


class LocationCreate(BaseModel):
    house: str = "默认房屋"
    room: str = "默认房间"
    cabinet: str = "默认柜体"
    grid: str | None = None


# ==================== 层级位置 ====================

@router.post("/locations")
async def create_location(
    data: LocationCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """创建存储位置"""
    manager = ItemManager(session, user.id)
    loc = await manager.create_location(data.house, data.room, data.cabinet, data.grid)
    await session.commit()
    return {"code": 0, "data": {"id": loc.id, "full_path": loc.full_path}}


@router.get("/locations")
async def list_locations(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """获取所有存储位置"""
    manager = ItemManager(session, user.id)
    locations = await manager.get_locations()
    return {"code": 0, "data": [
        {"id": loc.id, "house": loc.house, "room": loc.room, "cabinet": loc.cabinet,
         "grid": loc.grid, "full_path": loc.full_path}
        for loc in locations
    ]}


@router.get("/search")
async def search_items(
    keyword: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """按位置搜索物品"""
    manager = ItemManager(session, user.id)
    items = await manager.search_by_location(keyword)
    return {"code": 0, "data": [
        {"id": i.id, "name": i.name, "category": i.category, "location_path": i.location_path,
         "expire_at": i.expire_at.isoformat() if i.expire_at else None, "is_idle": i.is_idle}
        for i in items
    ]}


# ==================== CRUD ====================

@router.post("")
async def create_item(
    data: ItemCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    item = Item(
        user_id=user.id, name=data.name, category=data.category,
        location_id=data.location_id, location_path=data.location_path,
        quantity=data.quantity, expire_at=data.expire_at,
        expire_remind_days=data.expire_remind_days,
        second_remind_days=data.second_remind_days, notes=data.notes,
    )
    session.add(item)
    await session.commit()
    return {"code": 0, "data": {"id": item.id}}


@router.get("")
async def list_items(
    keyword: str | None = None,
    category: str | None = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    stmt = select(Item).where(Item.user_id == user.id)
    if keyword:
        stmt = stmt.where(Item.name.contains(keyword))
    if category:
        stmt = stmt.where(Item.category == category)
    result = await session.execute(stmt.order_by(Item.updated_at.desc()))
    items = result.scalars().all()
    return {"code": 0, "data": [
        {"id": i.id, "name": i.name, "category": i.category, "location_path": i.location_path,
         "expire_at": i.expire_at.isoformat() if i.expire_at else None,
         "is_idle": i.is_idle, "recommendation": i.recommendation,
         "last_used_at": i.last_used_at.isoformat() if i.last_used_at else None}
        for i in items
    ]}


@router.post("/{item_id}/use")
async def use_item(
    item_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """标记物品使用"""
    stmt = select(Item).where(and_(Item.id == item_id, Item.user_id == user.id))
    result = await session.execute(stmt)
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="物品不存在")
    item.last_used_at = datetime.utcnow()
    item.use_count += 1
    item.is_idle = False

    collector = BehaviorCollector(session)
    await collector.log_item(user_id=user.id, item_id=item_id, action="use")
    await session.commit()
    return {"code": 0}


# ==================== 双阶段临期预警 ====================

@router.get("/alerts/expiration")
async def expiration_alerts(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """双阶段临期预警"""
    manager = ItemManager(session, user.id)
    alerts = await manager.check_expiration_alerts()
    await session.commit()
    return {"code": 0, "data": alerts}


@router.get("/expiring")
async def expiring_items(
    days: int = 15,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """即将过期物品"""
    cutoff = datetime.utcnow() + __import__("datetime").timedelta(days=days)
    result = await session.execute(
        select(Item).where(
            and_(
                Item.user_id == user.id,
                Item.expire_at <= cutoff,
                Item.expire_at >= datetime.utcnow(),
            )
        ).order_by(Item.expire_at)
    )
    items = result.scalars().all()
    return {"code": 0, "data": [
        {"id": i.id, "name": i.name, "category": i.category,
         "expire_at": i.expire_at.isoformat(),
         "days_left": (i.expire_at - datetime.utcnow()).days,
         "recommendation": i.recommendation}
        for i in items
    ]}


# ==================== 闲置识别 ====================

@router.post("/detect-idle")
async def detect_idle(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """检测闲置物品"""
    manager = ItemManager(session, user.id)
    alerts = await manager.detect_idle_items()
    await session.commit()
    return {"code": 0, "data": alerts}


@router.get("/alerts/idle")
async def idle_alerts(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """获取闲置提醒"""
    manager = ItemManager(session, user.id)
    alerts = await manager.get_idle_alerts()
    return {"code": 0, "data": [
        {"id": a.id, "item_id": a.item_id, "alert_type": a.alert_type,
         "message": a.message, "suggestion": a.suggestion}
        for a in alerts
    ]}


# ==================== 总览 ====================

@router.get("/summary")
async def item_summary(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """物品总览"""
    manager = ItemManager(session, user.id)
    summary = await manager.get_item_summary()
    return {"code": 0, "data": summary}
