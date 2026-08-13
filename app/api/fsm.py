"""多Agent协同API：状态机、资源调度、预测智能"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, get_current_user
from app.models.user import User
from app.services.scene_fsm import SceneFSM
from app.services.resource_scheduler import ResourceScheduler
from app.services.predictor import Predictor

router = APIRouter()


# ==================== 场景状态机 ====================

class StateSwitch(BaseModel):
    new_state: str
    params: dict | None = None


@router.post("/switch-state")
async def switch_state(
    data: StateSwitch,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """切换生活状态（全模块联动）"""
    fsm = SceneFSM(session, user.id)
    result = await fsm.switch_state(data.new_state, data.params)
    await session.commit()
    return {"code": 0 if result["success"] else 1, "data": result}


@router.get("/current-state")
async def current_state(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """获取当前状态"""
    fsm = SceneFSM(session, user.id)
    state = await fsm.get_current_state()
    return {"code": 0, "data": state}


@router.get("/available-states")
async def available_states():
    """获取可用状态列表"""
    return {"code": 0, "data": [
        {"state": "daily", "label": "日常", "icon": "🏠"},
        {"state": "exam", "label": "备考", "icon": "📝"},
        {"state": "travel", "label": "出差", "icon": "✈️"},
        {"state": "vacation", "label": "假期", "icon": "🏖️"},
        {"state": "sick", "label": "生病", "icon": "🤒"},
        {"state": "overtime", "label": "加班", "icon": "💼"},
    ]}


# ==================== 资源调度 ====================

@router.post("/allocate-resources")
async def allocate_resources(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """生成资源分配方案"""
    scheduler = ResourceScheduler(session, user.id)
    result = await scheduler.generate_allocation()
    await session.commit()
    return {"code": 0, "data": result}


# ==================== 预测智能 ====================

@router.post("/generate-predictions")
async def generate_predictions(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """生成预测"""
    predictor = Predictor(session, user.id)
    predictions = await predictor.generate_predictions()
    await session.commit()
    return {"code": 0, "data": predictions}
