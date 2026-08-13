"""向量存储服务：用户偏好+对话向量+习惯向量+方案召回（轻量级，兼容SQLite）"""
import hashlib
import json
import re
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
        """基于文本相似度搜索偏好（轻量级：关键词匹配+TF-IDF加权）"""
        stmt = select(UserPreferenceVector).where(UserPreferenceVector.user_id == self.user_id)
        if dimension:
            stmt = stmt.where(UserPreferenceVector.dimension == dimension)

        result = await self.session.execute(stmt)
        preferences = result.scalars().all()

        # 关键词匹配 + 词频加权
        query_words = set(_tokenize(query_text))
        scored = []
        for pref in preferences:
            desc_words = set(_tokenize(pref.description))
            overlap = query_words & desc_words
            if overlap:
                score = len(overlap) / max(len(query_words), 1)
                # 考虑时效性（越近越重要）
                days_old = (datetime.utcnow() - pref.updated_at).days
                time_weight = max(0.5, 1.0 - days_old / 365)
                scored.append({"preference": pref, "score": round(score * time_weight, 3)})

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

    # ==================== 习惯向量（从行为日志生成） ====================

    async def vectorize_habits(self) -> list[UserPreferenceVector]:
        """从行为日志生成习惯向量"""
        from app.models.behavior import BehaviorLog
        from sqlalchemy import select, func

        dimensions = ["time", "study", "consume", "item"]
        vectors = []

        for dim in dimensions:
            # 统计该维度的关键特征
            result = await self.session.execute(
                select(
                    func.count(BehaviorLog.id),
                    func.avg(BehaviorLog.value),
                    func.group_concat(BehaviorLog.event_type),
                ).where(and_(
                    BehaviorLog.user_id == self.user_id,
                    BehaviorLog.dimension == dim,
                    BehaviorLog.created_at >= datetime.utcnow() - timedelta(days=30),
                ))
            )
            row = result.one()
            count, avg_value, event_types = row

            if count == 0:
                continue

            # 生成习惯描述
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

            # 生成简单哈希嵌入（用于相似度比较）
            embedding = _simple_hash_embedding(description)

            vec = await self.store_preference(dim, description, embedding, source="auto")
            vectors.append(vec)

        await self.session.flush()
        return vectors

    # ==================== 方案召回 ====================

    async def recall_similar_plans(self, plan_type: str, context: str, limit: int = 3) -> list[dict]:
        """召回相似历史方案（新建计划时参考）"""
        # 1. 搜索相关偏好
        pref_results = await self.search_similar_preferences(context, dimension=plan_type, limit=limit)

        # 2. 搜索相关对话
        conv_results = await self.search_conversations(context, limit=limit)

        # 3. 组合召回结果
        recalls = []
        for pref in pref_results:
            recalls.append({
                "type": "preference",
                "score": pref["score"],
                "description": pref["preference"].description,
                "dimension": pref["preference"].dimension,
            })

        for conv in conv_results:
            recalls.append({
                "type": "conversation",
                "score": 0.5,
                "description": conv.summary,
                "intent_type": conv.intent_type,
                "result": conv.result_summary,
            })

        recalls.sort(key=lambda x: x["score"], reverse=True)
        return recalls[:limit]


def _tokenize(text: str) -> list[str]:
    """简单分词"""
    return re.findall(r'[一-鿿]+|[a-zA-Z]+', text.lower())


def _simple_hash_embedding(text: str, dim: int = 64) -> list[float]:
    """生成简单哈希嵌入（无需外部模型）"""
    embedding = [0.0] * dim
    words = _tokenize(text)
    for word in words:
        hash_val = int(hashlib.md5(word.encode()).hexdigest(), 16)
        for i in range(dim):
            bit = (hash_val >> i) & 1
            embedding[i] += 1.0 if bit else -1.0

    # 归一化
    magnitude = sum(x**2 for x in embedding) ** 0.5
    if magnitude > 0:
        embedding = [round(x / magnitude, 4) for x in embedding]
    return embedding
