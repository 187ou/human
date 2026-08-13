"""系统自演化高级机制API"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, get_current_user
from app.models.user import User
from app.services.risk_guard import RiskGuard
from app.services.ks_drift import KSDriftDetector
from app.services.ab_test import ABTestManager

router = APIRouter()


# ==================== 风险自检 ====================

class RuleCheck(BaseModel):
    rule_name: str
    rule_expr: dict


@router.post("/risk-check")
async def risk_check(
    data: RuleCheck,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """规则风险自检"""
    guard = RiskGuard(session, user.id)
    result = await guard.check_rule_safety(data.rule_name, data.rule_expr)
    await session.commit()
    return {"code": 0, "data": result}


# ==================== 偏好漂移 ====================

@router.post("/detect-drift")
async def detect_drift(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """检测偏好漂移"""
    detector = DriftDetector(session, user.id)
    drifts = await detector.detect_drift()
    await session.commit()
    return {"code": 0, "data": {"drifts_found": len(drifts), "drifts": drifts}}


# ==================== A/B测试 ====================

class ABTestCreate(BaseModel):
    test_name: str
    dimension: str
    rule_a_expr: dict
    rule_b_expr: dict


class ABTestSample(BaseModel):
    test_id: int
    version: str  # A or B
    score: float


@router.post("/ab-test/create")
async def create_ab_test(
    data: ABTestCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """创建A/B测试"""
    manager = ABTestManager(session, user.id)
    test = await manager.create_test(data.test_name, data.dimension, data.rule_a_expr, data.rule_b_expr)
    await session.commit()
    return {"code": 0, "data": {"test_id": test.id, "status": test.status}}


@router.post("/ab-test/record")
async def record_ab_sample(
    data: ABTestSample,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """记录A/B测试样本"""
    manager = ABTestManager(session, user.id)
    await manager.record_sample(data.test_id, data.version, data.score)
    await session.commit()
    return {"code": 0}


@router.get("/ab-test/active")
async def active_tests(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """获取进行中的测试"""
    manager = ABTestManager(session, user.id)
    tests = await manager.get_active_tests()
    return {"code": 0, "data": [
        {"id": t.id, "name": t.test_name, "a_score": round(t.a_score, 3), "b_score": round(t.b_score, 3),
         "a_samples": t.a_samples, "b_samples": t.b_samples, "status": t.status}
        for t in tests
    ]}


@router.get("/ab-test/history")
async def test_history(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """获取测试历史"""
    manager = ABTestManager(session, user.id)
    tests = await manager.get_test_history()
    return {"code": 0, "data": [
        {"id": t.id, "name": t.test_name, "winner": t.winner, "status": t.status,
         "a_score": round(t.a_score, 3), "b_score": round(t.b_score, 3)}
        for t in tests
    ]}
