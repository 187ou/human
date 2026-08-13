"""出行API"""
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, field_validator
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schedules import _parse_dt

from app.api.deps import get_session, get_current_user
from app.models.travel import TravelPlan
from app.models.user import User
from app.services.behavior_collector import BehaviorCollector

router = APIRouter()


class TravelCreate(BaseModel):
    title: str
    travel_type: str = "trip"
    origin: str | None = None
    destination: str | None = None
    depart_time: datetime | None = None
    arrive_time: datetime | None = None

    @field_validator("depart_time", "arrive_time", mode="before")
    @classmethod
    def validate_datetime(cls, v):
        if v is None or v == "":
            return None
        return _parse_dt(v)
    ticket_no: str | None = None
    carrier: str | None = None
    notes: str | None = None


@router.post("")
async def create_travel(
    data: TravelCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    plan = TravelPlan(
        user_id=user.id,
        title=data.title,
        travel_type=data.travel_type,
        origin=data.origin,
        destination=data.destination,
        depart_time=data.depart_time,
        arrive_time=data.arrive_time,
        ticket_no=data.ticket_no,
        carrier=data.carrier,
        notes=data.notes,
    )
    session.add(plan)
    await session.commit()
    return {"code": 0, "data": {"id": plan.id}}


@router.get("")
async def list_travels(
    upcoming: bool = True,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    stmt = select(TravelPlan).where(TravelPlan.user_id == user.id)
    if upcoming:
        stmt = stmt.where(
            and_(TravelPlan.depart_time >= datetime.utcnow(), TravelPlan.is_completed == False)
        )
    result = await session.execute(stmt.order_by(TravelPlan.depart_time))
    items = result.scalars().all()
    return {"code": 0, "data": [
        {"id": t.id, "title": t.title, "type": t.travel_type, "destination": t.destination,
         "depart": t.depart_time.isoformat() if t.depart_time else None,
         "weather_risk": t.weather_risk}
        for t in items
    ]}


@router.post("/{travel_id}/complete")
async def complete_travel(
    travel_id: int,
    is_on_time: bool = True,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    stmt = select(TravelPlan).where(and_(TravelPlan.id == travel_id, TravelPlan.user_id == user.id))
    result = await session.execute(stmt)
    plan = result.scalar_one_or_none()
    if not plan:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="出行计划不存在")
    plan.is_completed = True
    collector = BehaviorCollector(session)
    await collector.log_travel(user_id=user.id, travel_id=travel_id, is_on_time=is_on_time)

    await session.commit()
    return {"code": 0}
