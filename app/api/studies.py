"""学习督导API（含知识点、错题、效率统计、动态调整）"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, get_current_user
from app.models.user import User
from app.models.study import StudyPlan, StudyRecord, KnowledgePoint, WrongQuestion
from app.services.behavior_collector import BehaviorCollector
from app.services.study_manager import StudyManager

router = APIRouter()


class StudyRecordCreate(BaseModel):
    subject: str
    duration_minutes: int
    focus_minutes: int | None = None
    accuracy: float | None = None
    efficiency: float | None = None
    content: str | None = None
    is_delayed: bool = False


class KnowledgePointCreate(BaseModel):
    subject: str
    title: str
    description: str | None = None


class WrongQuestionCreate(BaseModel):
    subject: str
    question: str
    correct_answer: str | None = None
    my_answer: str | None = None
    knowledge_point_id: int | None = None
    analysis: str | None = None


# ==================== 学习记录 ====================

@router.post("/records")
async def create_record(
    data: StudyRecordCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    manager = StudyManager(session, user.id)
    record = await manager.record_study(
        subject=data.subject, duration_minutes=data.duration_minutes,
        focus_minutes=data.focus_minutes, accuracy=data.accuracy,
        efficiency=data.efficiency, content=data.content,
    )

    # 行为采集
    collector = BehaviorCollector(session)
    await collector.log_study(
        user_id=user.id, subject=data.subject,
        duration_min=data.duration_minutes,
        accuracy=data.accuracy, focus_min=data.focus_minutes or data.duration_minutes,
        is_delayed=data.is_delayed,
    )

    await session.commit()
    return {"code": 0, "data": {"id": record.id}}


@router.get("/stats")
async def study_stats(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """学习统计"""
    result = await session.execute(
        select(
            StudyRecord.subject,
            func.sum(StudyRecord.duration_minutes).label("total_minutes"),
            func.sum(StudyRecord.focus_minutes).label("focus_minutes"),
            func.avg(StudyRecord.accuracy).label("avg_accuracy"),
            func.count().label("sessions"),
        ).where(StudyRecord.user_id == user.id).group_by(StudyRecord.subject)
    )
    rows = result.all()
    return {"code": 0, "data": [
        {"subject": r.subject, "total_minutes": r.total_minutes or 0,
         "focus_minutes": r.focus_minutes or 0,
         "avg_accuracy": round(r.avg_accuracy, 2) if r.avg_accuracy else None,
         "sessions": r.sessions}
        for r in rows
    ]}


# ==================== 知识点 ====================

@router.post("/knowledge")
async def add_knowledge(
    data: KnowledgePointCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """添加知识点"""
    manager = StudyManager(session, user.id)
    kp = await manager.add_knowledge_point(data.subject, data.title, data.description)
    await session.commit()
    return {"code": 0, "data": {"id": kp.id}}


@router.get("/knowledge")
async def list_knowledge(
    subject: str | None = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """获取知识点列表"""
    manager = StudyManager(session, user.id)
    items = await manager.get_knowledge_points(subject)
    return {"code": 0, "data": [
        {"id": kp.id, "subject": kp.subject, "title": kp.title,
         "mastery_level": kp.mastery_level, "accuracy_rate": kp.accuracy_rate,
         "review_count": kp.review_count}
        for kp in items
    ]}


@router.post("/knowledge/{kp_id}/review")
async def review_knowledge(
    kp_id: int,
    correct: bool = True,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """复习知识点"""
    manager = StudyManager(session, user.id)
    await manager.update_mastery(kp_id, correct)
    await session.commit()
    return {"code": 0}


# ==================== 错题 ====================

@router.post("/wrong-questions")
async def add_wrong_question(
    data: WrongQuestionCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """添加错题"""
    manager = StudyManager(session, user.id)
    wq = await manager.add_wrong_question(
        data.subject, data.question, data.correct_answer,
        data.my_answer, data.knowledge_point_id, data.analysis,
    )
    await session.commit()
    return {"code": 0, "data": {"id": wq.id}}


@router.get("/wrong-questions")
async def list_wrong_questions(
    subject: str | None = None,
    unmastered_only: bool = True,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """获取错题列表"""
    manager = StudyManager(session, user.id)
    items = await manager.get_wrong_questions(subject, unmastered_only)
    return {"code": 0, "data": [
        {"id": wq.id, "subject": wq.subject, "question": wq.question,
         "correct_answer": wq.correct_answer, "my_answer": wq.my_answer,
         "is_mastered": wq.is_mastered, "review_count": wq.review_count}
        for wq in items
    ]}


@router.post("/wrong-questions/{wq_id}/mastered")
async def mark_mastered(
    wq_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """标记错题已掌握"""
    manager = StudyManager(session, user.id)
    await manager.mark_mastered(wq_id)
    await session.commit()
    return {"code": 0}


# ==================== 动态推荐 ====================

@router.get("/daily-recommendation")
async def daily_recommendation(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """获取每日学习推荐（动态调整）"""
    manager = StudyManager(session, user.id)
    rec = await manager.get_daily_recommendation()
    return {"code": 0, "data": rec}


@router.get("/efficiency-report")
async def efficiency_report(
    days: int = 7,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """获取学习效率报告"""
    manager = StudyManager(session, user.id)
    report = await manager.get_efficiency_report(days)
    return {"code": 0, "data": report}
