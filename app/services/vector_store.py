"""向量存储服务：ChromaDB 向量数据库封装"""
import hashlib
import re
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vector import UserPreferenceVector, ConversationVector
from app.vector_db import vector_db


class VectorStore:
    """向量数据库封装（ChromaDB 后端）"""

    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id

    # ==================== 用户偏好向量 ====================

    async def store_preference(self, dimension: str, description: str,
                                embedding: list[float] | None = None,
                                source: str = "auto") -> str:
        """存储用户偏好向量（ChromaDB + 关系库双写）"""
        # ChromaDB 存储（向量检索）
        vec_id = await vector_db.store_preference(
            self.user_id, dimension, description,
            metadata={"source": source}
        )

        # 关系库存储（结构化查询）
        vec = UserPreferenceVector(
            user_id=self.user_id,
            dimension=dimension,
            description=description,
            embedding=embedding or [],
            source=source,
        )
        self.session.add(vec)
        await self.session.flush()
        return vec_id

    async def get_preferences(self, dimension: str | None = None, limit: int = 10) -> list[UserPreferenceVector]:
        """获取用户偏好"""
        stmt = select(UserPreferenceVector).where(UserPreferenceVector.user_id == self.user_id)
        if dimension:
            stmt = stmt.where(UserPreferenceVector.dimension == dimension)
        result = await self.session.execute(stmt.order_by(UserPreferenceVector.updated_at.desc()).limit(limit))
        return list(result.scalars().all())

    async def search_similar_preferences(self, query_text: str, dimension: str | None = None, limit: int = 5) -> list[dict]:
        """向量相似度搜索偏好"""
        return await vector_db.search_preferences(self.user_id, query_text, dimension, limit)

    # ==================== 对话向量 ====================

    async def store_conversation(self, summary: str, intent_type: str | None = None,
                                  result_summary: str | None = None,
                                  embedding: list[float] | None = None) -> str:
        """存储对话向量"""
        vec_id = await vector_db.store_conversation(
            self.user_id, summary, intent_type, result_summary
        )

        vec = ConversationVector(
            user_id=self.user_id,
            summary=summary,
            embedding=embedding or [],
            intent_type=intent_type,
            result_summary=result_summary,
        )
        self.session.add(vec)
        await self.session.flush()
        return vec_id

    async def get_recent_conversations(self, limit: int = 5) -> list[ConversationVector]:
        """获取最近对话"""
        result = await self.session.execute(
            select(ConversationVector)
            .where(ConversationVector.user_id == self.user_id)
            .order_by(ConversationVector.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def search_conversations(self, keyword: str, limit: int = 5) -> list[dict]:
        """向量搜索历史对话"""
        return await vector_db.search_conversations(self.user_id, keyword, limit)

    # ==================== 习惯向量 ====================

    async def vectorize_habits(self) -> list[str]:
        """从行为日志生成习惯向量"""
        from app.models.behavior import BehaviorLog
        from sqlalchemy import select, func

        dimensions = ["time", "study", "consume", "item"]
        vectors = []

        for dim in dimensions:
            result = await self.session.execute(
                select(
                    func.count(BehaviorLog.id),
                    func.avg(BehaviorLog.value),
                ).where(and_(
                    BehaviorLog.user_id == self.user_id,
                    BehaviorLog.dimension == dim,
                    BehaviorLog.created_at >= datetime.utcnow() - timedelta(days=30),
                ))
            )
            row = result.one()
            count, avg_value = row

            if count == 0:
                continue

            if dim == "time":
                description = f"近期记录{count}条日程，平均完成质量{avg_value or 0:.1f}"
            elif dim == "study":
                description = f"近期学习{count}次，平均正确率{avg_value or 0:.0%}"
            elif dim == "consume":
                description = f"近期消费{count}笔，平均金额{avg_value or 0:.0f}元"
            elif dim == "item":
                description = f"近期物品操作{count}次"
            else:
                description = f"近期{count}条记录"

            vec_id = await vector_db.store_habit(self.user_id, dim, description)
            vectors.append(vec_id)

        await self.session.flush()
        return vectors

    async def search_habits(self, query: str, habit_type: str | None = None, limit: int = 5) -> list[dict]:
        """搜索相似习惯"""
        return await vector_db.search_habits(self.user_id, query, habit_type, limit)

    # ==================== 方案召回 ====================

    async def store_plan(self, plan_type: str, description: str, plan_data: dict | None = None) -> str:
        """存储历史方案"""
        return await vector_db.store_plan(self.user_id, plan_type, description, plan_data)

    async def recall_similar_plans(self, plan_type: str, context: str, limit: int = 3) -> list[dict]:
        """召回相似历史方案"""
        return await vector_db.recall_similar_plans(self.user_id, plan_type, context, limit)

    # ==================== 综合召回 ====================

    async def recall_all(self, context: str, limit: int = 5) -> dict[str, list[dict]]:
        """综合召回：偏好+对话+习惯+方案"""
        return {
            "preferences": await self.search_similar_preferences(context, limit=limit),
            "conversations": await self.search_conversations(context, limit=limit),
            "habits": await self.search_habits(context, limit=limit),
        }
