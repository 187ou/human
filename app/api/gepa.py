"""GEPA Prompt进化API"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, get_current_user
from app.models.user import User
from app.services.gepa import GEPAEvolver

router = APIRouter()


@router.post("/evolve/{agent_type}")
async def evolve_prompt(
    agent_type: str,
    trajectory: dict | None = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """执行GEPA进化"""
    evolver = GEPAEvolver(session, user.id)
    result = await evolver.evolve(agent_type, trajectory)
    await session.commit()
    return {"code": 0, "data": result}


@router.get("/best-prompt/{agent_type}")
async def best_prompt(
    agent_type: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """获取最优Prompt"""
    evolver = GEPAEvolver(session, user.id)
    prompt = await evolver.get_best_prompt(agent_type)
    return {"code": 0, "data": {"prompt": prompt}}


@router.get("/population/{agent_type}")
async def population(
    agent_type: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """获取种群"""
    from app.models.gepa import PromptVariant
    from sqlalchemy import select, and_
    result = await session.execute(
        select(PromptVariant).where(and_(
            PromptVariant.user_id == user.id,
            PromptVariant.agent_type == agent_type,
        )).order_by(PromptVariant.fitness_score.desc())
    )
    variants = result.scalars().all()
    return {"code": 0, "data": [
        {"id": v.id, "fitness": round(v.fitness_score, 3), "pareto_rank": v.pareto_rank,
         "completion": round(v.completion_score, 2), "conciseness": round(v.conciseness_score, 2),
         "empathy": round(v.empathy_score, 2), "accuracy": round(v.accuracy_score, 2),
         "origin": v.origin, "generation": v.generation,
         "prompt": v.prompt_content[:80] + "..."}
        for v in variants
    ]}


@router.post("/evolve-all")
async def evolve_all(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """进化所有Agent的Prompt"""
    evolver = GEPAEvolver(session, user.id)
    results = {}
    for agent_type in ["time_plan", "consume", "study", "travel", "item"]:
        result = await evolver.evolve(agent_type)
        results[agent_type] = result
    await session.commit()
    return {"code": 0, "data": results}
