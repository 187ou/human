"""向量存储API"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, get_current_user
from app.models.user import User
from app.services.vector_store import VectorStore

router = APIRouter()


class PreferenceStore(BaseModel):
    dimension: str
    description: str


class ConversationStore(BaseModel):
    summary: str
    intent_type: str | None = None
    result_summary: str | None = None


class PlanStore(BaseModel):
    plan_type: str
    description: str
    plan_data: dict | None = None


# === 静态路径放前面 ===

@router.get("/stats")
async def vector_stats():
    """向量库统计"""
    from app.vector_db import vector_db
    stats = await vector_db.get_stats()
    return {"code": 0, "data": stats}


@router.post("/vectorize-habits")
async def vectorize_habits(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """从行为日志生成习惯向量"""
    store = VectorStore(session, user.id)
    vectors = await store.vectorize_habits()
    await session.commit()
    return {"code": 0, "data": {"vectorized": len(vectors)}}


# === 偏好 ===

@router.post("/preferences")
async def store_preference(
    data: PreferenceStore,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    store = VectorStore(session, user.id)
    vec = await store.store_preference(data.dimension, data.description)
    await session.commit()
    return {"code": 0, "data": {"id": vec}}


@router.get("/preferences")
async def get_preferences(
    dimension: str | None = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    store = VectorStore(session, user.id)
    items = await store.get_preferences(dimension)
    return {"code": 0, "data": [
        {"id": v.id, "dimension": v.dimension, "description": v.description, "source": v.source}
        for v in items
    ]}


# === 对话 ===

@router.post("/conversations")
async def store_conversation(
    data: ConversationStore,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    store = VectorStore(session, user.id)
    vec = await store.store_conversation(data.summary, data.intent_type, data.result_summary)
    await session.commit()
    return {"code": 0, "data": {"id": vec}}


@router.get("/conversations")
async def get_conversations(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    store = VectorStore(session, user.id)
    items = await store.get_recent_conversations()
    return {"code": 0, "data": [
        {"id": v.id, "summary": v.summary, "intent_type": v.intent_type, "created_at": v.created_at.isoformat()}
        for v in items
    ]}


# === 方案（静态路径优先） ===

@router.post("/store-plan")
async def store_plan(
    data: PlanStore,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """存储历史方案"""
    store = VectorStore(session, user.id)
    vec_id = await store.store_plan(data.plan_type, data.description, data.plan_data)
    await session.commit()
    return {"code": 0, "data": {"id": vec_id}}


@router.get("/recall-all")
async def recall_all(
    context: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """综合召回（偏好+对话+习惯）"""
    store = VectorStore(session, user.id)
    results = await store.recall_all(context)
    return {"code": 0, "data": results}


@router.get("/recall")
async def recall_plans(
    plan_type: str,
    context: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """召回相似历史方案"""
    store = VectorStore(session, user.id)
    recalls = await store.recall_similar_plans(plan_type, context)
    return {"code": 0, "data": recalls}
