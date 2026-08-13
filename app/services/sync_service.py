"""多设备云端同步服务"""
import hashlib
import json
from datetime import datetime
from typing import Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.snapshot import SyncRecord


class SyncService:
    """多设备数据同步管理器"""

    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id

    async def register_device(self, device_id: str, device_name: str,
                              device_type: str = "pc") -> SyncRecord:
        """注册设备"""
        existing = await self.session.execute(
            select(SyncRecord).where(and_(
                SyncRecord.user_id == self.user_id,
                SyncRecord.device_id == device_id,
            ))
        )
        device = existing.scalar_one_or_none()
        if device:
            device.device_name = device_name
            device.last_sync_at = datetime.utcnow()
            device.is_active = True
        else:
            device = SyncRecord(
                user_id=self.user_id,
                device_id=device_id,
                device_name=device_name,
                device_type=device_type,
                sync_token=hashlib.sha256(f"{device_id}{datetime.utcnow().isoformat()}".encode()).hexdigest()[:16],
            )
            self.session.add(device)
        await self.session.flush()
        return device

    async def sync_pull(self, device_id: str, last_sync_token: str | None = None) -> dict[str, Any]:
        """拉取最新数据（从云端到设备）"""
        device = await self.session.execute(
            select(SyncRecord).where(and_(
                SyncRecord.user_id == self.user_id,
                SyncRecord.device_id == device_id,
            ))
        )
        dev = device.scalar_one_or_none()
        if not dev:
            return {"success": False, "message": "设备未注册"}

        # 生成新的同步token
        new_token = hashlib.sha256(f"{device_id}{datetime.utcnow().isoformat()}".encode()).hexdigest()[:16]
        dev.sync_token = new_token
        dev.last_sync_at = datetime.utcnow()
        await self.session.flush()

        return {
            "success": True,
            "sync_token": new_token,
            "server_time": datetime.utcnow().isoformat(),
            "data": await self._get_all_user_data(),
        }

    async def sync_push(self, device_id: str, changes: list[dict]) -> dict[str, Any]:
        """推送数据（从设备到云端）"""
        device = await self.session.execute(
            select(SyncRecord).where(and_(
                SyncRecord.user_id == self.user_id,
                SyncRecord.device_id == device_id,
            ))
        )
        dev = device.scalar_one_or_none()
        if not dev:
            return {"success": False, "message": "设备未注册"}

        dev.last_sync_at = datetime.utcnow()
        dev.changes_count += len(changes)
        await self.session.flush()

        return {
            "success": True,
            "synced_count": len(changes),
            "sync_token": dev.sync_token,
        }

    async def get_active_devices(self) -> list[SyncRecord]:
        """获取活跃设备列表"""
        result = await self.session.execute(
            select(SyncRecord).where(and_(
                SyncRecord.user_id == self.user_id,
                SyncRecord.is_active == True,
            )).order_by(SyncRecord.last_sync_at.desc())
        )
        return list(result.scalars().all())

    async def _get_all_user_data(self) -> dict[str, Any]:
        """获取用户全部数据（用于同步）"""
        from app.models.schedule import Schedule, ScheduleItem
        from app.models.consume import ConsumeRecord, Budget
        from app.models.item import Item
        from app.models.study import StudyRecord
        from app.models.travel import TravelPlan
        from app.models.rule import UserRule

        schedules = await self.session.execute(
            select(Schedule).where(Schedule.user_id == self.user_id)
        )
        items = await self.session.execute(
            select(Item).where(Item.user_id == self.user_id)
        )
        rules = await self.session.execute(
            select(UserRule).where(UserRule.user_id == self.user_id)
        )

        return {
            "schedules": [{"id": s.id, "title": s.title, "start": s.start_time.isoformat() if s.start_time else None} for s in schedules.scalars().all()],
            "items": [{"id": i.id, "name": i.name, "category": i.category} for i in items.scalars().all()],
            "rules": [{"id": r.id, "name": r.name, "version": r.version} for r in rules.scalars().all()],
            "sync_time": datetime.utcnow().isoformat(),
        }
