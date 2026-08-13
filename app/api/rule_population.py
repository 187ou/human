"""规则体系API：遗传演化、A/B测试、生命周期"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, get_current_user
from app.models.user import User
from app.services.genetic_rules import GeneticRuleEvolution
from app.services.rule_lifecycle import RuleLifecycleManager

router = APIRouter()


# ==================== 遗传演化 ====================

class RuleCreate(BaseModel):
    name: str
    dimension: str
    rule_expr: dict


class SampleRecord(BaseModel):
    rule_id: int
    success: bool


@router.post("/create")
async def create_rule(
    data: RuleCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """创建规则个体"""
    ga = GeneticRuleEvolution(session, user.id)
    rule = await ga.create_rule(data.name, data.dimension, data.rule_expr)
    await session.commit()
    return {"code": 0, "data": {"id": rule.id, "name": rule.name}}


@router.post("/evolve")
async def evolve_generation(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """执行一代遗传演化"""
    ga = GeneticRuleEvolution(session, user.id)
    result = await ga.evolve_generation()
    return {"code": 0, "data": result}


@router.post("/record-sample")
async def record_sample(
    data: SampleRecord,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """记录规则样本"""
    ga = GeneticRuleEvolution(session, user.id)
    await ga.record_sample(data.rule_id, data.success)
    await session.commit()
    return {"code": 0}


@router.get("/best-rules")
async def best_rules(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """获取最优规则"""
    ga = GeneticRuleEvolution(session, user.id)
    rules = await ga.get_best_rules()
    return {"code": 0, "data": [
        {"id": r.id, "name": r.name, "fitness": r.fitness_score, "generation": r.generation}
        for r in rules
    ]}


# ==================== 生命周期 ====================

@router.post("/lifecycle-process")
async def process_lifecycle_api(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """处理规则生命周期"""
    manager = RuleLifecycleManager(session, user.id)
    result = await manager.process_lifecycle()
    await session.commit()
    return {"code": 0, "data": result}
