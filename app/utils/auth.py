"""JWT认证工具（纯bcrypt实现，避免passlib兼容性问题）"""
from datetime import datetime, timedelta
from typing import Any

import bcrypt
from jose import JWTError, jwt

SECRET_KEY = "human-agent-secret-key-change-in-production-2026"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode(), salt).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


def create_access_token(data: dict[str, Any]) -> str:
    to_encode = {"sub": str(data.get("sub", ""))}
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
