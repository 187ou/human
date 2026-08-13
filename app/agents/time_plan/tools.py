"""时间规划工具集"""
from datetime import datetime, timedelta
from typing import Any


class TimePlanTools:
    """时间规划工具（供Agent调用）"""

    def __init__(self, user_id: int, user_rules: dict[str, Any]):
        self.user_id = user_id
        self.rules = user_rules.get("time", {})

    def parse_schedule(self, text: str) -> dict[str, Any]:
        """解析自然语言日程"""
        # 简化实现：提取时间+事项
        return {
            "title": text[:50],
            "start_time": datetime.now().isoformat(),
            "end_time": (datetime.now() + timedelta(hours=1)).isoformat(),
            "source": "manual",
        }

    def find_fragment_slots(self) -> list[dict[str, Any]]:
        """挖掘碎片时间"""
        # 基于用户作息规则
        wake = self.rules.get("wake_hour", 7)
        sleep = self.rules.get("sleep_hour", 23)
        return [
            {"slot": "morning_commute", "start": f"{wake+7}:30", "duration": 20},
            {"slot": "lunch_break", "start": "12:30", "duration": 15},
            {"slot": "evening", "start": "21:00", "duration": 25},
        ]

    def detect_conflict(self, schedules: list[dict]) -> list[dict[str, Any]]:
        """检测日程冲突"""
        conflicts = []
        sorted_s = sorted(schedules, key=lambda x: x.get("start_time", ""))
        for i in range(len(sorted_s) - 1):
            if sorted_s[i]["end_time"] > sorted_s[i + 1]["start_time"]:
                conflicts.append({
                    "a": sorted_s[i]["title"],
                    "b": sorted_s[i + 1]["title"],
                    "overlap": "时间重叠",
                })
        return conflicts

    def split_task(self, task_title: str, total_minutes: int) -> list[dict[str, Any]]:
        """拆解大任务为微任务（拖延优化）"""
        chunk = max(10, total_minutes // 4)
        subtasks = []
        remaining = total_minutes
        idx = 1
        while remaining > 0:
            dur = min(chunk, remaining)
            subtasks.append({"title": f"{task_title} ({idx})", "minutes": dur})
            remaining -= dur
            idx += 1
        return subtasks
