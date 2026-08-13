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


@router.post("/preferences")
async def store_preference(
    data: PreferenceStore,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    store = VectorStore(session, user.id)
    vec = await store.store_preference(data.dimension, data.description)
    await session.commit()
    return {"code": 0, "data": {"id": vec.id}}


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


@router.post("/conversations")
async def store_conversation(
    data: ConversationStore,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    store = VectorStore(session, user.id)
    vec = await store.store_conversation(data.summary, data.intent_type, data.result_summary)
    await session.commit()
    return {"code": 0, "data": {"id": vec.id}}


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
