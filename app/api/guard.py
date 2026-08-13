"""守护机制API：LLM驳回+大额支出"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, get_current_user
from app.models.user import User
from app.services.expense_guard import ExpenseGuard, LLMGuard

router = APIRouter()


# === 大额支出守护 ===

class ExpenseCheck(BaseModel):
    amount: float
    category: str
    merchant: str | None = None


@router.post("/check-expense")
async def check_large_expense(
    data: ExpenseCheck,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """检查大额支出并重核算"""
    guard = ExpenseGuard(session, user.id)
    result = await guard.check_large_expense(data.amount, data.category, data.merchant)
    await session.commit()
    return {"code": 0, "data": result}


# === LLM驳回 ===

class RejectRequest(BaseModel):
    content_type: str
    original_content: dict
    reason: str | None = None


class CorrectRequest(BaseModel):
    log_id: int
    corrected_content: dict


@router.post("/reject-llm")
async def reject_llm_content(
    data: RejectRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """驳回LLM生成内容"""
    guard = LLMGuard(session, user.id)
    log = await guard.reject_content(data.content_type, data.original_content, data.reason)
    await session.commit()
    return {"code": 0, "data": {"id": log.id}}


@router.post("/correct-llm")
async def correct_llm_content(
    data: CorrectRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """提交修正后内容"""
    guard = LLMGuard(session, user.id)
    ok = await guard.correct_content(data.log_id, data.corrected_content)
    await session.commit()
    return {"code": 0 if ok else 1}


@router.get("/reject-history")
async def reject_history(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """获取驳回历史"""
    guard = LLMGuard(session, user.id)
    history = await guard.get_reject_history()
    return {"code": 0, "data": [
        {"id": h.id, "content_type": h.content_type, "original": h.original_content,
         "reason": h.reject_reason, "is_corrected": h.is_corrected,
         "created_at": h.created_at.isoformat()}
        for h in history
    ]}
