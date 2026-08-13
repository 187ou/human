"""自适应演化API"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, get_current_user
from app.models.user import User
from app.models.rule import UserRule
from app.evolution.engine import EvolutionEngine

router = APIRouter()


# ==================== 演化触发 ====================

@router.post("/run")
async def run_evolution(
    mode: str = "incremental",  # incremental | full
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """触发演化"""
    engine = EvolutionEngine(session, user.id)
    if mode == "full":
        result = await engine.run_full()
    else:
        result = await engine.run_incremental()
    return {"code": 0, "data": result}


# ==================== 规则管理 ====================

@router.get("/rules")
async def list_rules(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """查看用户专属规则库"""
    result = await session.execute(
        select(UserRule).where(UserRule.user_id == user.id).order_by(UserRule.priority.desc(), UserRule.updated_at.desc())
    )
    rules = result.scalars().all()
    return {"code": 0, "data": [
        {"id": r.id, "dimension": r.dimension, "name": r.name, "description": r.description,
         "confidence": r.confidence, "sample_count": r.sample_count, "version": r.version,
         "is_active": r.is_active, "priority": r.priority,
         "updated_at": r.updated_at.isoformat()}
        for r in rules
    ]}


class RuleUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    priority: int | None = None


@router.put("/rules/{rule_id}")
async def update_rule(
    rule_id: int,
    data: RuleUpdateRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """修改规则参数"""
    engine = EvolutionEngine(session, user.id)
    ok = await engine.update_rule(rule_id, **{k: v for k, v in data.model_dump().items() if v is not None})
    return {"code": 0 if ok else 1, "message": "ok" if ok else "规则不存在"}


@router.post("/rules/{rule_id}/toggle")
async def toggle_rule(
    rule_id: int,
    active: bool,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """启用/禁用规则"""
    engine = EvolutionEngine(session, user.id)
    ok = await engine.toggle_rule(rule_id, active)
    return {"code": 0 if ok else 1, "message": "ok" if ok else "规则不存在"}


@router.delete("/rules/{rule_id}")
async def delete_rule(
    rule_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """删除规则"""
    engine = EvolutionEngine(session, user.id)
    ok = await engine.delete_rule(rule_id)
    return {"code": 0 if ok else 1, "message": "ok" if ok else "规则不存在"}


@router.post("/rules/{rule_id}/pin")
async def pin_rule(
    rule_id: int,
    priority: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """设置规则优先级"""
    engine = EvolutionEngine(session, user.id)
    ok = await engine.pin_priority(rule_id, priority)
    return {"code": 0 if ok else 1, "message": "ok" if ok else "规则不存在"}


@router.post("/rules/{rule_id}/rollback")
async def rollback_rule(
    rule_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """回滚到上一版本"""
    engine = EvolutionEngine(session, user.id)
    ok = await engine.rollback_rule(rule_id)
    return {"code": 0 if ok else 1, "message": "ok" if ok else "无法回滚"}


@router.get("/snapshot")
async def rules_snapshot(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """获取当前生效规则快照"""
    engine = EvolutionEngine(session, user.id)
    snapshot = await engine.get_active_rules()
    return {"code": 0, "data": snapshot}
