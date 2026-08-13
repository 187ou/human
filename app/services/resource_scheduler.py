"""资源统一调度中枢：时间+精力+金钱+物品四维智能分配"""
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, and_, func, Integer
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fsm import ResourceAllocation


class ResourceScheduler:
    """四维资源统一调度器

    调度维度：
    1. 时间 - 日程密度、学习时长、休闲时长
    2. 精力 - 高难度任务窗口、休息缓冲
    3. 金钱 - 各品类预算分配
    4. 物品 - 囤货预警、闲置处理
    """

    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id

    async def generate_allocation(self, target_date: datetime | None = None) -> dict[str, Any]:
        """生成资源分配方案"""
        if not target_date:
            target_date = datetime.utcnow()

        date_str = target_date.strftime('%Y-%m-%d')

        # 获取精力值
        energy = await self._get_energy(target_date)

        # 获取当前状态
        scene_state = await self._get_scene_state()

        # 四维分配
        time_alloc = self._allocate_time(energy, scene_state)
        energy_alloc = self._allocate_energy(energy)
        money_alloc = self._allocate_money(scene_state)
        item_alloc = await self._allocate_items()

        # 计算总分
        total_score = (
            time_alloc.get("score", 0) * 0.25 +
            energy_alloc.get("score", 0) * 0.25 +
            money_alloc.get("score", 0) * 0.25 +
            item_alloc.get("score", 0) * 0.25
        )

        # 记录
        alloc = ResourceAllocation(
            user_id=self.user_id,
            allocation_date=date_str,
            time_alloc=time_alloc,
            energy_alloc=energy_alloc,
            money_alloc=money_alloc,
            item_alloc=item_alloc,
            strategy=scene_state or "balanced",
            total_score=round(total_score, 1),
        )
        self.session.add(alloc)
        await self.session.flush()

        return {
            "date": date_str,
            "time": time_alloc,
            "energy": energy_alloc,
            "money": money_alloc,
            "items": item_alloc,
            "total_score": round(total_score, 1),
        }

    async def _get_energy(self, target_date: datetime) -> float:
        """获取精力值"""
        from app.models.innovation import EnergyRecord
        date_str = target_date.strftime('%Y-%m-%d')
        result = await self.session.execute(
            select(EnergyRecord).where(and_(
                EnergyRecord.user_id == self.user_id,
                EnergyRecord.record_date == date_str,
            ))
        )
        record = result.scalar_one_or_none()
        return record.total_energy if record else 50.0

    async def _get_scene_state(self) -> str:
        """获取当前状态"""
        from app.models.fsm import LifeSceneState
        result = await self.session.execute(
            select(LifeSceneState).where(and_(
                LifeSceneState.user_id == self.user_id,
                LifeSceneState.is_active == True,
            )).order_by(LifeSceneState.created_at.desc()).limit(1)
        )
        state = result.scalar_one_or_none()
        return state.current_state if state else "daily"

    def _allocate_time(self, energy: float, scene: str) -> dict:
        """时间分配"""
        if energy >= 75:
            return {"study_hours": 4, "work_hours": 6, "rest_hours": 2, "leisure_hours": 2, "score": 90}
        elif energy >= 45:
            return {"study_hours": 2, "work_hours": 6, "rest_hours": 3, "leisure_hours": 2, "score": 70}
        else:
            return {"study_hours": 1, "work_hours": 4, "rest_hours": 4, "leisure_hours": 2, "score": 50}

    def _allocate_energy(self, energy: float) -> dict:
        """精力分配"""
        if energy >= 75:
            return {"hard_tasks": 3, "medium_tasks": 3, "easy_tasks": 2, "score": 90}
        elif energy >= 45:
            return {"hard_tasks": 1, "medium_tasks": 3, "easy_tasks": 3, "score": 70}
        else:
            return {"hard_tasks": 0, "medium_tasks": 2, "easy_tasks": 4, "score": 50}

    def _allocate_money(self, scene: str) -> dict:
        """金钱分配"""
        allocations = {
            "daily": {"food": 100, "transport": 30, "entertainment": 50, "study": 30, "score": 80},
            "exam": {"food": 80, "transport": 20, "entertainment": 20, "study": 80, "score": 70},
            "travel": {"food": 150, "transport": 100, "entertainment": 30, "study": 10, "score": 60},
            "vacation": {"food": 120, "transport": 50, "entertainment": 200, "study": 0, "score": 90},
            "sick": {"food": 60, "medical": 200, "transport": 10, "entertainment": 10, "score": 40},
            "overtime": {"food": 120, "transport": 30, "entertainment": 20, "study": 10, "score": 50},
        }
        return allocations.get(scene, allocations["daily"])

    async def _allocate_items(self) -> dict:
        """物品分配"""
        from app.models.item import Item
        result = await self.session.execute(
            select(func.count(Item.id), func.sum(func.cast(Item.is_idle == True, Integer))).where(
                Item.user_id == self.user_id
            )
        )
        row = result.one()
        total = row[0] or 0
        idle = row[1] or 0

        return {
            "total_items": total,
            "idle_items": idle,
            "hoarding_risk": "high" if idle > 5 else "medium" if idle > 2 else "low",
            "suggested_dispose": max(0, idle - 3),
            "score": max(0, 100 - idle * 10),
        }
