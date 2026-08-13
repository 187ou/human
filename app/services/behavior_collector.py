"""行为观测采集服务（含结果反馈）"""
from datetime import datetime
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.behavior import BehaviorLog


class BehaviorCollector:
    """无感采集用户全维度行为数据（含结果反馈闭环）"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _add(self, **kwargs) -> BehaviorLog:
        log_entry = BehaviorLog(**kwargs)
        self.session.add(log_entry)
        await self.session.flush()
        return log_entry

    # ---- 时间规划 ----
    async def log_schedule(
        self, user_id: int, schedule_id: int,
        completed: bool = True, duration_min: int = 0,
        self_rating: int | None = None, is_delayed: bool = False,
        occurred_at: datetime | None = None,
    ) -> BehaviorLog:
        return await self._add(
            user_id=user_id, dimension="time", event_type="schedule_completed",
            event_data={"schedule_id": schedule_id, "quality": self_rating},
            value=self_rating or (1.0 if completed else 0.0),
            hour_of_day=(occurred_at or datetime.utcnow()).hour,
            day_of_week=(occurred_at or datetime.utcnow()).weekday(),
            created_at=occurred_at,
            schedule_completed=completed, schedule_duration_min=duration_min,
            schedule_self_rating=self_rating, schedule_is_delayed=is_delayed,
        )

    # ---- 学习督导 ----
    async def log_study(
        self, user_id: int, subject: str, duration_min: int,
        accuracy: float | None = None, focus_min: int | None = None,
        is_delayed: bool = False, occurred_at: datetime | None = None,
    ) -> BehaviorLog:
        return await self._add(
            user_id=user_id, dimension="study", event_type="study_session",
            event_data={"subject": subject, "is_delayed": is_delayed},
            value=accuracy,
            hour_of_day=(occurred_at or datetime.utcnow()).hour,
            day_of_week=(occurred_at or datetime.utcnow()).weekday(),
            created_at=occurred_at,
            schedule_duration_min=duration_min,
            study_accuracy=accuracy, study_focus_min=focus_min or duration_min,
            schedule_is_delayed=is_delayed,
        )

    # ---- 消费记账 ----
    async def log_consume(
        self, user_id: int, amount: float, category: str,
        is_necessity: bool | None = None, is_impulse: bool | None = None,
        occurred_at: datetime | None = None,
    ) -> BehaviorLog:
        return await self._add(
            user_id=user_id, dimension="consume", event_type="consume",
            event_data={"amount": amount, "category": category},
            value=amount,
            hour_of_day=(occurred_at or datetime.utcnow()).hour,
            day_of_week=(occurred_at or datetime.utcnow()).weekday(),
            created_at=occurred_at,
            consume_is_necessity=is_necessity, consume_is_impulse=is_impulse,
        )

    # ---- 物品收纳 ----
    async def log_item(
        self, user_id: int, item_id: int, action: str,
        occurred_at: datetime | None = None,
    ) -> BehaviorLog:
        return await self._add(
            user_id=user_id, dimension="item", event_type="item_usage",
            event_data={"item_id": item_id, "action": action},
            hour_of_day=(occurred_at or datetime.utcnow()).hour,
            day_of_week=(occurred_at or datetime.utcnow()).weekday(),
            created_at=occurred_at,
            item_action=action,
        )

    # ---- 出行 ----
    async def log_travel(
        self, user_id: int, travel_id: int, is_on_time: bool,
        occurred_at: datetime | None = None,
    ) -> BehaviorLog:
        return await self._add(
            user_id=user_id, dimension="travel", event_type="travel",
            event_data={"travel_id": travel_id, "is_on_time": is_on_time},
            value=1.0 if is_on_time else 0.0,
            hour_of_day=(occurred_at or datetime.utcnow()).hour,
            day_of_week=(occurred_at or datetime.utcnow()).weekday(),
            created_at=occurred_at,
            schedule_completed=is_on_time,
        )
