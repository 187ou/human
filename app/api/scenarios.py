"""跨Agent场景联动API"""
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, get_current_user
from app.models.user import User
from app.services.cross_agent import CrossAgentOrchestrator

router = APIRouter()


class TripScenarioRequest(BaseModel):
    destination: str
    depart_time: datetime
    arrive_time: datetime
    budget: float | None = None


class ExamScenarioRequest(BaseModel):
    subject: str
    exam_date: str
    daily_hours: int = 6


class SickScenarioRequest(BaseModel):
    rest_days: int = 3
    symptoms: str | None = None


@router.post("/trip")
async def trip_scenario(
    data: TripScenarioRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """场景1：短途出游联动"""
    orchestrator = CrossAgentOrchestrator(session, user.id)
    result = await orchestrator.trip_linkage(
        destination=data.destination,
        depart_time=data.depart_time,
        arrive_time=data.arrive_time,
        budget=data.budget,
    )
    return {"code": 0, "data": result}


@router.post("/exam-prep")
async def exam_scenario(
    data: ExamScenarioRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """场景2：备考冲刺联动"""
    orchestrator = CrossAgentOrchestrator(session, user.id)
    result = await orchestrator.exam_prep_linkage(
        subject=data.subject,
        exam_date=data.exam_date,
        daily_hours=data.daily_hours,
    )
    return {"code": 0, "data": result}


@router.post("/sick-rest")
async def sick_scenario(
    data: SickScenarioRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """场景3：生病休养联动"""
    orchestrator = CrossAgentOrchestrator(session, user.id)
    result = await orchestrator.sick_rest_linkage(
        rest_days=data.rest_days,
        symptoms=data.symptoms,
    )
    return {"code": 0, "data": result}
