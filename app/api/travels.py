"""出行处理API（含开销预估、行李清单、日程联动、天气提醒）"""
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, field_validator
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schedules import _parse_dt
from app.api.deps import get_session, get_current_user
from app.models.user import User
from app.models.travel import TravelPlan
from app.services.travel_planner import TravelPlanner

router = APIRouter()


class TravelCreate(BaseModel):
    title: str
    travel_type: str = "trip"
    origin: str | None = None
    destination: str | None = None
    depart_time: datetime
    arrive_time: datetime | None = None
    notes: str | None = None

    @field_validator("depart_time", "arrive_time", mode="before")
    @classmethod
    def validate_datetime(cls, v):
        if v is None or v == "":
            return None
        return _parse_dt(v)


# ==================== CRUD ====================

@router.post("")
async def create_travel(
    data: TravelCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """创建出行计划（含开销预估、行李清单、日程联动）"""
    planner = TravelPlanner(session, user.id)
    result = await planner.create_travel_plan(
        title=data.title, travel_type=data.travel_type,
        destination=data.destination, depart_time=data.depart_time,
        arrive_time=data.arrive_time, origin=data.origin, notes=data.notes,
    )
    await session.commit()
    return {"code": 0, "data": result}


@router.get("")
async def list_travels(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    stmt = select(TravelPlan).where(TravelPlan.user_id == user.id).order_by(TravelPlan.depart_time)
    result = await session.execute(stmt)
    items = result.scalars().all()
    return {"code": 0, "data": [
        {"id": t.id, "title": t.title, "type": t.travel_type,
         "destination": t.destination, "depart": t.depart_time.isoformat() if t.depart_time else None,
         "arrive": t.arrive_time.isoformat() if t.arrive_time else None,
         "estimated_cost": t.estimated_total_cost, "weather_risk": t.weather_risk,
         "is_completed": t.is_completed}
        for t in items
    ]}


@router.post("/{travel_id}/complete")
async def complete_travel(
    travel_id: int,
    is_on_time: bool = True,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """完成出行"""
    plan = await session.get(TravelPlan, travel_id)
    if not plan or plan.user_id != user.id:
        return {"code": 1, "message": "出行计划不存在"}
    plan.is_completed = True
    await session.commit()
    return {"code": 0}


# ==================== 功能接口 ====================

@router.get("/estimate-cost")
async def estimate_cost(
    travel_type: str = "trip",
    destination: str | None = None,
    days: int = 1,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """预估开销"""
    planner = TravelPlanner(session, user.id)
    costs = await planner.estimate_costs(travel_type, destination, days)
    return {"code": 0, "data": costs}


@router.get("/packing-list")
async def packing_list(
    days: int = 1,
    weather: str | None = None,
    temp: float | None = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """生成行李清单"""
    planner = TravelPlanner(session, user.id)
    packing = await planner.generate_packing_list(days, weather, temp)
    return {"code": 0, "data": packing}


@router.get("/weather-check")
async def weather_check(
    destination: str | None = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """天气检查"""
    planner = TravelPlanner(session, user.id)
    weather = await planner.check_weather_risk(destination)
    return {"code": 0, "data": weather}
