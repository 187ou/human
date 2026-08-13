"""隐性习惯挖掘引擎：发现用户自己不知道的规律"""
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.advanced import HiddenHabit
from app.models.behavior import BehaviorLog


class HiddenHabitMiner:
    """隐性习惯挖掘器

    挖掘类型：
    1. slump_timed - 特定时段极易摆烂
    2. procrastinate_trigger - 特定触发条件导致拖延
    3. energy_dip - 精力低谷期
    4. impulse_prone - 冲动消费高发期
    5. focus_window - 高效专注窗口
    """

    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id

    async def mine_hidden_habits(self) -> list[dict[str, Any]]:
        """挖掘隐性习惯"""
        cutoff = datetime.utcnow() - timedelta(days=60)
        result = await self.session.execute(
            select(BehaviorLog).where(and_(
                BehaviorLog.user_id == self.user_id,
                BehaviorLog.created_at >= cutoff,
            )).order_by(BehaviorLog.created_at)
        )
        logs = result.scalars().all()

        if len(logs) < 20:
            return []

        findings = []

        # 1. 时段摆烂检测
        slump = self._detect_timed_slump(logs)
        if slump:
            findings.append(slump)

        # 2. 拖延触发条件
        procrastinate = self._detect_procrastinate_trigger(logs)
        if procrastinate:
            findings.append(procrastinate)

        # 3. 精力低谷
        energy = self._detect_energy_dip(logs)
        if energy:
            findings.append(energy)

        # 4. 冲动消费高发
        impulse = self._detect_impulse_prone(logs)
        if impulse:
            findings.append(impulse)

        # 5. 高效窗口
        focus = self._detect_focus_window(logs)
        if focus:
            findings.append(focus)

        # 持久化
        saved = []
        for finding in findings:
            habit = HiddenHabit(
                user_id=self.user_id,
                habit_type=finding["type"],
                name=finding["name"],
                description=finding["description"],
                trigger_condition=finding["trigger"],
                effect_description=finding["effect"],
                confidence=finding["confidence"],
                sample_count=finding["samples"],
                evidence=finding.get("evidence", []),
            )
            self.session.add(habit)
            saved.append(finding)

        await self.session.flush()
        return saved

    def _detect_timed_slump(self, logs: list[BehaviorLog]) -> dict | None:
        """检测时段摆烂"""
        # 按时段统计完成率
        hour_completion = defaultdict(lambda: {"completed": 0, "total": 0})

        for log in logs:
            if log.dimension == "time" and log.schedule_completed is not None:
                hour = log.hour_of_day
                if hour is not None:
                    hour_completion[hour]["total"] += 1
                    if log.schedule_completed:
                        hour_completion[hour]["completed"] += 1

        # 找完成率<30%的时段
        slump_hours = []
        for hour, stats in hour_completion.items():
            if stats["total"] >= 3:
                rate = stats["completed"] / stats["total"]
                if rate < 0.3:
                    slump_hours.append(hour)

        if not slump_hours:
            return None

        # 合并连续时段
        slump_hours.sort()
        ranges = self._merge_consecutive_hours(slump_hours)

        if not ranges:
            return None

        best_range = max(ranges, key=lambda r: r[1] - r[0])
        start, end = best_range

        return {
            "type": "slump_timed",
            "name": f"晚间摆烂时段 {start}:00-{end+1}:00",
            "description": f"用户在{start}:00-{end+1}:00时段任务完成率极低，极易摆烂",
            "trigger": {"time_range": f"{start}:00-{end+1}:00", "type": "daily"},
            "effect": "此时段不适合安排高难度硬核任务，建议安排轻量复盘或休息",
            "confidence": 0.75,
            "samples": sum(1 for l in logs if l.hour_of_day and start <= l.hour_of_day <= end),
            "evidence": [{"hour": h, "completion_rate": hour_completion[h]["completed"] / max(hour_completion[h]["total"], 1)} for h in range(start, end + 1)],
        }

    def _detect_procrastinate_trigger(self, logs: list[BehaviorLog]) -> dict | None:
        """检测拖延触发条件"""
        # 统计拖延与前一天行为的关系
        delayed_logs = [l for l in logs if l.schedule_is_delayed == True]
        if len(delayed_logs) < 3:
            return None

        # 检查拖延是否集中在特定条件
        prev_day_late = 0
        for log in delayed_logs:
            hour = log.hour_of_day
            if hour and hour >= 22:
                prev_day_late += 1

        ratio = prev_day_late / len(delayed_logs) if delayed_logs else 0
        if ratio > 0.5:
            return {
                "type": "procrastinate_trigger",
                "name": "熬夜后拖延触发",
                "description": "用户在前一晚熬夜（22点后仍有活动）后，次日任务拖延率显著升高",
                "trigger": {"condition": "prev_day_late_night", "threshold_hour": 22},
                "effect": "熬夜后次日应降低任务量，安排轻量任务",
                "confidence": round(ratio, 3),
                "samples": len(delayed_logs),
            }
        return None

    def _detect_energy_dip(self, logs: list[BehaviorLog]) -> dict | None:
        """检测精力低谷"""
        hour_focus = defaultdict(lambda: {"focus": 0, "total": 0})

        for log in logs:
            if log.dimension == "study" and log.study_focus_min is not None:
                hour = log.hour_of_day
                if hour is not None:
                    hour_focus[hour]["focus"] += log.study_focus_min
                    hour_focus[hour]["total"] += 1

        # 找专注度最低的时段
        dip_hours = []
        for hour, stats in hour_focus.items():
            if stats["total"] >= 2:
                avg_focus = stats["focus"] / stats["total"]
                if avg_focus < 20:
                    dip_hours.append(hour)

        if dip_hours:
            return {
                "type": "energy_dip",
                "name": f"精力低谷 {min(dip_hours)}:00-{max(dip_hours)+1}:00",
                "description": f"用户在{min(dip_hours)}:00-{max(dip_hours)+1}:00专注度显著下降",
                "trigger": {"time_range": f"{min(dip_hours)}:00-{max(dip_hours)+1}:00"},
                "effect": "此时段不适合深度学习，建议安排机械性任务",
                "confidence": 0.65,
                "samples": sum(hour_focus[h]["total"] for h in dip_hours),
            }
        return None

    def _detect_impulse_prone(self, logs: list[BehaviorLog]) -> dict | None:
        """检测冲动消费高发"""
        impulse_logs = [l for l in logs if l.consume_is_impulse == True]
        if len(impulse_logs) < 3:
            return None

        hour_count = defaultdict(int)
        for log in impulse_logs:
            if log.hour_of_day is not None:
                hour_count[log.hour_of_day] += 1

        if hour_count:
            peak_hour = max(hour_count, key=hour_count.get)
            return {
                "type": "impulse_prone",
                "name": f"冲动消费高发 {peak_hour}:00",
                "description": f"用户在{peak_hour}:00左右极易产生冲动消费",
                "trigger": {"hour": peak_hour, "type": "consume"},
                "effect": "此消费时段建议增加冷静期提醒",
                "confidence": 0.7,
                "samples": hour_count[peak_hour],
            }
        return None

    def _detect_focus_window(self, logs: list[BehaviorLog]) -> dict | None:
        """检测高效专注窗口"""
        hour_accuracy = defaultdict(lambda: {"correct": 0, "total": 0})

        for log in logs:
            if log.dimension == "study" and log.study_accuracy is not None:
                hour = log.hour_of_day
                if hour is not None:
                    hour_accuracy[hour]["total"] += 1
                    hour_accuracy[hour]["correct"] += log.study_accuracy

        # 找专注度最高的时段
        best_hours = []
        for hour, stats in hour_accuracy.items():
            if stats["total"] >= 2:
                avg = stats["correct"] / stats["total"]
                if avg > 0.75:
                    best_hours.append(hour)

        if best_hours:
            return {
                "type": "focus_window",
                "name": f"高效专注窗口 {min(best_hours)}:00-{max(best_hours)+1}:00",
                "description": f"用户在{min(best_hours)}:00-{max(best_hours)+1}:00学习正确率最高",
                "trigger": {"time_range": f"{min(best_hours)}:00-{max(best_hours)+1}:00"},
                "effect": "此时段最适合安排高难度学习任务",
                "confidence": 0.8,
                "samples": sum(hour_accuracy[h]["total"] for h in best_hours),
            }
        return None

    @staticmethod
    def _merge_consecutive_hours(hours: list[int]) -> list[tuple[int, int]]:
        """合并连续时段"""
        if not hours:
            return []

        ranges = []
        start = hours[0]
        prev = hours[0]

        for h in hours[1:]:
            if h == prev + 1:
                prev = h
            else:
                ranges.append((start, prev))
                start = h
                prev = h
        ranges.append((start, prev))
        return ranges
