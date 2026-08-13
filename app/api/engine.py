"""底层架构API：分层闭环自演化引擎"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, get_current_user
from app.models.user import User
from app.services.evolution_engine import EvolutionEngine
from app.services.meta_agent import MetaEvolutionAgent

router = APIRouter()


# ==================== 三层演化 ====================

class OnlineEvent(BaseModel):
    event_type: str  # task_completed / task_failed / task_delayed
    event_data: dict


@router.post("/online-reflection")
async def online_reflection(
    data: OnlineEvent,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """在线即时反射"""
    engine = EvolutionEngine(session, user.id)
    result = await engine.online_reflection(data.event_type, data.event_data)
    await session.commit()
    return {"code": 0, "data": result}


@router.post("/nightly-evolution")
async def nightly_evolution(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """夜间轻量化演化"""
    engine = EvolutionEngine(session, user.id)
    result = await engine.nightly_evolution()
    await session.commit()
    return {"code": 0, "data": result}


@router.post("/weekly-evolution")
async def weekly_evolution(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """周度全局深度演化"""
    engine = EvolutionEngine(session, user.id)
    result = await engine.weekly_evolution()
    await session.commit()
    return {"code": 0, "data": result}


# ==================== 快照管理 ====================

@router.get("/snapshots")
async def list_snapshots(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """获取快照列表"""
    from app.models.engine import GitSnapshot
    from sqlalchemy import select, and_
    result = await session.execute(
        select(GitSnapshot).where(GitSnapshot.user_id == user.id).order_by(GitSnapshot.created_at.desc()).limit(20)
    )
    snapshots = result.scalars().all()
    return {"code": 0, "data": [
        {"hash": s.commit_hash, "message": s.message, "rules_count": len(s.rules_snapshot),
         "changes": s.changes_count, "created_at": s.created_at.isoformat()}
        for s in snapshots
    ]}


# ==================== 元演化调控 ====================

@router.post("/meta-evaluate")
async def meta_evaluate(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """元演化评估与调控"""
    agent = MetaEvolutionAgent(session, user.id)
    result = await agent.evaluate_and_adjust()
    return {"code": 0, "data": result}


@router.get("/meta-state")
async def meta_state(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """获取元演化状态"""
    from app.models.engine import MetaEvolutionState
    from sqlalchemy import select, and_
    result = await session.execute(
        select(MetaEvolutionState).where(MetaEvolutionState.user_id == user.id)
    )
    state = result.scalar_one_or_none()
    if not state:
        return {"code": 0, "data": {"phase": "initial", "speed": "normal"}}
    return {"code": 0, "data": {
        "phase": state.current_phase,
        "speed": state.evolution_speed,
        "convergence": state.convergence_score,
        "stagnation": state.stagnation_counter,
        "exploration_rate": state.exploration_rate,
        "last_decision": state.last_decision,
    }}
