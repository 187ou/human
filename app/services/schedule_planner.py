"""时间规划服务：冲突检测、突发场景、例外日程、熬夜适配"""
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schedule import Schedule, RecurringException
from app.models.user import User


class SchedulePlanner:
    """时间规划引擎"""

    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id

    # ==================== 冲突检测 ====================

    async def detect_conflicts(self, target_date: datetime | None = None) -> list[dict[str, Any]]:
        """检测日程时间重叠冲突"""
        if not target_date:
            target_date = datetime.utcnow()

        start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)

        result = await self.session.execute(
            select(Schedule).where(
                and_(
                    Schedule.user_id == self.user_id,
                    Schedule.is_paused == False,
                    Schedule.start_time >= start,
                    Schedule.start_time < end,
                )
            ).order_by(Schedule.start_time)
        )
        schedules = result.scalars().all()

        conflicts = []
        for i in range(len(schedules) - 1):
            a = schedules[i]
            b = schedules[i + 1]
            if a.end_time > b.start_time:
                overlap_min = (a.end_time - b.start_time).total_seconds() / 60
                conflicts.append({
                    "schedule_a": {"id": a.id, "title": a.title, "start": a.start_time.isoformat(), "end": a.end_time.isoformat()},
                    "schedule_b": {"id": b.id, "title": b.title, "start": b.start_time.isoformat(), "end": b.end_time.isoformat()},
                    "overlap_minutes": round(overlap_min, 1),
                })
        return conflicts

    async def suggest_fragment_slots(self, target_date: datetime | None = None) -> list[dict[str, Any]]:
        """挖掘碎片时间并提供挪位方案"""
        user = await self.session.get(User, self.user_id)
        wake = user.wake_hour if user else 7
        sleep = user.sleep_hour if user else 23
        commute = user.commute_minutes if user else 30

        if not target_date:
            target_date = datetime.utcnow()

        start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)

        result = await self.session.execute(
            select(Schedule).where(
                and_(
                    Schedule.user_id == self.user_id,
                    Schedule.is_paused == False,
                    Schedule.start_time >= start,
                    Schedule.start_time < end,
                )
            ).order_by(Schedule.start_time)
        )
        schedules = result.scalars().all()

        # 计算空闲时段
        slots = []
        day_start = start.replace(hour=wake)
        day_end = start.replace(hour=sleep if sleep > wake else sleep + 24)

        prev_end = day_start
        for s in schedules:
            if s.start_time > prev_end:
                gap_min = (s.start_time - prev_end).total_seconds() / 60
                if gap_min >= 15:
                    slots.append({
                        "start": prev_end.isoformat(),
                        "end": s.start_time.isoformat(),
                        "minutes": round(gap_min, 1),
                        "slot_type": self._classify_slot(prev_end, commute),
                    })
            prev_end = max(prev_end, s.end_time)

        # 检查末尾空闲
        if prev_end < day_end:
            gap_min = (day_end - prev_end).total_seconds() / 60
            if gap_min >= 15:
                slots.append({
                    "start": prev_end.isoformat(),
                    "end": day_end.isoformat(),
                    "minutes": round(gap_min, 1),
                    "slot_type": "evening",
                })

        return slots

    @staticmethod
    def _classify_slot(dt: datetime, commute: int) -> str:
        """分类时段类型"""
        hour = dt.hour
        if hour <= 9:
            return "morning_commute" if commute > 0 else "morning"
        elif hour <= 12:
            return "forenoon"
        elif hour <= 14:
            return "lunch"
        elif hour <= 18:
            return "afternoon"
        else:
            return "evening"

    # ==================== 突发场景 ====================

    async def emergency_pause(self, reason: str = "general") -> dict[str, Any]:
        """一键暂停所有未完成的未来日程"""
        now = datetime.utcnow()
        result = await self.session.execute(
            select(Schedule).where(
                and_(
                    Schedule.user_id == self.user_id,
                    Schedule.is_completed == False,
                    Schedule.is_paused == False,
                    Schedule.start_time >= now,
                )
            )
        )
        paused_count = 0
        for s in result.scalars().all():
            s.original_start = s.start_time
            s.is_paused = True
            paused_count += 1

        await self.session.commit()
        return {"action": "pause", "reason": reason, "paused_count": paused_count}

    async def emergency_postpone(self, delay_hours: int = 2, reason: str = "general") -> dict[str, Any]:
        """一键顺延所有未完成的未来日程"""
        now = datetime.utcnow()
        result = await self.session.execute(
            select(Schedule).where(
                and_(
                    Schedule.user_id == self.user_id,
                    Schedule.is_completed == False,
                    Schedule.start_time >= now,
                )
            ).order_by(Schedule.start_time)
        )
        postponed_count = 0
        for s in result.scalars().all():
            s.start_time = s.start_time + timedelta(hours=delay_hours)
            s.end_time = s.end_time + timedelta(hours=delay_hours)
            s.is_paused = False
            postponed_count += 1

        await self.session.commit()
        return {"action": "postpone", "reason": reason, "delay_hours": delay_hours, "postponed_count": postponed_count}

    async def resume_all(self) -> dict[str, Any]:
        """恢复所有暂停的日程到原始时间"""
        result = await self.session.execute(
            select(Schedule).where(
                and_(Schedule.user_id == self.user_id, Schedule.is_paused == True)
            )
        )
        resumed_count = 0
        for s in result.scalars().all():
            if s.original_start:
                duration = s.end_time - s.start_time
                s.start_time = s.original_start
                s.end_time = s.original_start + duration
                s.original_start = None
                s.is_paused = False
                resumed_count += 1

        await self.session.commit()
        return {"action": "resume", "resumed_count": resumed_count}

    # ==================== 周期性例外 ====================

    async def add_recurring_exception(self, title: str, rule_expr: dict, effective_from: datetime,
                                       effective_until: datetime | None = None, description: str | None = None) -> RecurringException:
        """添加周期性例外日程"""
        exc = RecurringException(
            user_id=self.user_id,
            title=title,
            description=description,
            rule_expr=rule_expr,
            effective_from=effective_from,
            effective_until=effective_until,
            is_active=True,
        )
        self.session.add(exc)
        await self.session.flush()
        return exc

    async def apply_recurring_exceptions(self, target_date: datetime | None = None) -> list[dict[str, Any]]:
        """将周期性例外应用到指定日期的日程"""
        if not target_date:
            target_date = datetime.utcnow()

        weekday = target_date.weekday()  # 0=Monday
        result = await self.session.execute(
            select(RecurringException).where(
                and_(
                    RecurringException.user_id == self.user_id,
                    RecurringException.is_active == True,
                    RecurringException.effective_from <= target_date,
                )
            )
        )

        applied = []
        for exc in result.scalars().all():
            if exc.effective_until and exc.effective_until < target_date:
                continue
            rule = exc.rule_expr
            days = rule.get("days_of_week", [])
            if weekday in days:
                applied.append({
                    "exception_id": exc.id,
                    "title": exc.title,
                    "action": rule.get("action", "add"),
                    "start_time": rule.get("start_time"),
                    "end_time": rule.get("end_time"),
                })

        return applied

    # ==================== 熬夜检测 ====================

    async def detect_late_night(self, target_date: datetime | None = None) -> dict[str, Any]:
        """检测前一日熬夜情况"""
        if not target_date:
            target_date = datetime.utcnow()

        user = await self.session.get(User, self.user_id)
        sleep_hour = user.sleep_hour if user else 23

        # 查找前一日晚于睡觉时间的日程
        prev_day_start = (target_date - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        late_threshold = prev_day_start.replace(hour=sleep_hour)

        result = await self.session.execute(
            select(Schedule).where(
                and_(
                    Schedule.user_id == self.user_id,
                    Schedule.end_time >= late_threshold,
                    Schedule.start_time >= prev_day_start,
                )
            ).order_by(Schedule.end_time.desc())
        )
        late_schedules = result.scalars().all()

        if not late_schedules:
            return {"is_late": False, "latest_end": None, "adjustment_factor": 1.0}

        latest = late_schedules[0].end_time
        late_hours = (latest - late_threshold).total_seconds() / 3600

        # 熬夜因子：越晚越低（最低0.5）
        factor = max(0.5, 1.0 - late_hours * 0.1)

        return {
            "is_late": True,
            "latest_end": latest.isoformat(),
            "late_hours": round(late_hours, 1),
            "adjustment_factor": round(factor, 2),
            "message": f"检测到熬夜（最晚{latest.strftime('%H:%M')}），建议今日任务量下调{round((1 - factor) * 100)}%",
        }

    async def get_adjusted_task_load(self, target_date: datetime | None = None) -> dict[str, Any]:
        """获取调整后的任务负荷建议"""
        late_info = await self.detect_late_night(target_date)
        factor = late_info.get("adjustment_factor", 1.0)

        if not target_date:
            target_date = datetime.utcnow()

        start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)

        result = await self.session.execute(
            select(func.count(Schedule.id), func.coalesce(func.sum(
                func.strftime('%s', Schedule.end_time) - func.strftime('%s', Schedule.start_time)
            ), 0)).where(
                and_(
                    Schedule.user_id == self.user_id,
                    Schedule.is_completed == False,
                    Schedule.is_paused == False,
                    Schedule.start_time >= start,
                    Schedule.start_time < end,
                )
            )
        )
        row = result.one()
        total_count = row[0]
        total_seconds = row[1] or 0
        total_hours = total_seconds / 3600

        return {
            "original_count": total_count,
            "original_hours": round(total_hours, 1),
            "adjusted_count": max(1, int(total_count * factor)),
            "adjusted_hours": round(total_hours * factor, 1),
            "adjustment_factor": factor,
            "late_night_info": late_info,
        }
