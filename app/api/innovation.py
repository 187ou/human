"""核心创新API：因果挖掘、精力建模、状态记忆、规则生命周期、博弈协商"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, get_current_user
from app.models.user import User
from app.services.causal_miner import CausalMiner
from app.services.energy_model import EnergyModel
from app.services.life_state import LifeStateManager
from app.services.rule_lifecycle import RuleLifecycleManager
from app.services.negotiation import NegotiationEngine

router = APIRouter()


# ==================== 因果挖掘 ====================

@router.post("/causal/mine")
async def mine_causal(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """挖掘行为因果关系"""
    miner = CausalMiner(session, user.id)
    results = await miner.mine_causal_relationships()
    await session.commit()
    return {"code": 0, "data": {
        "found": len(results),
        "relationships": results,
    }}


@router.get("/causal/conclusions")
async def causal_conclusions(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """获取因果结论"""
    miner = CausalMiner(session, user.id)
    conclusions = await miner.get_causal_conclusions()
    return {"code": 0, "data": [
        {"id": c.id, "cause": c.cause_event, "effect": c.effect_event,
         "confidence": c.confidence, "type": c.causal_type, "conclusion": c.conclusion}
        for c in conclusions
    ]}


# ==================== 精力建模 ====================

@router.post("/energy/calculate")
async def calculate_energy(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """计算今日精力值"""
    model = EnergyModel(session, user.id)
    record = await model.calculate_daily_energy()
    await session.commit()
    return {"code": 0, "data": {
        "total_energy": record.total_energy,
        "energy_level": record.energy_level,
        "factors": record.factors,
    }}


@router.get("/energy/recommendation")
async def energy_recommendation(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """获取精力推荐"""
    model = EnergyModel(session, user.id)
    rec = await model.get_task_recommendation()
    return {"code": 0, "data": rec}


@router.get("/energy/trend")
async def energy_trend(
    days: int = 7,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """获取精力趋势"""
    model = EnergyModel(session, user.id)
    records = await model.get_energy_trend(days)
    return {"code": 0, "data": [
        {"date": r.record_date, "energy": r.total_energy, "level": r.energy_level}
        for r in records
    ]}


# ==================== 生活状态记忆 ====================

@router.post("/life-state/generate")
async def generate_life_state(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """生成生活状态快照"""
    manager = LifeStateManager(session, user.id)
    snapshot = await manager.generate_snapshot()
    await session.commit()
    return {"code": 0, "data": {
        "phase": snapshot.life_phase,
        "confidence": snapshot.phase_confidence,
        "trend": snapshot.trend,
        "summary": snapshot.summary,
    }}


@router.get("/life-state/current")
async def current_life_state(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """获取当前生活状态"""
    manager = LifeStateManager(session, user.id)
    state = await manager.get_current_phase()
    return {"code": 0, "data": state}


# ==================== 规则生命周期 ====================

@router.post("/rules/lifecycle")
async def process_lifecycle(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """处理规则生命周期"""
    manager = RuleLifecycleManager(session, user.id)
    result = await manager.process_lifecycle()
    await session.commit()
    return {"code": 0, "data": result}


@router.get("/rules/lifecycle-stats")
async def lifecycle_stats(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """获取生命周期统计"""
    manager = RuleLifecycleManager(session, user.id)
    stats = await manager.get_lifecycle_stats()
    return {"code": 0, "data": stats}


# ==================== 博弈协商 ====================

class NegotiateRequest(BaseModel):
    topic: str = "协商"
    proposals: dict = {}


@router.post("/negotiate")
async def negotiate(
    data: NegotiateRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """执行多智能体博弈协商"""
    engine = NegotiationEngine(session, user.id)
    result = await engine.negotiate(data.topic, data.proposals)
    await session.commit()
    return {"code": 0, "data": result}
