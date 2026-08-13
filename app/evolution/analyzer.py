"""行为数据分析器：从行为日志中挖掘规律"""
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.behavior import BehaviorLog
from app.models.rule import UserRule


class BehaviorAnalyzer:
    """分析用户行为数据，输出统计结果供规则挖掘用"""

    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id

    async def _recent_logs(self, dimension: str | None = None, days: int = 30) -> list[BehaviorLog]:
        cutoff = datetime.utcnow() - timedelta(days=days)
        stmt = select(BehaviorLog).where(
            and_(
                BehaviorLog.user_id == self.user_id,
                BehaviorLog.created_at >= cutoff,
            )
        )
        if dimension:
            stmt = stmt.where(BehaviorLog.dimension == dimension)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def time_analysis(self) -> dict[str, Any]:
        """时间维度分析"""
        logs = await self._recent_logs("time")
        if not logs:
            return {}

        # 按时段统计完成质量
        hour_quality: dict[int, list[float]] = defaultdict(list)
        delay_count: dict[int, int] = defaultdict(int)
        for log in logs:
            h = log.hour_of_day
            if h is not None and log.value is not None:
                hour_quality[h].append(log.value)
            if log.event_data.get("is_delayed"):
                delay_count[h] += 1

        # 找出高效/低效时段
        hour_avg = {h: sum(vs) / len(vs) for h, vs in hour_quality.items() if vs}
        best_hours = sorted(hour_avg, key=hour_avg.get, reverse=True)[:3] if hour_avg else []
        worst_hours = sorted(hour_avg, key=hour_avg.get)[:3] if hour_avg else []
        delay_hotspot = max(delay_count, key=delay_count.get) if delay_count else None

        return {
            "best_hours": best_hours,
            "worst_hours": worst_hours,
            "delay_hotspot_hour": delay_hotspot,
            "delay_hotspot_count": delay_count.get(delay_hotspot, 0),
            "avg_quality": sum(hour_avg.values()) / len(hour_avg) if hour_avg else 0,
            "sample_count": len(logs),
        }

    async def consume_analysis(self) -> dict[str, Any]:
        """消费维度分析"""
        logs = await self._recent_logs("consume")
        if not logs:
            return {}

        category_amount: dict[str, list[float]] = defaultdict(list)
        impulse_count: dict[str, int] = defaultdict(int)
        for log in logs:
            cat = log.event_data.get("category", "other")
            if log.value:
                category_amount[cat].append(log.value)
            if log.event_data.get("is_impulse"):
                impulse_count[cat] += 1

        # 找出超支品类
        category_avg = {c: sum(vs) / len(vs) for c, vs in category_amount.items()}
        top_overspend = sorted(category_avg, key=category_avg.get, reverse=True)[:3]
        top_impulse = sorted(impulse_count, key=impulse_count.get, reverse=True)[:3]

        return {
            "category_avg": category_avg,
            "top_overspend_categories": top_overspend,
            "top_impulse_categories": top_impulse,
            "total_impulse": sum(impulse_count.values()),
            "sample_count": len(logs),
        }

    async def study_analysis(self) -> dict[str, Any]:
        """学习维度分析"""
        logs = await self._recent_logs("study")
        if not logs:
            return {}

        hour_eff: dict[int, list[float]] = defaultdict(list)
        delay_count = 0
        for log in logs:
            h = log.hour_of_day
            if h is not None and log.value is not None:
                hour_eff[h].append(log.value)
            if log.event_data.get("is_delayed"):
                delay_count += 1

        hour_avg = {h: sum(vs) / len(vs) for h, vs in hour_eff.items() if vs}
        best_hours = sorted(hour_avg, key=hour_avg.get, reverse=True)[:3] if hour_avg else []
        delay_rate = delay_count / len(logs) if logs else 0

        return {
            "best_hours": best_hours,
            "delay_rate": delay_rate,
            "avg_efficiency": sum(hour_avg.values()) / len(hour_avg) if hour_avg else 0,
            "sample_count": len(logs),
        }

    async def full_analysis(self) -> dict[str, Any]:
        """全维度分析"""
        time_a, consume_a, study_a = await asyncio_gather(
            self.time_analysis(),
            self.consume_analysis(),
            self.study_analysis(),
        )
        return {"time": time_a, "consume": consume_a, "study": study_a}


async def asyncio_gather(*coros):
    """兼容写法"""
    import asyncio
    return await asyncio.gather(*coros)
