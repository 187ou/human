"""Agent对话API"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, get_current_user
from app.models.user import User
from app.agents.orchestrator import orchestrator_graph
from app.evolution.engine import EvolutionEngine

router = APIRouter()


class ChatRequest(BaseModel):
    message: str


@router.post("/chat")
async def chat(
    data: ChatRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """与智能Agent对话"""
    # 1. 加载用户规则
    engine = EvolutionEngine(session, user.id)
    rules = await engine.get_active_rules()

    # 2. 构建初始状态
    initial_state = {
        "user_id": user.id,
        "input": data.message,
        "active_agent": "none",
        "agent_output": {},
        "messages": [],
        "user_rules": rules,
        "need_evolution": False,
        "response": "",
    }

    # 3. 执行编排图
    result = await orchestrator_graph.ainvoke(initial_state)

    return {
        "code": 0,
        "data": {
            "response": result.get("response", ""),
            "active_agent": result.get("active_agent", "none"),
            "agent_output": result.get("agent_output", {}),
            "rules_applied": list(rules.keys()),
        },
    }
