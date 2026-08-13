"""规则挖掘器：统计学置信度（置信度=符合规律样本数÷总观测样本数，≥15样本）"""
from collections import defaultdict
from typing import Any

from loguru import logger
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.behavior import BehaviorLog
from app.models.rule import UserRule

MIN_SAMPLES = 15  # 最小样本数


class RuleMiner:
    """基于统计学的规则挖掘器"""

    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id

    async def _behavior_stats(self, dimension: str, days: int = 30) -> dict[str, Any]:
        """获取指定维度的统计数据"""
        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() - timedelta(days=days)

        total = await self.session.scalar(
            select(func.count(BehaviorLog.id)).where(
                and_(BehaviorLog.user_id == self.user_id, BehaviorLog.dimension == dimension, BehaviorLog.created_at >= cutoff)
            )
        )
        return {"total": total or 0}

    async def mine_time_rules(self) -> list[dict[str, Any]]:
        """挖掘时间规则"""
        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() - timedelta(days=30)
        logs = await self.session.execute(
            select(BehaviorLog).where(
                and_(BehaviorLog.user_id == self.user_id, BehaviorLog.dimension == "time", BehaviorLog.created_at >= cutoff)
            )
        )
        all_logs = logs.scalars().all()
        total = len(all_logs)
        if total < MIN_SAMPLES:
            return []

        # 按时段统计完成率和平均自评
        hour_stats: dict[int, dict] = defaultdict(lambda: {"count": 0, "completed": 0, "rating_sum": 0, "delayed": 0})
        for log in all_logs:
            h = log.hour_of_day
            if h is None:
                continue
            hour_stats[h]["count"] += 1
            if log.schedule_completed:
                hour_stats[h]["completed"] += 1
            if log.schedule_self_rating:
                hour_stats[h]["rating_sum"] += log.schedule_self_rating
            if log.schedule_is_delayed:
                hour_stats[h]["delayed"] += 1

        rules = []
        for hour, stats in hour_stats.items():
            if stats["count"] < 5:
                continue
            completion_rate = stats["completed"] / stats["count"]
            avg_rating = stats["rating_sum"] / stats["count"] if stats["rating_sum"] else 0
            delay_rate = stats["delayed"] / stats["count"]

            # 高效时段：完成率>70% 且 平均自评>=3.5
            if completion_rate > 0.7 and avg_rating >= 3.5:
                confidence = min(0.95, stats["count"] / total)
                rules.append({
                    "name": f"高效时段规则-{hour}点",
                    "dimension": "time",
                    "description": f"{hour}点完成率{completion_rate:.0%}，平均自评{avg_rating:.1f}，建议安排高难度任务",
                    "rule_expr": {"type": "schedule_hard_task", "hour": hour, "completion_rate": completion_rate},
                    "confidence": round(confidence, 3),
                    "sample_count": stats["count"],
                    "priority": 2,
                })

            # 拖延高发：拖延率>50%
            if delay_rate > 0.5:
                confidence = min(0.9, stats["count"] / total)
                rules.append({
                    "name": f"拖延矫正规则-{hour}点",
                    "dimension": "time",
                    "description": f"{hour}点拖延率{delay_rate:.0%}，需自动拆解任务+阶梯提醒",
                    "rule_expr": {"type": "split_task", "hour": hour, "delay_rate": delay_rate},
                    "confidence": round(confidence, 3),
                    "sample_count": stats["count"],
                    "priority": 3,
                })

        return rules

    async def mine_consume_rules(self) -> list[dict[str, Any]]:
        """挖掘消费规则"""
        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() - timedelta(days=30)
        logs = await self.session.execute(
            select(BehaviorLog).where(
                and_(BehaviorLog.user_id == self.user_id, BehaviorLog.dimension == "consume", BehaviorLog.created_at >= cutoff)
            )
        )
        all_logs = logs.scalars().all()
        total = len(all_logs)
        if total < MIN_SAMPLES:
            return []

        # 按品类统计
        cat_stats: dict[str, dict] = defaultdict(lambda: {"count": 0, "total_amount": 0, "impulse": 0, "necessity": 0})
        for log in all_logs:
            cat = log.event_data.get("category", "other") if log.event_data else "other"
            cat_stats[cat]["count"] += 1
            cat_stats[cat]["total_amount"] += log.value or 0
            if log.consume_is_impulse:
                cat_stats[cat]["impulse"] += 1
            if log.consume_is_necessity:
                cat_stats[cat]["necessity"] += 1

        rules = []
        for cat, stats in cat_stats.items():
            if stats["count"] < 5:
                continue
            impulse_rate = stats["impulse"] / stats["count"] if stats["impulse"] else 0
            avg_amount = stats["total_amount"] / stats["count"]

            if impulse_rate > 0.3:
                confidence = min(0.9, stats["count"] / total)
                rules.append({
                    "name": f"冲动消费预警-{cat}",
                    "dimension": "consume",
                    "description": f"品类{cat}冲动率{impulse_rate:.0%}，均值¥{avg_amount:.0f}，超支前弹窗提醒",
                    "rule_expr": {"type": "impulse_alert", "category": cat, "impulse_rate": impulse_rate, "avg_amount": avg_amount},
                    "confidence": round(confidence, 3),
                    "sample_count": stats["count"],
                    "priority": 2,
                })

        return rules

    async def mine_study_rules(self) -> list[dict[str, Any]]:
        """挖掘学习规则"""
        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() - timedelta(days=30)
        logs = await self.session.execute(
            select(BehaviorLog).where(
                and_(BehaviorLog.user_id == self.user_id, BehaviorLog.dimension == "study", BehaviorLog.created_at >= cutoff)
            )
        )
        all_logs = logs.scalars().all()
        total = len(all_logs)
        if total < MIN_SAMPLES:
            return []

        hour_stats: dict[int, dict] = defaultdict(lambda: {"count": 0, "accuracy_sum": 0, "focus_sum": 0, "delayed": 0})
        for log in all_logs:
            h = log.hour_of_day
            if h is None:
                continue
            hour_stats[h]["count"] += 1
            if log.study_accuracy:
                hour_stats[h]["accuracy_sum"] += log.study_accuracy
            if log.study_focus_min:
                hour_stats[h]["focus_sum"] += log.study_focus_min
            if log.schedule_is_delayed:
                hour_stats[h]["delayed"] += 1

        rules = []
        for hour, stats in hour_stats.items():
            if stats["count"] < 5:
                continue
            avg_accuracy = stats["accuracy_sum"] / stats["count"] if stats["accuracy_sum"] else 0
            delay_rate = stats["delayed"] / stats["count"]

            if avg_accuracy > 0.7:
                confidence = min(0.9, stats["count"] / total)
                rules.append({
                    "name": f"高效学习时段-{hour}点",
                    "dimension": "study",
                    "description": f"{hour}点正确率{avg_accuracy:.0%}，建议安排刷题/背诵",
                    "rule_expr": {"type": "study_hard", "hour": hour, "accuracy": avg_accuracy},
                    "confidence": round(confidence, 3),
                    "sample_count": stats["count"],
                    "priority": 2,
                })

            if delay_rate > 0.5:
                confidence = min(0.85, stats["count"] / total)
                rules.append({
                    "name": f"学习拖延矫正-{hour}点",
                    "dimension": "study",
                    "description": f"{hour}点拖延率{delay_rate:.0%}，自动拆分任务+降低负荷",
                    "rule_expr": {"type": "study_split", "hour": hour, "delay_rate": delay_rate, "max_chunk_min": 25},
                    "confidence": round(confidence, 3),
                    "sample_count": stats["count"],
                    "priority": 3,
                })

        return rules

    async def mine_all(self) -> list[dict[str, Any]]:
        """挖掘全部规则"""
        rules = []
        rules.extend(await self.mine_time_rules())
        rules.extend(await self.mine_consume_rules())
        rules.extend(await self.mine_study_rules())
        logger.info(f"mined {len(rules)} rules (min_samples={MIN_SAMPLES})")
        return rules
