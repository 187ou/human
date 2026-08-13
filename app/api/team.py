"""多智能体协同演化API"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, get_current_user
from app.models.user import User
from app.services.team_evolution import TeamEvolution
from app.services.graph_reconfig import GraphReconfigurator

router = APIRouter()


# ==================== 协同共进化 ====================

class AgentTaskRecord(BaseModel):
    agent_name: str
    success: bool
    quality: float = 0.5


@router.post("/evolve")
async def evolve_team(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """执行三层协同进化"""
    team = TeamEvolution(session, user.id)
    result = await team.evolve_all_layers()
    return {"code": 0, "data": result}


@router.post("/record-task")
async def record_agent_task(
    data: AgentTaskRecord,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """记录Agent任务"""
    team = TeamEvolution(session, user.id)
    await team.record_agent_task(data.agent_name, data.success, data.quality)
    await session.commit()
    return {"code": 0}


@router.get("/performances")
async def agent_performances(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """获取Agent表现"""
    from app.models.team import AgentPerformance
    from sqlalchemy import select, and_
    result = await session.execute(
        select(AgentPerformance).where(AgentPerformance.user_id == user.id)
    )
    perfs = result.scalars().all()
    return {"code": 0, "data": [
        {"agent": p.agent_name, "tasks": p.total_tasks, "success_rate": round(p.success_tasks / max(p.total_tasks, 1), 2),
         "quality": round(p.avg_quality, 2)}
        for p in perfs
    ]}


# ==================== 图重构 ====================

@router.post("/reconfigure")
async def reconfigure_graph(
    scene: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """根据场景重构图"""
    reconfig = GraphReconfigurator(session, user.id)
    result = await reconfig.reconfigure_for_scene(scene)
    await session.commit()
    return {"code": 0, "data": result}


@router.get("/graph-config")
async def graph_config(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """获取当前图配置"""
    reconfig = GraphReconfigurator(session, user.id)
    config = await reconfig.get_current_config()
    return {"code": 0, "data": config}
