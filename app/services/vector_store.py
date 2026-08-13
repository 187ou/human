"""向量存储服务：用户偏好+对话向量（轻量级，兼容SQLite）"""
import json
from datetime import datetime
from typing import Any

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vector import UserPreferenceVector, ConversationVector


class VectorStore:
    """轻量级向量存储（SQLite兼容）"""

    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id

    # ==================== 用户偏好向量 ====================

    async def store_preference(self, dimension: str, description: str,
                                embedding: list[float] | None = None,
                                source: str = "auto") -> UserPreferenceVector:
        """存储用户偏好向量"""
        vec = UserPreferenceVector(
            user_id=self.user_id,
            dimension=dimension,
            description=description,
            embedding=embedding or [],
            source=source,
        )
        self.session.add(vec)
        await self.session.flush()
        return vec

    async def get_preferences(self, dimension: str | None = None, limit: int = 10) -> list[UserPreferenceVector]:
        """获取用户偏好"""
        stmt = select(UserPreferenceVector).where(UserPreferenceVector.user_id == self.user_id)
        if dimension:
            stmt = stmt.where(UserPreferenceVector.dimension == dimension)
        result = await self.session.execute(stmt.order_by(UserPreferenceVector.updated_at.desc()).limit(limit))
        return list(result.scalars().all())

    async def search_similar_preferences(self, query_text: str, dimension: str | None = None, limit: int = 5) -> list[dict]:
        """基于文本相似度搜索偏好（轻量级：关键词匹配）"""
        stmt = select(UserPreferenceVector).where(UserPreferenceVector.user_id == self.user_id)
        if dimension:
            stmt = stmt.where(UserPreferenceVector.dimension == dimension)

        result = await self.session.execute(stmt)
        preferences = result.scalars().all()

        # 简单的关键词匹配（无需嵌入模型）
        query_words = set(query_text.lower().split())
        scored = []
        for pref in preferences:
            desc_words = set(pref.description.lower().split())
            overlap = len(query_words & desc_words)
            if overlap > 0:
                scored.append({"preference": pref, "score": overlap / max(len(query_words), 1)})

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:limit]

    # ==================== 对话向量 ====================

    async def store_conversation(self, summary: str, intent_type: str | None = None,
                                  result_summary: str | None = None,
                                  embedding: list[float] | None = None) -> ConversationVector:
        """存储对话向量"""
        vec = ConversationVector(
            user_id=self.user_id,
            summary=summary,
            embedding=embedding or [],
            intent_type=intent_type,
            result_summary=result_summary,
        )
        self.session.add(vec)
        await self.session.flush()
        return vec

    async def get_recent_conversations(self, limit: int = 5) -> list[ConversationVector]:
        """获取最近对话"""
        result = await self.session.execute(
            select(ConversationVector)
            .where(ConversationVector.user_id == self.user_id)
            .order_by(ConversationVector.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def search_conversations(self, keyword: str, limit: int = 5) -> list[ConversationVector]:
        """搜索历史对话"""
        result = await self.session.execute(
            select(ConversationVector)
            .where(and_(
                ConversationVector.user_id == self.user_id,
                ConversationVector.summary.contains(keyword),
            ))
            .order_by(ConversationVector.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
