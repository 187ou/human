"""数据挖掘层API：因果DAG、隐性模式、漂移检测"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, get_current_user
from app.models.user import User
from app.services.causal_dag import CausalDAGBuilder
from app.services.ks_drift import KSDriftDetector

router = APIRouter()


# ==================== 因果DAG ====================

@router.post("/build-dag")
async def build_dag(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """构建因果DAG"""
    builder = CausalDAGBuilder(session, user.id)
    result = await builder.build_dag()
    return {"code": 0, "data": result}


@router.get("/dag-nodes")
async def dag_nodes(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """获取DAG节点"""
    from app.models.mining import CausalDAGNode
    from sqlalchemy import select, and_
    result = await session.execute(
        select(CausalDAGNode).where(and_(CausalDAGNode.user_id == user.id, CausalDAGNode.is_active == True))
    )
    nodes = result.scalars().all()
    return {"code": 0, "data": [
        {"name": n.node_name, "type": n.node_type, "mean": n.mean_value, "samples": n.sample_count}
        for n in nodes
    ]}


@router.get("/dag-edges")
async def dag_edges(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """获取DAG边"""
    from app.models.mining import CausalDAGEdge
    from sqlalchemy import select, and_
    result = await session.execute(
        select(CausalDAGEdge).where(and_(CausalDAGEdge.user_id == user.id, CausalDAGEdge.is_active == True))
    )
    edges = result.scalars().all()
    return {"code": 0, "data": [
        {"cause": e.cause_node, "effect": e.effect_node, "strength": e.causal_strength}
        for e in edges
    ]}


# ==================== 漂移检测 ====================

@router.post("/detect-drift")
async def detect_drift(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """检测偏好漂移"""
    detector = KSDriftDetector(session, user.id)
    drifts = await detector.detect_all()
    return {"code": 0, "data": {"drifts_found": len(drifts), "drifts": drifts}}


# ==================== 综合挖掘 ====================

@router.post("/full-analysis")
async def full_analysis(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """综合分析：DAG+漂移+因果"""
    # 1. 构建DAG
    builder = CausalDAGBuilder(session, user.id)
    dag_result = await builder.build_dag()

    # 2. 漂移检测
    detector = KSDriftDetector(session, user.id)
    drifts = await detector.detect_all()

    # 3. 因果挖掘
    from app.services.causal_miner import CausalMiner
    miner = CausalMiner(session, user.id)
    causal = await miner.mine_causal_relationships()

    await session.commit()
    return {"code": 0, "data": {
        "dag": dag_result,
        "drifts": drifts,
        "causal_relationships": len(causal),
    }}
