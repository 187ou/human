"""自然语言解析API"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, get_current_user
from app.models.user import User
from app.services.nlp_parser import NLPParser, QUICK_COMMANDS

router = APIRouter()


class NLParseRequest(BaseModel):
    text: str


@router.post("/parse")
async def parse_text(
    data: NLParseRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """解析自然语言为结构化指令"""
    parser = NLPParser()
    try:
        result = await parser.parse(data.text)
    except Exception:
        # 降级到规则解析
        result = parser._rule_based_parse(data.text)
    return {"code": 0, "data": result}


@router.get("/quick-commands")
async def quick_commands():
    """获取快捷指令模板"""
    return {"code": 0, "data": QUICK_COMMANDS}
