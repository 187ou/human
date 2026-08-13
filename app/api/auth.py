"""角色选择API（无需登录注册，直接选角色）"""
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.user import User
from app.utils.auth import create_access_token

router = APIRouter()


class SelectRoleRequest(BaseModel):
    user_id: int


async def get_current_user(
    authorization: str | None = Header(None),
    session: AsyncSession = Depends(get_db),
) -> User:
    from app.utils.auth import decode_access_token
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未选择角色")
    token = authorization.replace("Bearer ", "")
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token无效")
    result = await session.execute(select(User).where(User.id == int(payload["sub"])))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


@router.get("/roles")
async def list_roles(session: AsyncSession = Depends(get_db)):
    """获取所有可用角色"""
    result = await session.execute(select(User).order_by(User.id))
    users = result.scalars().all()
    return {"code": 0, "data": [
        {"id": u.id, "username": u.username, "user_type": u.user_type}
        for u in users
    ]}


@router.post("/select")
async def select_role(data: SelectRoleRequest, session: AsyncSession = Depends(get_db)):
    """选择角色"""
    result = await session.execute(select(User).where(User.id == data.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="角色不存在")
    token = create_access_token({"sub": str(user.id)})
    return {"code": 0, "data": {
        "access_token": token,
        "user": {"id": user.id, "username": user.username, "user_type": user.user_type},
    }}


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    return {"code": 0, "data": {
        "id": user.id, "username": user.username, "user_type": user.user_type,
        "wake_hour": user.wake_hour, "sleep_hour": user.sleep_hour,
        "commute_minutes": user.commute_minutes,
    }}


class UserProfileUpdate(BaseModel):
    wake_hour: int | None = None
    sleep_hour: int | None = None
    commute_minutes: int | None = None


@router.put("/profile")
async def update_profile(
    data: UserProfileUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """更新用户基础信息（起床/睡觉/通勤）"""
    if data.wake_hour is not None:
        user.wake_hour = max(0, min(23, data.wake_hour))
    if data.sleep_hour is not None:
        user.sleep_hour = max(0, min(23, data.sleep_hour))
    if data.commute_minutes is not None:
        user.commute_minutes = max(0, min(180, data.commute_minutes))
    await session.commit()
    return {"code": 0, "data": {
        "wake_hour": user.wake_hour, "sleep_hour": user.sleep_hour, "commute_minutes": user.commute_minutes,
    }}


@router.get("/debug")
async def debug(session: AsyncSession = Depends(get_db)):
    """调试：查看数据库状态"""
    from sqlalchemy import select, text
    result = await session.execute(select(User))
    users = [{"id": u.id, "username": u.username} for u in result.scalars().all()]
    return {"code": 0, "data": {"users": users, "count": len(users)}}
