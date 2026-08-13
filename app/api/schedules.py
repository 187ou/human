"""时间规划API"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, get_current_user
from app.models.schedule import Schedule, ScheduleItem
from app.models.user import User
from app.services.behavior_collector import BehaviorCollector

router = APIRouter()


def _parse_dt(v):
    """支持空格或T分隔的datetime"""
    try:
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace(" ", "T"))
        return v
    except Exception:
        return v


class ScheduleCreate(BaseModel):
    title: str
    category: str = "other"
    start_time: datetime
    end_time: datetime
    location: str | None = None
    description: str | None = None
    source: str = "manual"

    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def validate_datetime(cls, v):
        return _parse_dt(v)


class ScheduleComplete(BaseModel):
    quality: float = 1.0  # 完成质量 0-1
    duration_min: int = 0
    is_delayed: bool = False


@router.post("")
async def create_schedule(
    data: ScheduleCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    schedule = Schedule(
        user_id=user.id,
        title=data.title,
        category=data.category,
        start_time=data.start_time,
        end_time=data.end_time,
        location=data.location,
        description=data.description,
        source=data.source,
    )
    session.add(schedule)
    await session.commit()
    return {"code": 0, "data": {"id": schedule.id}}


@router.get("")
async def list_schedules(
    date: str | None = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    stmt = select(Schedule).where(Schedule.user_id == user.id)
    if date:
        day = datetime.strptime(date, "%Y-%m-%d")
        stmt = stmt.where(
            and_(Schedule.start_time >= day, Schedule.start_time < day.replace(day=day.day + 1))
        )
    result = await session.execute(stmt.order_by(Schedule.start_time))
    items = result.scalars().all()
    return {"code": 0, "data": [
        {"id": s.id, "title": s.title, "start": s.start_time.isoformat(), "end": s.end_time.isoformat(),
         "category": s.category, "is_completed": s.is_completed}
        for s in items
    ]}


@router.post("/{schedule_id}/complete")
async def complete_schedule(
    schedule_id: int,
    data: ScheduleComplete,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    stmt = select(Schedule).where(and_(Schedule.id == schedule_id, Schedule.user_id == user.id))
    result = await session.execute(stmt)
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail="日程不存在")
    schedule.is_completed = True
    schedule.completion_quality = data.quality

    # 行为采集（含结果反馈）
    collector = BehaviorCollector(session)
    await collector.log_schedule(
        user_id=user.id, schedule_id=schedule_id,
        completed=True, duration_min=data.duration_min,
        self_rating=int(data.quality * 5) if data.quality else None,
        is_delayed=data.is_delayed,
    )
    await session.commit()
    return {"code": 0, "message": "已完成，行为已记录"}


# ---- 碎片任务 ----

class ItemCreate(BaseModel):
    title: str
    estimated_minutes: int = 15
    priority: int = 5
    slot_type: str = "fragment"


@router.post("/items")
async def create_item(
    data: ItemCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    item = ScheduleItem(
        user_id=user.id,
        title=data.title,
        estimated_minutes=data.estimated_minutes,
        priority=data.priority,
        slot_type=data.slot_type,
    )
    session.add(item)
    await session.commit()
    return {"code": 0, "data": {"id": item.id}}


@router.get("/items")
async def list_items(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    result = await session.execute(
        select(ScheduleItem).where(
            and_(ScheduleItem.user_id == user.id, ScheduleItem.is_done == False)
        ).order_by(ScheduleItem.priority.desc())
    )
    items = result.scalars().all()
    return {"code": 0, "data": [
        {"id": i.id, "title": i.title, "minutes": i.estimated_minutes, "priority": i.priority}
        for i in items
    ]}
