"""时间规划API（含冲突检测、突发场景、例外日程、熬夜适配）"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, get_current_user
from app.models.schedule import Schedule, ScheduleItem, RecurringException
from app.models.user import User
from app.services.behavior_collector import BehaviorCollector
from app.services.schedule_planner import SchedulePlanner

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
    quality: float = 1.0
    duration_min: int = 0
    is_delayed: bool = False


class RecurringExceptionCreate(BaseModel):
    title: str
    description: str | None = None
    rule_expr: dict
    effective_from: datetime
    effective_until: datetime | None = None

    @field_validator("effective_from", "effective_until", mode="before")
    @classmethod
    def validate_dates(cls, v):
        if v is None or v == "":
            return None
        return _parse_dt(v)


# ==================== CRUD ====================

@router.post("")
async def create_schedule(
    data: ScheduleCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    schedule = Schedule(
        user_id=user.id, title=data.title, category=data.category,
        start_time=data.start_time, end_time=data.end_time,
        location=data.location, description=data.description, source=data.source,
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
        stmt = stmt.where(and_(Schedule.start_time >= day, Schedule.start_time < day.replace(day=day.day + 1)))
    result = await session.execute(stmt.order_by(Schedule.start_time))
    items = result.scalars().all()
    return {"code": 0, "data": [
        {"id": s.id, "title": s.title, "start": s.start_time.isoformat(), "end": s.end_time.isoformat(),
         "category": s.category, "is_completed": s.is_completed, "is_paused": s.is_paused}
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

    collector = BehaviorCollector(session)
    await collector.log_schedule(
        user_id=user.id, schedule_id=schedule_id,
        completed=True, duration_min=data.duration_min,
        self_rating=int(data.quality) if data.quality > 1 else int(data.quality * 5),
        is_delayed=data.is_delayed,
    )
    await session.commit()
    return {"code": 0, "message": "已完成，行为已记录"}


# ==================== 冲突检测 ====================

@router.get("/conflicts")
async def detect_conflicts(
    date: str | None = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """检测日程时间重叠冲突"""
    target = datetime.strptime(date, "%Y-%m-%d") if date else None
    planner = SchedulePlanner(session, user.id)
    conflicts = await planner.detect_conflicts(target)
    return {"code": 0, "data": conflicts}


@router.get("/fragment-slots")
async def fragment_slots(
    date: str | None = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """获取碎片时间挪位方案"""
    target = datetime.strptime(date, "%Y-%m-%d") if date else None
    planner = SchedulePlanner(session, user.id)
    slots = await planner.suggest_fragment_slots(target)
    return {"code": 0, "data": slots}


# ==================== 突发场景 ====================

@router.post("/emergency/pause")
async def emergency_pause(
    reason: str = "general",
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """一键暂停所有未来日程"""
    planner = SchedulePlanner(session, user.id)
    result = await planner.emergency_pause(reason)
    return {"code": 0, "data": result}


@router.post("/emergency/postpone")
async def emergency_postpone(
    delay_hours: int = 2,
    reason: str = "general",
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """一键顺延所有未来日程"""
    planner = SchedulePlanner(session, user.id)
    result = await planner.emergency_postpone(delay_hours, reason)
    return {"code": 0, "data": result}


@router.post("/emergency/resume")
async def emergency_resume(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """恢复所有暂停的日程"""
    planner = SchedulePlanner(session, user.id)
    result = await planner.resume_all()
    return {"code": 0, "data": result}


# ==================== 周期性例外 ====================

@router.post("/exceptions")
async def add_exception(
    data: RecurringExceptionCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """添加周期性例外日程"""
    planner = SchedulePlanner(session, user.id)
    exc = await planner.add_recurring_exception(
        title=data.title, description=data.description, rule_expr=data.rule_expr,
        effective_from=data.effective_from, effective_until=data.effective_until,
    )
    await session.commit()
    return {"code": 0, "data": {"id": exc.id}}


@router.get("/exceptions")
async def list_exceptions(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """获取周期性例外列表"""
    result = await session.execute(
        select(RecurringException).where(
            and_(RecurringException.user_id == user.id, RecurringException.is_active == True)
        )
    )
    items = result.scalars().all()
    return {"code": 0, "data": [
        {"id": e.id, "title": e.title, "description": e.description, "rule_expr": e.rule_expr,
         "effective_from": e.effective_from.isoformat(), "effective_until": e.effective_until.isoformat() if e.effective_until else None}
        for e in items
    ]}


@router.get("/exceptions/apply")
async def apply_exceptions(
    date: str | None = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """应用周期性例外"""
    target = datetime.strptime(date, "%Y-%m-%d") if date else None
    planner = SchedulePlanner(session, user.id)
    applied = await planner.apply_recurring_exceptions(target)
    return {"code": 0, "data": applied}


# ==================== 熬夜检测 ====================

@router.get("/late-night")
async def detect_late_night(
    date: str | None = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """检测熬夜情况"""
    target = datetime.strptime(date, "%Y-%m-%d") if date else None
    planner = SchedulePlanner(session, user.id)
    result = await planner.detect_late_night(target)
    return {"code": 0, "data": result}


@router.get("/adjusted-load")
async def adjusted_load(
    date: str | None = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """获取调整后的任务负荷"""
    target = datetime.strptime(date, "%Y-%m-%d") if date else None
    planner = SchedulePlanner(session, user.id)
    result = await planner.get_adjusted_task_load(target)
    return {"code": 0, "data": result}


# ==================== 碎片任务 ====================

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
        user_id=user.id, title=data.title, estimated_minutes=data.estimated_minutes,
        priority=data.priority, slot_type=data.slot_type,
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
