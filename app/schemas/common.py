"""通用请求/响应Schema"""
from pydantic import BaseModel


class Response(BaseModel):
    code: int = 0
    message: str = "ok"
    data: dict | list | None = None
