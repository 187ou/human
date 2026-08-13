"""消息推送API"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, get_current_user
from app.models.user import User
from app.services.notification_service import NotificationService

router = APIRouter()


@router.get("/")
async def list_notifications(
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """获取通知列表"""
    service = NotificationService(session, user.id)
    notifications = await service.get_unread_notifications(limit)
    return {"code": 0, "data": [
        {"id": n.id, "type": n.type, "source": n.source, "title": n.title,
         "content": n.content, "priority": n.priority, "is_read": n.is_read,
         "created_at": n.created_at.isoformat()}
        for n in notifications
    ]}


@router.get("/count")
async def notification_count(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """获取通知数量"""
    service = NotificationService(session, user.id)
    counts = await service.get_notification_count()
    return {"code": 0, "data": counts}


@router.post("/collect")
async def collect_notifications(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """收集所有模块的最新通知"""
    service = NotificationService(session, user.id)
    notifications = await service.collect_all_notifications()
    await session.flush()
    await session.commit()
    return {"code": 0, "data": notifications}


@router.post("/{notification_id}/read")
async def mark_read(
    notification_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """标记已读"""
    service = NotificationService(session, user.id)
    ok = await service.mark_as_read(notification_id)
    return {"code": 0 if ok else 1}


@router.post("/read-all")
async def mark_all_read(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """全部标记已读"""
    service = NotificationService(session, user.id)
    count = await service.mark_all_as_read()
    return {"code": 0, "data": {"marked": count}}
