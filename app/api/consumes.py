"""消费记账API"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, get_current_user
from app.models.consume import ConsumeRecord, Budget
from app.models.user import User
from app.services.behavior_collector import BehaviorCollector

router = APIRouter()


class ConsumeCreate(BaseModel):
    amount: float
    category: str
    merchant: str | None = None
    description: str | None = None
    source: str = "manual"


@router.post("")
async def create_consume(
    data: ConsumeCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    record = ConsumeRecord(
        user_id=user.id,
        amount=data.amount,
        category=data.category,
        merchant=data.merchant,
        description=data.description,
        source=data.source,
    )
    session.add(record)

    # 行为采集
    collector = BehaviorCollector(session)
    await collector.log_consume(user_id=user.id, amount=data.amount, category=data.category, is_necessity=True, is_impulse=False)

    await session.commit()
    return {"code": 0, "data": {"id": record.id}}


@router.get("")
async def list_consumes(
    month: str | None = None,
    category: str | None = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    stmt = select(ConsumeRecord).where(ConsumeRecord.user_id == user.id)
    if category:
        stmt = stmt.where(ConsumeRecord.category == category)
    if month:
        stmt = stmt.where(ConsumeRecord.occurred_at.like(f"{month}%"))
    result = await session.execute(stmt.order_by(ConsumeRecord.occurred_at.desc()))
    items = result.scalars().all()
    return {"code": 0, "data": [
        {"id": r.id, "amount": r.amount, "category": r.category, "merchant": r.merchant,
         "occurred_at": r.occurred_at.isoformat()}
        for r in items
    ]}


@router.get("/stats")
async def consume_stats(
    month: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """月度统计"""
    stmt = select(
        ConsumeRecord.category,
        func.sum(ConsumeRecord.amount).label("total"),
        func.count().label("count"),
    ).where(
        and_(
            ConsumeRecord.user_id == user.id,
            ConsumeRecord.occurred_at.like(f"{month}%"),
        )
    ).group_by(ConsumeRecord.category)
    result = await session.execute(stmt)
    rows = result.all()
    return {"code": 0, "data": [
        {"category": r.category, "total": float(r.total), "count": r.count}
        for r in rows
    ]}


# ---- 预算 ----

class BudgetSet(BaseModel):
    category: str
    monthly_limit: float


@router.post("/budget")
async def set_budget(
    data: BudgetSet,
    month: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    # 查找已有预算
    stmt = select(Budget).where(
        and_(
            Budget.user_id == user.id,
            Budget.category == data.category,
            Budget.effective_month == month,
        )
    )
    result = await session.execute(stmt)
    budget = result.scalar_one_or_none()
    if budget:
        budget.monthly_limit = data.monthly_limit
    else:
        budget = Budget(
            user_id=user.id,
            category=data.category,
            monthly_limit=data.monthly_limit,
            effective_month=month,
        )
        session.add(budget)
    await session.commit()
    return {"code": 0, "data": {"id": budget.id}}
