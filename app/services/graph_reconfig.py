"""LangGraph图结构动态自重构引擎

根据用户场景变化，自主调整多Agent流转节点、分支条件、调度权重。
"""
from datetime import datetime
from typing import Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.team import GraphNodeConfig


class GraphReconfigurator:
    """LangGraph动态重构器"""

    # 场景→图配置映射
    SCENE_CONFIGS = {
        "exam": {
            "study": {"weight": 3.0, "priority": 3},
            "time_plan": {"weight": 1.5, "priority": 2},
            "consume": {"weight": 0.5, "priority": 1},
            "travel": {"weight": 0.2, "priority": 1},
            "item": {"weight": 0.5, "priority": 1},
        },
        "vacation": {
            "study": {"weight": 0.2, "priority": 1},
            "time_plan": {"weight": 0.5, "priority": 1},
            "consume": {"weight": 2.0, "priority": 3},
            "travel": {"weight": 3.0, "priority": 3},
            "item": {"weight": 1.0, "priority": 2},
        },
        "sick": {
            "study": {"weight": 0.0, "priority": 1},
            "time_plan": {"weight": 0.3, "priority": 1},
            "consume": {"weight": 0.5, "priority": 2},
            "travel": {"weight": 0.0, "priority": 1},
            "item": {"weight": 1.5, "priority": 3},
        },
        "daily": {
            "study": {"weight": 1.0, "priority": 2},
            "time_plan": {"weight": 1.5, "priority": 3},
            "consume": {"weight": 1.0, "priority": 2},
            "travel": {"weight": 0.5, "priority": 1},
            "item": {"weight": 0.5, "priority": 1},
        },
    }

    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id

    async def reconfigure_for_scene(self, scene: str) -> dict[str, Any]:
        """根据场景重构图"""
        config = self.SCENE_CONFIGS.get(scene, self.SCENE_CONFIGS["daily"])

        changes = []
        for node_name, node_config in config.items():
            db_config = await self._get_or_create_node(node_name)
            old_weight = db_config.weight
            old_priority = db_config.priority

            db_config.weight = node_config["weight"]
            db_config.priority = node_config["priority"]
            db_config.is_active = node_config["weight"] > 0

            if old_weight != db_config.weight:
                changes.append({
                    "node": node_name,
                    "old_weight": old_weight,
                    "new_weight": db_config.weight,
                    "new_priority": db_config.priority,
                })

        await self.session.flush()
        return {"scene": scene, "changes": changes}

    async def get_current_config(self) -> dict[str, Any]:
        """获取当前图配置"""
        result = await self.session.execute(
            select(GraphNodeConfig).where(and_(
                GraphNodeConfig.user_id == self.user_id,
                GraphNodeConfig.is_active == True,
            )).order_by(GraphNodeConfig.priority.desc())
        )
        nodes = result.scalars().all()

        return {
            "nodes": [{"name": n.node_name, "weight": n.weight, "priority": n.priority} for n in nodes],
        }

    async def _get_or_create_node(self, node_name: str) -> GraphNodeConfig:
        """获取或创建节点配置"""
        result = await self.session.execute(
            select(GraphNodeConfig).where(and_(
                GraphNodeConfig.user_id == self.user_id,
                GraphNodeConfig.node_name == node_name,
            ))
        )
        node = result.scalar_one_or_none()

        if not node:
            node = GraphNodeConfig(
                user_id=self.user_id,
                node_name=node_name,
                node_type="agent" if node_name != "router" else "router",
            )
            self.session.add(node)
            await self.session.flush()

        return node
