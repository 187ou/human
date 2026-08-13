"""记忆与经验API"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, get_current_user
from app.models.user import User
from app.services.memory_tier import MemoryTierManager
from app.services.skill_craft import SkillCraft
from app.services.failure_learner import FailureLearner

router = APIRouter()


# ==================== 三级记忆 ====================

class MemoryCreate(BaseModel):
    memory_type: str
    title: str
    description: str
    dimension: str
    data: dict | None = None
    importance: float = 0.5
    valence: float = 0.0


@router.post("/create")
async def create_memory(
    data: MemoryCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """创建情景记忆"""
    manager = MemoryTierManager(session, user.id)
    memory = await manager.create_memory(
        data.memory_type, data.title, data.description,
        data.dimension, data.data, data.importance, data.valence
    )
    await session.commit()
    return {"code": 0, "data": {"id": memory.id}}


@router.post("/compress")
async def compress_memories(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """压缩记忆"""
    manager = MemoryTierManager(session, user.id)
    result = await manager.daily_compression()
    await session.commit()
    return {"code": 0, "data": result}


@router.get("/summary")
async def memory_summary(
    days: int = 7,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """获取记忆摘要"""
    manager = MemoryTierManager(session, user.id)
    summary = await manager.get_memory_summary(days)
    return {"code": 0, "data": summary}


# ==================== 技能封装 ====================

class SkillInvoke(BaseModel):
    skill_type: str
    params: dict = {}


@router.post("/invoke-skill")
async def invoke_skill(
    data: SkillInvoke,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """调用技能"""
    craft = SkillCraft(session, user.id)
    result = await craft.invoke_skill(data.skill_type, data.params)
    await session.commit()
    return {"code": 0, "data": result}


@router.get("/skills")
async def list_skills(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """获取所有技能"""
    craft = SkillCraft(session, user.id)
    skills = await craft.get_all_skills()
    return {"code": 0, "data": [
        {"id": s.id, "name": s.name, "type": s.skill_type, "use_count": s.use_count, "success_rate": s.success_rate}
        for s in skills
    ]}


# ==================== 失败复盘 ====================

class FailureRecord(BaseModel):
    failure_type: str
    title: str
    description: str
    severity: int = 5
    trigger: dict | None = None


@router.post("/record-failure")
async def record_failure(
    data: FailureRecord,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """记录失败"""
    learner = FailureLearner(session, user.id)
    memory = await learner.record_failure(data.failure_type, data.title, data.description, data.severity, data.trigger)
    await session.commit()
    return {"code": 0, "data": {"id": memory.id, "strategy": memory.avoidance_strategy}}


@router.get("/failure-patterns")
async def failure_patterns(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """获取失败模式"""
    learner = FailureLearner(session, user.id)
    patterns = await learner.get_failure_patterns()
    return {"code": 0, "data": patterns}


@router.post("/counter-rules")
async def generate_counter_rules(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """生成反向约束规则"""
    learner = FailureLearner(session, user.id)
    rules = await learner.generate_counter_rules()
    return {"code": 0, "data": rules}
