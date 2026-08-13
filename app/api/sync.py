"""多设备同步API"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, get_current_user
from app.models.user import User
from app.services.sync_service import SyncService

router = APIRouter()


class DeviceRegister(BaseModel):
    device_id: str
    device_name: str
    device_type: str = "pc"


class SyncPushRequest(BaseModel):
    changes: list[dict] = []


@router.post("/register")
async def register_device(
    data: DeviceRegister,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """注册设备"""
    service = SyncService(session, user.id)
    device = await service.register_device(data.device_id, data.device_name, data.device_type)
    await session.commit()
    return {"code": 0, "data": {"sync_token": device.sync_token}}


@router.get("/pull")
async def sync_pull(
    device_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """拉取最新数据"""
    service = SyncService(session, user.id)
    result = await service.sync_pull(device_id)
    await session.commit()
    return {"code": 0 if result["success"] else 1, "data": result}


@router.post("/push")
async def sync_push(
    device_id: str,
    data: SyncPushRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """推送数据变更"""
    service = SyncService(session, user.id)
    result = await service.sync_push(device_id, data.changes)
    await session.commit()
    return {"code": 0 if result["success"] else 1, "data": result}


@router.get("/devices")
async def list_devices(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """获取活跃设备"""
    service = SyncService(session, user.id)
    devices = await service.get_active_devices()
    return {"code": 0, "data": [
        {"device_id": d.device_id, "name": d.device_name, "type": d.device_type,
         "last_sync": d.last_sync_at.isoformat(), "is_active": d.is_active}
        for d in devices
    ]}
