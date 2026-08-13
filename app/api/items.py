"""物品收纳API"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schedules import _parse_dt

from app.api.deps import get_session, get_current_user
from app.models.item import Item
from app.models.user import User
from app.services.behavior_collector import BehaviorCollector

router = APIRouter()


class ItemCreate(BaseModel):
    name: str
    category: str
    location: str
    quantity: int = 1
    expire_at: datetime | None = None

    @field_validator("expire_at", mode="before")
    @classmethod
    def validate_expire(cls, v):
        if v is None or v == "":
            return None
        return _parse_dt(v)
    expire_remind_days: int = 7
    notes: str | None = None


@router.post("")
async def create_item(
    data: ItemCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    item = Item(
        user_id=user.id,
        name=data.name,
        category=data.category,
        location=data.location,
        quantity=data.quantity,
        expire_at=data.expire_at,
        expire_remind_days=data.expire_remind_days,
        notes=data.notes,
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
        {"id": i.id, "name": i.name, "category": i.category, "location": i.location,
         "expire_at": i.expire_at.isoformat() if i.expire_at else None,
         "is_idle": i.is_idle, "last_used_at": i.last_used_at.isoformat() if i.last_used_at else None}
        for i in items
    ]}


@router.get("/expiring")
async def expiring_items(
    days: int = 7,
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
        {"id": i.id, "name": i.name, "expire_at": i.expire_at.isoformat(),
         "days_left": (i.expire_at - datetime.utcnow()).days}
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
