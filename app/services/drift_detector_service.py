"""用户偏好漂移检测引擎"""
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evolution import PreferenceDriftRecord
from app.models.behavior import BehaviorLog
from app.models.rule import UserRule


class DriftDetector:
    """用户偏好漂移检测器

    检测生活习惯的显著变化：
    - 从摆烂变自律（学习时长显著增加）
    - 从自律变摆烂（完成率显著下降）
    - 从宅家变社交（出行频率增加）
    - 从节俭变消费（消费金额增加）
    """

    # 漂移阈值
    DRIFT_THRESHOLD = 0.3  # 变化超过30%视为漂移
    MIN_SAMPLES = 7  # 最少需要7天数据

    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id

    async def detect_drift(self) -> list[dict[str, Any]]:
        """检测偏好漂移"""
        drifts = []

        # 分前后两半对比
        now = datetime.utcnow()
        mid = now - timedelta(days=15)
        early_start = now - timedelta(days=30)

        # 获取早期数据（15-30天前）
        early = await self._get_period_stats(early_start, mid)
        # 获取近期数据（近15天）
        recent = await self._get_period_stats(mid, now)

        if not early or not recent:
            return []

        # 检测各维度漂移
        dimensions = ["study", "consume", "schedule"]
        for dim in dimensions:
            drift = self._compare_periods(dim, early, recent)
            if drift and drift["is_drift"]:
                drifts.append(drift)

        # 持久化并处理
        saved = []
        for drift in drifts:
            # 重置相关旧规则
            reset_rules = await self._reset_stale_rules(drift["dimension"])

            record = PreferenceDriftRecord(
                user_id=self.user_id,
                drift_type=drift["type"],
                dimension=drift["dimension"],
                drift_score=drift["score"],
                old_pattern=drift["old"],
                new_pattern=drift["new"],
                rules_reset=reset_rules,
                is_handled=len(reset_rules) > 0,
            )
            self.session.add(record)
            drift["rules_reset"] = reset_rules
            saved.append(drift)

        await self.session.flush()
        return saved

    async def _get_period_stats(self, start: datetime, end: datetime) -> dict:
        """获取时间段统计"""
        start_str = start.strftime('%Y-%m-%d')
        end_str = end.strftime('%Y-%m-%d')

        result = await self.session.execute(
            select(
                BehaviorLog.dimension,
                func.count(BehaviorLog.id),
                func.avg(BehaviorLog.value),
            ).where(and_(
                BehaviorLog.user_id == self.user_id,
                func.strftime('%Y-%m-%d', BehaviorLog.created_at) >= start_str,
                func.strftime('%Y-%m-%d', BehaviorLog.created_at) < end_str,
            )).group_by(BehaviorLog.dimension)
        )

        stats = {}
        for row in result.all():
            stats[row[0]] = {"count": row[1], "avg_value": float(row[2] or 0)}
        return stats

    def _compare_periods(self, dimension: str, early: dict, recent: dict) -> dict | None:
        """对比两个时期的数据"""
        early_stat = early.get(dimension)
        recent_stat = recent.get(dimension)

        if not early_stat or not recent_stat:
            return None

        if early_stat["count"] < self.MIN_SAMPLES // 2:
            return None

        # 计算变化率
        old_avg = early_stat["avg_value"]
        new_avg = recent_stat["avg_value"]

        if old_avg == 0:
            change_rate = 1.0 if new_avg > 0 else 0
        else:
            change_rate = abs(new_avg - old_avg) / old_avg

        is_drift = change_rate > self.DRIFT_THRESHOLD

        if not is_drift:
            return None

        # 判定漂移类型
        direction = "increase" if new_avg > old_avg else "decrease"

        drift_types = {
            ("study", "increase"): "slump_to_discipline",
            ("study", "decrease"): "discipline_to_slump",
            ("consume", "increase"): "frugal_to_spending",
            ("consume", "decrease"): "spending_to_frugal",
            ("schedule", "increase"): "homebody_to_social",
            ("schedule", "decrease"): "social_to_homebody",
        }

        drift_type = drift_types.get((dimension, direction), f"{dimension}_{direction}")

        return {
            "is_drift": True,
            "type": drift_type,
            "dimension": dimension,
            "score": round(min(1.0, change_rate), 3),
            "old": f"均值{old_avg:.1f}",
            "new": f"均值{new_avg:.1f}",
            "change_rate": round(change_rate, 3),
        }

    async def _reset_stale_rules(self, dimension: str) -> list[int]:
        """重置过时规则"""
        dim_map = {
            "study": "study",
            "consume": "consume",
            "schedule": "time",
        }
        rule_dim = dim_map.get(dimension, dimension)

        result = await self.session.execute(
            select(UserRule).where(and_(
                UserRule.user_id == self.user_id,
                UserRule.dimension == rule_dim,
                UserRule.is_active == True,
            ))
        )
        rules = result.scalars().all()

        reset_ids = []
        for rule in rules:
            rule.is_active = False
            reset_ids.append(rule.id)

        return reset_ids
