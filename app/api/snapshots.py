"""演化快照API"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, get_current_user
from app.models.user import User
from app.services.snapshot_service import SnapshotService

router = APIRouter()


@router.post("/create")
async def create_snapshot(
    description: str | None = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """创建演化快照"""
    service = SnapshotService(session, user.id)
    snap = await service.create_snapshot("full", description)
    await session.commit()
    return {"code": 0, "data": {"version": snap.version, "rules_count": snap.rules_count}}


@router.get("/list")
async def list_snapshots(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """获取快照列表"""
    service = SnapshotService(session, user.id)
    snapshots = await service.list_snapshots()
    return {"code": 0, "data": [
        {"version": s.version, "type": s.snapshot_type, "rules_count": s.rules_count,
         "confidence_avg": s.confidence_avg, "description": s.description,
         "created_at": s.created_at.isoformat()}
        for s in snapshots
    ]}


@router.post("/rollback/{version}")
async def rollback_snapshot(
    version: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """回滚到指定版本"""
    service = SnapshotService(session, user.id)
    result = await service.rollback_to_version(version)
    await session.commit()
    return {"code": 0 if result["success"] else 1, "data": result}
