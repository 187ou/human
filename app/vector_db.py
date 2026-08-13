"""向量数据库服务：ChromaDB 嵌入式向量存储 + pgvector 兼容层"""
import os
import hashlib
import json
from datetime import datetime
from typing import Any

import chromadb
from chromadb.config import Settings

from loguru import logger

# ChromaDB 持久化路径
VECTOR_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "vector_db")


class VectorDB:
    """向量数据库管理器（ChromaDB 嵌入式）"""

    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=VECTOR_DB_PATH,
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
        )
        self._collections = {}

    def _get_collection(self, name: str):
        """获取或创建集合"""
        if name not in self._collections:
            self._collections[name] = self.client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"},  # 余弦相似度
            )
        return self._collections[name]

    # ==================== 用户偏好向量 ====================

    async def store_preference(self, user_id: int, dimension: str, description: str,
                                metadata: dict | None = None) -> str:
        """存储用户偏好向量"""
        collection = self._get_collection("user_preferences")
        vec_id = f"pref_{user_id}_{dimension}_{hashlib.md5(description.encode()).hexdigest()[:8]}"

        meta = {
            "user_id": user_id,
            "dimension": dimension,
            "created_at": datetime.utcnow().isoformat(),
            **(metadata or {}),
        }

        collection.upsert(
            ids=[vec_id],
            documents=[description],
            metadatas=[meta],
        )
        logger.debug(f"stored preference: {vec_id}")
        return vec_id

    async def search_preferences(self, user_id: int, query: str, dimension: str | None = None, limit: int = 5) -> list[dict]:
        """搜索相似用户偏好"""
        collection = self._get_collection("user_preferences")
        if dimension:
            where = {"$and": [{"user_id": user_id}, {"dimension": dimension}]}
        else:
            where = {"user_id": user_id}

        results = collection.query(
            query_texts=[query],
            where=where,
            n_results=limit,
        )

        ids = results.get("ids", [[]])[0]
        if not ids:
            return []

        return [{
            "id": ids[i],
            "description": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i] if results.get("distances") else 0,
        } for i in range(len(ids))]

    # ==================== 对话向量 ====================

    async def store_conversation(self, user_id: int, summary: str, intent_type: str | None = None,
                                  result_summary: str | None = None) -> str:
        """存储对话向量"""
        collection = self._get_collection("conversations")
        vec_id = f"conv_{user_id}_{hashlib.md5(summary.encode()).hexdigest()[:12]}"

        collection.upsert(
            ids=[vec_id],
            documents=[summary],
            metadatas=[{
                "user_id": user_id,
                "intent_type": intent_type or "",
                "result_summary": result_summary or "",
                "created_at": datetime.utcnow().isoformat(),
            }],
        )
        return vec_id

    async def search_conversations(self, user_id: int, query: str, limit: int = 5) -> list[dict]:
        """搜索相似历史对话"""
        collection = self._get_collection("conversations")
        results = collection.query(
            query_texts=[query],
            where={"user_id": {"$eq": user_id}},
            n_results=limit,
        )

        ids = results.get("ids", [[]])[0]
        if not ids:
            return []

        return [{
            "id": ids[i],
            "summary": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i] if results.get("distances") else 0,
        } for i in range(len(ids))]

    # ==================== 习惯向量 ====================

    async def store_habit(self, user_id: int, habit_type: str, description: str,
                           metadata: dict | None = None) -> str:
        """存储习惯向量"""
        collection = self._get_collection("habits")
        vec_id = f"habit_{user_id}_{habit_type}_{hashlib.md5(description.encode()).hexdigest()[:8]}"

        collection.upsert(
            ids=[vec_id],
            documents=[description],
            metadatas=[{
                "user_id": user_id,
                "habit_type": habit_type,
                "created_at": datetime.utcnow().isoformat(),
                **(metadata or {}),
            }],
        )
        return vec_id

    async def search_habits(self, user_id: int, query: str, habit_type: str | None = None, limit: int = 5) -> list[dict]:
        """搜索相似习惯"""
        collection = self._get_collection("habits")
        if habit_type:
            where = {"$and": [{"user_id": user_id}, {"habit_type": habit_type}]}
        else:
            where = {"user_id": user_id}

        results = collection.query(
            query_texts=[query],
            where=where,
            n_results=limit,
        )

        ids = results.get("ids", [[]])[0]
        if not ids:
            return []

        return [{
            "id": ids[i],
            "description": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i] if results.get("distances") else 0,
        } for i in range(len(ids))]

    # ==================== 方案召回 ====================

    async def store_plan(self, user_id: int, plan_type: str, description: str,
                          plan_data: dict | None = None) -> str:
        """存储历史方案"""
        collection = self._get_collection("plans")
        vec_id = f"plan_{user_id}_{plan_type}_{hashlib.md5(description.encode()).hexdigest()[:8]}"

        collection.upsert(
            ids=[vec_id],
            documents=[description],
            metadatas=[{
                "user_id": user_id,
                "plan_type": plan_type,
                "plan_data": json.dumps(plan_data or {}, ensure_ascii=False),
                "created_at": datetime.utcnow().isoformat(),
            }],
        )
        return vec_id

    async def recall_similar_plans(self, user_id: int, plan_type: str, context: str, limit: int = 3) -> list[dict]:
        """召回相似历史方案"""
        collection = self._get_collection("plans")
        results = collection.query(
            query_texts=[context],
            where={"$and": [{"user_id": user_id}, {"plan_type": plan_type}]},
            n_results=limit,
        )

        ids = results.get("ids", [[]])[0]
        if not ids:
            return []

        return [{
            "id": ids[i],
            "description": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i] if results.get("distances") else 0,
        } for i in range(len(ids))]

    # ==================== 通用操作 ====================

    async def delete_by_user(self, user_id: int) -> None:
        """删除用户的所有向量数据"""
        for name in ["user_preferences", "conversations", "habits", "plans"]:
            collection = self._get_collection(name)
            try:
                collection.delete(where={"user_id": user_id})
            except Exception:
                pass

    async def get_stats(self) -> dict[str, int]:
        """获取向量库统计"""
        stats = {}
        for name in ["user_preferences", "conversations", "habits", "plans"]:
            collection = self._get_collection(name)
            stats[name] = collection.count()
        return stats


# 全局实例
vector_db = VectorDB()
