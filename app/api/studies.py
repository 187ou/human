"""学习督导API"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, get_current_user
from app.models.study import StudyPlan, StudyRecord
from app.models.user import User
from app.services.behavior_collector import BehaviorCollector

router = APIRouter()


class PlanCreate(BaseModel):
    title: str
    subject: str
    target_description: str | None = None
    difficulty: int = 5
    estimated_hours: float = 1.0


@router.post("/plans")
async def create_plan(
    data: PlanCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    plan = StudyPlan(
        user_id=user.id,
        title=data.title,
        subject=data.subject,
        target_description=data.target_description,
        difficulty=data.difficulty,
        estimated_hours=data.estimated_hours,
    )
    session.add(plan)
    await session.commit()
    return {"code": 0, "data": {"id": plan.id}}


@router.get("/plans")
async def list_plans(
    status: str | None = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    stmt = select(StudyPlan).where(StudyPlan.user_id == user.id)
    if status:
        stmt = stmt.where(StudyPlan.status == status)
    result = await session.execute(stmt.order_by(StudyPlan.created_at.desc()))
    plans = result.scalars().all()
    return {"code": 0, "data": [
        {"id": p.id, "title": p.title, "subject": p.subject, "difficulty": p.difficulty, "status": p.status}
        for p in plans
    ]}


class RecordCreate(BaseModel):
    subject: str
    content: str | None = None
    plan_id: int | None = None
    duration_minutes: int
    efficiency: float | None = None
    is_delayed: bool = False
    quality: int | None = None


@router.post("/records")
async def create_record(
    data: RecordCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    record = StudyRecord(
        user_id=user.id,
        plan_id=data.plan_id,
        subject=data.subject,
        content=data.content,
        start_time=datetime.utcnow(),
        end_time=datetime.utcnow(),
        duration_minutes=data.duration_minutes,
        efficiency=data.efficiency,
        is_delayed=data.is_delayed,
        quality=data.quality,
    )
    session.add(record)

    collector = BehaviorCollector(session)
    await collector.log_study(
        user_id=user.id, subject=data.subject,
        duration_min=data.duration_minutes,
        accuracy=data.efficiency,
        focus_min=data.duration_minutes,
        is_delayed=data.is_delayed,
    )
    await session.commit()
    return {"code": 0, "data": {"id": record.id}}


@router.get("/stats")
async def study_stats(
    days: int = 7,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """学习统计"""
    cutoff = datetime.utcnow() - __import__("datetime").timedelta(days=days)
    result = await session.execute(
        select(
            StudyRecord.subject,
            func.sum(StudyRecord.duration_minutes).label("total_min"),
            func.count().label("sessions"),
        ).where(
            and_(StudyRecord.user_id == user.id, StudyRecord.created_at >= cutoff)
        ).group_by(StudyRecord.subject)
    )
    rows = result.all()
    return {"code": 0, "data": [
        {"subject": r.subject, "total_minutes": r.total_min, "sessions": r.sessions}
        for r in rows
    ]}
