"""API依赖"""
from fastapi import Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db as _get_db
from app.models.user import User


async def get_session(db: AsyncSession = Depends(_get_db)) -> AsyncSession:
    return db


async def get_current_user(
    authorization: str | None = Header(None, description="JWT Token: Bearer <token>"),
    session: AsyncSession = Depends(get_session),
) -> User:
    """获取当前用户（从JWT Token解析）"""
    from app.utils.auth import decode_access_token

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    token = authorization.replace("Bearer ", "")
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token已过期或无效")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token无效")

    from sqlalchemy import select
    result = await session.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user
