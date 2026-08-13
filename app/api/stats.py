"""Dashboard数据统计API"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, get_current_user
from app.models.user import User
from app.models.schedule import Schedule
from app.models.consume import ConsumeRecord
from app.models.study import StudyRecord
from app.models.travel import TravelPlan
from app.models.item import Item

router = APIRouter()


@router.get("/dashboard")
async def dashboard(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Dashboard综合统计"""
    now = datetime.utcnow()
    month_str = now.strftime("%Y-%m")
    weekday = now.weekday()
    start_of_week = now - timedelta(days=weekday)

    # 本月消费总额
    r = await session.execute(
        select(func.sum(ConsumeRecord.amount)).where(
            and_(ConsumeRecord.user_id == user.id, ConsumeRecord.occurred_at.like(f"{month_str}%"))
        )
    )
    month_consume = r.scalar() or 0

    # 本周学习总时长
    r = await session.execute(
        select(func.sum(StudyRecord.duration_minutes)).where(
            and_(StudyRecord.user_id == user.id, StudyRecord.created_at >= start_of_week)
        )
    )
    week_study_min = r.scalar() or 0

    # 待办日程数
    r = await session.execute(
        select(func.count(Schedule.id)).where(
            and_(Schedule.user_id == user.id, Schedule.is_completed == False, Schedule.start_time >= now)
        )
    )
    upcoming_schedules = r.scalar() or 0

    # 即将过期物品
    r = await session.execute(
        select(func.count(Item.id)).where(
            and_(
                Item.user_id == user.id,
                Item.expire_at >= now,
                Item.expire_at <= now + timedelta(days=7),
            )
        )
    )
    expiring_items = r.scalar() or 0

    # 本月消费趋势（按日）
    r = await session.execute(
        select(
            func.date(ConsumeRecord.occurred_at).label("day"),
            func.sum(ConsumeRecord.amount),
        ).where(
            and_(ConsumeRecord.user_id == user.id, ConsumeRecord.occurred_at.like(f"{month_str}%"))
        ).group_by(func.date(ConsumeRecord.occurred_at))
    )
    daily_consume = [{"day": str(row[0]), "total": float(row[1])} for row in r.all()]

    # 学习科目分布
    r = await session.execute(
        select(StudyRecord.subject, func.sum(StudyRecord.duration_minutes)).where(
            StudyRecord.user_id == user.id
        ).group_by(StudyRecord.subject)
    )
    study_subjects = [{"subject": row[0], "minutes": row[1]} for row in r.all()]

    # 消费品类分布
    r = await session.execute(
        select(ConsumeRecord.category, func.sum(ConsumeRecord.amount)).where(
            and_(ConsumeRecord.user_id == user.id, ConsumeRecord.occurred_at.like(f"{month_str}%"))
        ).group_by(ConsumeRecord.category)
    )
    consume_categories = [{"category": row[0], "total": float(row[1])} for row in r.all()]

    # 近7天活跃天数
    r = await session.execute(
        select(func.date(Schedule.created_at)).where(
            and_(Schedule.user_id == user.id, Schedule.created_at >= now - timedelta(days=7))
        )
    )
    active_days = len(set(str(row[0]) for row in r.all()))

    return {
        "code": 0,
        "data": {
            "month_consume": float(month_consume),
            "week_study_hours": round(week_study_min / 60, 1),
            "upcoming_schedules": upcoming_schedules,
            "expiring_items": expiring_items,
            "active_days": active_days,
            "daily_consume": daily_consume,
            "study_subjects": study_subjects,
            "consume_categories": consume_categories,
        },
    }
