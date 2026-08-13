"""用户画像API"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, get_current_user
from app.models.user import User
from app.services.log_archiver import LogArchiver

router = APIRouter()


class ProfileUpdate(BaseModel):
    chronotype: str | None = None
    commute_minutes: int | None = None
    monthly_income: float | None = None
    spending_concept: str | None = None
    study_goal: str | None = None
    study_subject: str | None = None
    living_env: str | None = None
    has_kitchen: bool | None = None
    wake_hour: int | None = None
    sleep_hour: int | None = None


@router.get("/")
async def get_profile(user: User = Depends(get_current_user)):
    """获取完整用户画像"""
    return {"code": 0, "data": {
        "id": user.id,
        "username": user.username,
        "user_type": user.user_type,
        "chronotype": user.chronotype,
        "wake_hour": user.wake_hour,
        "sleep_hour": user.sleep_hour,
        "commute_minutes": user.commute_minutes,
        "monthly_income": user.monthly_income,
        "spending_concept": user.spending_concept,
        "study_goal": user.study_goal,
        "study_subject": user.study_subject,
        "living_env": user.living_env,
        "has_kitchen": user.has_kitchen,
        "comm_style": user.comm_style,
        "tone": user.tone,
    }}


@router.put("/")
async def update_profile(
    data: ProfileUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """更新用户画像"""
    if data.chronotype is not None:
        user.chronotype = data.chronotype
    if data.commute_minutes is not None:
        user.commute_minutes = max(0, min(180, data.commute_minutes))
    if data.monthly_income is not None:
        user.monthly_income = max(0, data.monthly_income)
    if data.spending_concept is not None:
        user.spending_concept = data.spending_concept
    if data.study_goal is not None:
        user.study_goal = data.study_goal
    if data.study_subject is not None:
        user.study_subject = data.study_subject
    if data.living_env is not None:
        user.living_env = data.living_env
    if data.has_kitchen is not None:
        user.has_kitchen = data.has_kitchen
    if data.wake_hour is not None:
        user.wake_hour = max(0, min(23, data.wake_hour))
    if data.sleep_hour is not None:
        user.sleep_hour = max(0, min(23, data.sleep_hour))

    await session.commit()
    return {"code": 0, "message": "ok"}


@router.post("/init")
async def init_profile(
    data: ProfileUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """初始化用户画像（首次设置）"""
    if data.chronotype:
        user.chronotype = data.chronotype
    if data.commute_minutes is not None:
        user.commute_minutes = data.commute_minutes
    if data.monthly_income is not None:
        user.monthly_income = data.monthly_income
    if data.spending_concept:
        user.spending_concept = data.spending_concept
    if data.study_goal:
        user.study_goal = data.study_goal
    if data.study_subject:
        user.study_subject = data.study_subject
    if data.living_env:
        user.living_env = data.living_env
    if data.has_kitchen is not None:
        user.has_kitchen = data.has_kitchen
    if data.wake_hour is not None:
        user.wake_hour = data.wake_hour
    if data.sleep_hour is not None:
        user.sleep_hour = data.sleep_hour

    await session.commit()
    return {"code": 0, "message": "profile initialized"}


@router.get("/log-stats")
async def log_storage_stats(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """获取日志存储统计"""
    archiver = LogArchiver(session, user.id)
    stats = await archiver.get_storage_stats()
    return {"code": 0, "data": stats}


@router.post("/archive-logs")
async def archive_logs(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """手动触发日志归档"""
    archiver = LogArchiver(session, user.id)
    result = await archiver.archive_cold_logs()
    await session.commit()
    return {"code": 0, "data": result}


@router.get("/log-hot")
async def get_hot_logs(
    dimension: str | None = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """获取热数据（近90天）"""
    archiver = LogArchiver(session, user.id)
    logs = await archiver.get_hot_logs(dimension)
    return {"code": 0, "data": [
        {"id": l.id, "dimension": l.dimension, "event_type": l.event_type,
         "value": l.value, "created_at": l.created_at.isoformat()}
        for l in logs[:50]
    ]}
