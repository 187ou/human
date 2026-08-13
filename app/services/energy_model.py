"""用户精力动态建模：四维精力评估"""
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, and_, Integer, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.innovation import EnergyRecord
from app.models.behavior import BehaviorLog


class EnergyModel:
    """四维精力动态模型

    维度：
    1. 睡眠质量 (sleep_score) - 基于睡眠时长、入睡时间
    2. 昨日负荷 (load_score) - 基于昨日任务量、学习时长
    3. 完成率 (completion_score) - 基于近期任务完成率
    4. 专注度 (focus_score) - 基于有效专注时长占比

    综合精力 = 睡眠*0.3 + 负荷反向*0.25 + 完成率*0.25 + 专注度*0.2
    """

    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id

    async def calculate_daily_energy(self, target_date: datetime | None = None) -> EnergyRecord:
        """计算指定日期的精力值"""
        if not target_date:
            target_date = datetime.utcnow()

        date_str = target_date.strftime('%Y-%m-%d')
        yesterday = target_date - timedelta(days=1)
        yesterday_str = yesterday.strftime('%Y-%m-%d')

        # 1. 睡眠质量得分
        sleep_score = await self._calc_sleep_score(target_date)

        # 2. 昨日负荷得分（负荷越低得分越高）
        load_score = await self._calc_load_score(yesterday)

        # 3. 完成率得分
        completion_score = await self._calc_completion_score(yesterday)

        # 4. 专注度得分
        focus_score = await self._calc_focus_score(yesterday)

        # 综合精力值（加权）
        total_energy = (
            sleep_score * 0.30 +
            (100 - load_score) * 0.25 +  # 负荷反向
            completion_score * 0.25 +
            focus_score * 0.20
        )

        # 精力等级
        if total_energy >= 75:
            energy_level = "high"
        elif total_energy >= 45:
            energy_level = "medium"
        else:
            energy_level = "low"

        # 影响因素
        factors = {
            "sleep": round(sleep_score, 1),
            "load": round(load_score, 1),
            "completion": round(completion_score, 1),
            "focus": round(focus_score, 1),
        }

        # 查找或创建记录
        existing = await self.session.execute(
            select(EnergyRecord).where(and_(
                EnergyRecord.user_id == self.user_id,
                EnergyRecord.record_date == date_str,
            ))
        )
        record = existing.scalar_one_or_none()

        if record:
            record.sleep_score = sleep_score
            record.load_score = load_score
            record.completion_score = completion_score
            record.focus_score = focus_score
            record.total_energy = total_energy
            record.energy_level = energy_level
            record.factors = factors
        else:
            record = EnergyRecord(
                user_id=self.user_id,
                record_date=date_str,
                sleep_score=sleep_score,
                load_score=load_score,
                completion_score=completion_score,
                focus_score=focus_score,
                total_energy=total_energy,
                energy_level=energy_level,
                factors=factors,
            )
            self.session.add(record)

        await self.session.flush()
        return record

    async def _calc_sleep_score(self, target_date: datetime) -> float:
        """计算睡眠质量得分"""
        from app.models.user import User
        user = await self.session.get(User, self.user_id)
        if not user:
            return 50.0

        sleep_hour = user.sleep_hour
        wake_hour = user.wake_hour

        # 计算睡眠时长
        if sleep_hour > wake_hour:
            sleep_duration = sleep_hour - wake_hour
        else:
            sleep_duration = (24 - wake_hour) + sleep_hour

        # 理想睡眠7-9小时
        if 7 <= sleep_duration <= 9:
            return 90.0
        elif 6 <= sleep_duration < 7 or 9 < sleep_duration <= 10:
            return 70.0
        elif 5 <= sleep_duration < 6:
            return 50.0
        else:
            return 30.0

    async def _calc_load_score(self, yesterday: datetime) -> float:
        """计算昨日负荷得分（值越高=负荷越重）"""
        yesterday_str = yesterday.strftime('%Y-%m-%d')

        result = await self.session.execute(
            select(
                func.coalesce(func.sum(BehaviorLog.schedule_duration_min), 0),
                func.count(BehaviorLog.id),
            ).where(and_(
                BehaviorLog.user_id == self.user_id,
                func.strftime('%Y-%m-%d', BehaviorLog.created_at) == yesterday_str,
            ))
        )
        row = result.one()
        total_minutes = float(row[0] or 0)
        event_count = row[1] or 0

        load = total_minutes / 10 + event_count * 2
        return min(100.0, load)

    async def _calc_completion_score(self, yesterday: datetime) -> float:
        """计算完成率得分"""
        yesterday_str = yesterday.strftime('%Y-%m-%d')

        result = await self.session.execute(
            select(
                func.count(BehaviorLog.id),
                func.sum(func.cast(BehaviorLog.schedule_completed, Integer)),
            ).where(and_(
                BehaviorLog.user_id == self.user_id,
                BehaviorLog.dimension == "time",
                func.strftime('%Y-%m-%d', BehaviorLog.created_at) == yesterday_str,
            ))
        )
        row = result.one()
        total = row[0] or 0
        completed = row[1] or 0

        return (completed / total * 100) if total > 0 else 50.0

    async def _calc_focus_score(self, yesterday: datetime) -> float:
        """计算专注度得分"""
        yesterday_str = yesterday.strftime('%Y-%m-%d')

        result = await self.session.execute(
            select(
                func.coalesce(func.sum(BehaviorLog.schedule_duration_min), 0),
                func.coalesce(func.sum(BehaviorLog.study_focus_min), 0),
            ).where(and_(
                BehaviorLog.user_id == self.user_id,
                func.strftime('%Y-%m-%d', BehaviorLog.created_at) == yesterday_str,
            ))
        )
        row = result.one()
        total = float(row[0] or 0)
        focus = float(row[1] or 0)

        return (focus / total * 100) if total > 0 else 50.0

    async def get_energy_trend(self, days: int = 7) -> list[EnergyRecord]:
        """获取精力趋势"""
        cutoff = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')
        result = await self.session.execute(
            select(EnergyRecord).where(and_(
                EnergyRecord.user_id == self.user_id,
                EnergyRecord.record_date >= cutoff,
            )).order_by(EnergyRecord.record_date)
        )
        return list(result.scalars().all())

    async def get_task_recommendation(self) -> dict[str, Any]:
        """基于精力值的任务推荐"""
        energy = await self.calculate_daily_energy()

        if energy.energy_level == "high":
            return {
                "level": "high",
                "energy": energy.total_energy,
                "recommendation": "精力充沛，适合安排高难度任务",
                "max_tasks": 8,
                "suggested_difficulty": "hard",
                "focus_blocks": 4,
            }
        elif energy.energy_level == "medium":
            return {
                "level": "medium",
                "energy": energy.total_energy,
                "recommendation": "精力适中，建议均衡安排任务",
                "max_tasks": 5,
                "suggested_difficulty": "medium",
                "focus_blocks": 3,
            }
        else:
            return {
                "level": "low",
                "energy": energy.total_energy,
                "recommendation": "精力较低，建议轻量任务+适当休息",
                "max_tasks": 3,
                "suggested_difficulty": "easy",
                "focus_blocks": 2,
                "rest_reminder": True,
            }


