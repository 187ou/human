"""行为日志冷热分离服务"""
import json
import os
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, and_, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.behavior import BehaviorLog


class LogArchiver:
    """行为日志冷热分离管理"""

    HOT_DATA_DAYS = 90  # 3个月为热数据
    ARCHIVE_DIR = "archives"

    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id

    async def archive_cold_logs(self) -> dict[str, int]:
        """归档冷数据（超过90天的日志）"""
        cutoff = datetime.utcnow() - timedelta(days=self.HOT_DATA_DAYS)

        # 查询冷数据
        result = await self.session.execute(
            select(BehaviorLog).where(and_(
                BehaviorLog.user_id == self.user_id,
                BehaviorLog.created_at < cutoff,
            ))
        )
        cold_logs = result.scalars().all()

        if not cold_logs:
            return {"archived": 0, "deleted": 0}

        # 写入归档文件
        os.makedirs(self.ARCHIVE_DIR, exist_ok=True)
        archive_file = os.path.join(self.ARCHIVE_DIR, f"user_{self.user_id}_{cutoff.strftime('%Y%m')}.jsonl")

        archived_count = 0
        with open(archive_file, "a", encoding="utf-8") as f:
            for log in cold_logs:
                record = {
                    "id": log.id,
                    "dimension": log.dimension,
                    "event_type": log.event_type,
                    "event_data": log.event_data,
                    "value": log.value,
                    "hour_of_day": log.hour_of_day,
                    "day_of_week": log.day_of_week,
                    "created_at": log.created_at.isoformat(),
                    "schedule_completed": log.schedule_completed,
                    "schedule_duration_min": log.schedule_duration_min,
                    "schedule_self_rating": log.schedule_self_rating,
                    "study_accuracy": log.study_accuracy,
                    "study_focus_min": log.study_focus_min,
                    "consume_is_necessity": log.consume_is_necessity,
                    "consume_is_impulse": log.consume_is_impulse,
                    "item_action": log.item_action,
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                archived_count += 1

        # 删除已归档的热数据
        await self.session.execute(
            delete(BehaviorLog).where(and_(
                BehaviorLog.user_id == self.user_id,
                BehaviorLog.created_at < cutoff,
            ))
        )
        await self.session.flush()

        return {"archived": archived_count, "deleted": archived_count}

    async def get_hot_logs(self, dimension: str | None = None, days: int = 90) -> list[BehaviorLog]:
        """获取热数据（近90天）"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        stmt = select(BehaviorLog).where(and_(
            BehaviorLog.user_id == self.user_id,
            BehaviorLog.created_at >= cutoff,
        ))
        if dimension:
            stmt = stmt.where(BehaviorLog.dimension == dimension)
        result = await self.session.execute(stmt.order_by(BehaviorLog.created_at.desc()))
        return list(result.scalars().all())

    async def get_cold_logs(self, months_ago: int = 3) -> list[dict]:
        """获取冷数据（从归档文件读取，仅全量演化调取）"""
        archive_file = os.path.join(self.ARCHIVE_DIR, f"user_{self.user_id}_*.jsonl")
        import glob
        files = sorted(glob.glob(archive_file))

        logs = []
        for f in files[-months_ago:]:  # 只读取最近几个月的归档
            with open(f, "r", encoding="utf-8") as fh:
                for line in fh:
                    try:
                        logs.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        continue
        return logs

    async def get_all_logs_for_evolution(self, dimension: str | None = None) -> list[dict]:
        """获取全部日志（热数据+冷数据，仅供全量演化使用）"""
        # 热数据
        hot = await self.get_hot_logs(dimension, days=365)
        all_logs = []
        for log in hot:
            all_logs.append({
                "dimension": log.dimension,
                "event_type": log.event_type,
                "value": log.value,
                "hour_of_day": log.hour_of_day,
                "created_at": log.created_at.isoformat(),
                "schedule_completed": log.schedule_completed,
                "study_accuracy": log.study_accuracy,
                "consume_is_impulse": log.consume_is_impulse,
            })

        # 冷数据
        cold = await self.get_cold_logs(months_ago=12)
        if dimension:
            cold = [l for l in cold if l.get("dimension") == dimension]
        all_logs.extend(cold)

        return all_logs

    async def get_storage_stats(self) -> dict[str, Any]:
        """获取存储统计"""
        hot_count = await self.session.scalar(
            select(func.count(BehaviorLog.id)).where(and_(
                BehaviorLog.user_id == self.user_id,
                BehaviorLog.created_at >= datetime.utcnow() - timedelta(days=self.HOT_DATA_DAYS),
            ))
        )

        archive_file_pattern = os.path.join(self.ARCHIVE_DIR, f"user_{self.user_id}_*.jsonl")
        import glob
        archive_files = glob.glob(archive_file_pattern)
        cold_count = 0
        for f in archive_files:
            with open(f, "r", encoding="utf-8") as fh:
                cold_count += sum(1 for _ in fh)

        return {
            "hot_logs": hot_count or 0,
            "cold_logs": cold_count,
            "archive_files": len(archive_files),
            "hot_data_days": self.HOT_DATA_DAYS,
        }
