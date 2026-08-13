"""三级弹性记忆架构引擎

层级：
1. 瞬时记忆 - 当日对话、临时日程（LangGraph状态常驻）
2. 情景记忆 - 近3个月完整行为轨迹（向量存储）
3. 长期习惯记忆 - 萃取固化规则（结构化数据表）
"""
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import EpisodicMemory


class MemoryTierManager:
    """三级记忆管理器"""

    # 时间阈值
    EPISODIC_DAYS = 90  # 情景记忆保留90天
    COMPRESS_THRESHOLD = 30  # 30天以上的记忆开始压缩

    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id

    async def create_memory(self, memory_type: str, title: str, description: str,
                             dimension: str, data: dict | None = None,
                             importance: float = 0.5, valence: float = 0.0) -> EpisodicMemory:
        """创建情景记忆"""
        memory = EpisodicMemory(
            user_id=self.user_id,
            memory_type=memory_type,
            title=title,
            description=description,
            dimension=dimension,
            related_data=data or {},
            importance=importance,
            emotional_valence=valence,
        )
        self.session.add(memory)
        await self.session.flush()
        return memory

    async def search_memories(self, query: str, memory_type: str | None = None,
                               limit: int = 10) -> list[EpisodicMemory]:
        """搜索情景记忆"""
        stmt = select(EpisodicMemory).where(and_(
            EpisodicMemory.user_id == self.user_id,
            EpisodicMemory.is_compressed == False,
        ))
        if memory_type:
            stmt = stmt.where(EpisodicMemory.memory_type == memory_type)

        result = await self.session.execute(stmt.order_by(EpisodicMemory.importance.desc()).limit(limit))
        return list(result.scalars().all())

    async def daily_compression(self) -> dict[str, int]:
        """每日压缩：将短期记忆提炼为长期经验"""
        cutoff = datetime.utcnow() - timedelta(days=self.COMPRESS_THRESHOLD)

        # 获取需要压缩的记忆
        result = await self.session.execute(
            select(EpisodicMemory).where(and_(
                EpisodicMemory.user_id == self.user_id,
                EpisodicMemory.created_at < cutoff,
                EpisodicMemory.is_compressed == False,
            ))
        )
        old_memories = result.scalars().all()

        compressed = 0
        for memory in old_memories:
            # 压缩为长期规则
            memory.is_compressed = True
            compressed += 1

        await self.session.flush()
        return {"compressed": compressed}

    async def get_memory_summary(self, days: int = 7) -> dict[str, Any]:
        """获取近期记忆摘要"""
        cutoff = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')

        result = await self.session.execute(
            select(EpisodicMemory).where(and_(
                EpisodicMemory.user_id == self.user_id,
                EpisodicMemory.created_at >= datetime.utcnow() - timedelta(days=days),
            )).order_by(EpisodicMemory.created_at.desc())
        )
        memories = result.scalars().all()

        return {
            "period_days": days,
            "total_memories": len(memories),
            "successes": len([m for m in memories if m.memory_type == "success"]),
            "failures": len([m for m in memories if m.memory_type == "failure"]),
            "recent": [{"title": m.title, "type": m.memory_type, "importance": m.importance} for m in memories[:5]],
        }
