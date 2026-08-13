"""生活稳态维持API"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, get_current_user
from app.models.user import User
from app.services.stability_objective import StabilityObjectiveFunction

router = APIRouter()


@router.post("/evaluate")
async def evaluate_stability(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """评估稳态并执行干预"""
    func = StabilityObjectiveFunction(session, user.id)
    result = await func.evaluate_and_intervene()
    await session.commit()
    return {"code": 0, "data": result}


@router.get("/interventions")
async def intervention_history(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """获取干预历史"""
    from app.models.stability import StabilityIntervention
    from sqlalchemy import select, and_
    result = await session.execute(
        select(StabilityIntervention).where(
            StabilityIntervention.user_id == user.id
        ).order_by(StabilityIntervention.created_at.desc()).limit(20)
    )
    interventions = result.scalars().all()
    return {"code": 0, "data": [
        {"id": i.id, "type": i.intervention_type, "trigger": i.trigger,
         "action": i.action_taken, "severity": i.severity, "created_at": i.created_at.isoformat()}
        for i in interventions
    ]}
