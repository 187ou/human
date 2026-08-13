"""高级智能能力API"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, get_current_user
from app.models.user import User
from sqlalchemy import select, and_, func, Integer
from app.services.hidden_habit_miner import HiddenHabitMiner
from app.services.stability_keeper import StabilityKeeper
from app.services.prompt_evolver import PromptEvolver
from app.services.negative_learner import NegativeLearner

router = APIRouter()


# ==================== 隐性习惯挖掘 ====================

@router.post("/mine-habits")
async def mine_hidden_habits(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """挖掘隐性习惯"""
    miner = HiddenHabitMiner(session, user.id)
    findings = await miner.mine_hidden_habits()
    await session.commit()
    return {"code": 0, "data": {"found": len(findings), "habits": findings}}


@router.get("/hidden-habits")
async def get_hidden_habits(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """获取隐性习惯"""
    from app.models.advanced import HiddenHabit
    result = await session.execute(
        select(HiddenHabit).where(and_(
            HiddenHabit.user_id == user.id,
            HiddenHabit.is_active == True,
        )).order_by(HiddenHabit.confidence.desc())
    )
    habits = result.scalars().all()
    return {"code": 0, "data": [
        {"id": h.id, "type": h.habit_type, "name": h.name, "description": h.description,
         "confidence": h.confidence, "effect": h.effect_description}
        for h in habits
    ]}


# ==================== 任务难度缩放 ====================

@router.post("/adjust-difficulty")
async def adjust_difficulty(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """任务难度自适应缩放"""
    keeper = StabilityKeeper(session, user.id)
    result = await keeper.adjust_task_difficulty()
    await session.commit()
    return {"code": 0, "data": result}


# ==================== 生活稳态维持 ====================

@router.post("/stability-check")
async def stability_check(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """稳态检查与干预"""
    keeper = StabilityKeeper(session, user.id)
    result = await keeper.check_and_intervene()
    await session.commit()
    return {"code": 0, "data": result}


# ==================== 个性化Prompt ====================

@router.get("/prompts")
async def get_personal_prompts(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """获取个性化Prompt"""
    evolver = PromptEvolver(session, user.id)
    prompts = await evolver.get_all_active_prompts()
    return {"code": 0, "data": {
        agent: {"prompt": p.system_prompt, "version": p.version, "score": p.performance_score}
        for agent, p in prompts.items()
    }}


# ==================== 负反馈学习 ====================

class FeedbackRequest(BaseModel):
    feedback_type: str
    dimension: str
    description: str
    severity: int = 5


@router.post("/record-feedback")
async def record_feedback(
    data: FeedbackRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """记录负反馈"""
    learner = NegativeLearner(session, user.id)
    fb = await learner.record_feedback(data.feedback_type, data.dimension, data.description, data.severity)
    await session.commit()
    return {"code": 0, "data": {"id": fb.id}}


@router.get("/weakness-profile")
async def weakness_profile(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """获取短板画像"""
    learner = NegativeLearner(session, user.id)
    profile = await learner.get_weakness_profile()
    return {"code": 0, "data": profile}
