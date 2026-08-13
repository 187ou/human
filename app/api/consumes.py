"""消费记账API（含账单导入、AI打标、弹性预算、复盘报告、预算提醒）"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, get_current_user
from app.models.user import User
from app.models.consume import ConsumeRecord, Budget, BudgetTransfer, MonthlyReview, BudgetAlert
from app.services.behavior_collector import BehaviorCollector
from app.services.consume_analyzer import ConsumeAnalyzer

router = APIRouter()


class ConsumeCreate(BaseModel):
    amount: float
    category: str
    merchant: str | None = None
    description: str | None = None
    source: str = "manual"


class BillImport(BaseModel):
    content: str  # CSV文件内容
    source: str  # wechat / alipay


class BudgetSet(BaseModel):
    category: str
    monthly_limit: float
    is_flexible: bool = False
    flex_source_categories: list[str] | None = None


# ==================== CRUD ====================

@router.post("")
async def create_consume(
    data: ConsumeCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    record = ConsumeRecord(
        user_id=user.id, amount=data.amount, category=data.category,
        merchant=data.merchant, description=data.description, source=data.source,
    )
    session.add(record)
    await session.flush()

    # AI自动打标
    analyzer = ConsumeAnalyzer(session, user.id)
    tag = await analyzer.auto_tag_record(record)
    record.tag = tag
    record.is_impulse = (tag == 'impulse')
    record.is_waste = (tag in ('impulse', 'hoarding'))

    # 弹性预算处理
    flex_result = await analyzer.handle_flexible_budget(record)

    # 行为采集
    collector = BehaviorCollector(session)
    await collector.log_consume(user_id=user.id, amount=data.amount, category=data.category,
                                is_necessity=(tag == 'necessity'), is_impulse=(tag == 'impulse'))

    # 检查预算提醒
    alerts = await analyzer.check_budget_alerts()

    await session.commit()
    return {"code": 0, "data": {"id": record.id, "tag": tag, "flex_result": flex_result, "alerts": len(alerts)}}


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
        stmt = stmt.where(func.strftime('%Y-%m', ConsumeRecord.occurred_at) == month)
    result = await session.execute(stmt.order_by(ConsumeRecord.occurred_at.desc()))
    items = result.scalars().all()
    return {"code": 0, "data": [
        {"id": r.id, "amount": r.amount, "category": r.category, "merchant": r.merchant,
         "tag": r.tag, "is_impulse": r.is_impulse, "is_waste": r.is_waste,
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
            func.strftime('%Y-%m', ConsumeRecord.occurred_at) == month,
        )
    ).group_by(ConsumeRecord.category)
    result = await session.execute(stmt)
    rows = result.all()
    return {"code": 0, "data": [
        {"category": r.category, "total": float(r.total), "count": r.count}
        for r in rows
    ]}


# ==================== 账单导入 ====================

@router.post("/import")
async def import_bill(
    data: BillImport,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """导入微信/支付宝账单"""
    analyzer = ConsumeAnalyzer(session, user.id)

    if data.source == 'wechat':
        records = await analyzer.parse_wechat_bill(data.content)
    elif data.source == 'alipay':
        records = await analyzer.parse_alipay_bill(data.content)
    else:
        raise HTTPException(status_code=400, detail="不支持的账单来源")

    if not records:
        raise HTTPException(status_code=400, detail="未解析到有效记录")

    # 导入并打标
    count = await analyzer.import_records(records)
    await analyzer.batch_tag_records()

    # 弹性预算处理
    for record_data in records:
        rec = ConsumeRecord(
            user_id=user.id, amount=record_data['amount'],
            category=record_data.get('category', 'other'),
            merchant=record_data.get('merchant'),
            source=data.source,
        )
        await analyzer.handle_flexible_budget(rec)

    await session.commit()
    return {"code": 0, "data": {"imported": count, "source": data.source}}


# ==================== AI打标 ====================

@router.post("/auto-tag")
async def auto_tag(
    month: str | None = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """批量AI打标"""
    analyzer = ConsumeAnalyzer(session, user.id)
    count = await analyzer.batch_tag_records(month)
    await session.commit()
    return {"code": 0, "data": {"tagged": count}}


# ==================== 预算管理 ====================

@router.post("/budget")
async def set_budget(
    data: BudgetSet,
    month: str | None = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """设置品类预算"""
    if not month:
        month = datetime.utcnow().strftime('%Y-%m')

    result = await session.execute(
        select(Budget).where(
            and_(
                Budget.user_id == user.id,
                Budget.category == data.category,
                Budget.effective_month == month,
            )
        )
    )
    budget = result.scalar_one_or_none()
    if budget:
        budget.monthly_limit = data.monthly_limit
        budget.is_flexible = data.is_flexible
        budget.flex_source_categories = data.flex_source_categories
    else:
        budget = Budget(
            user_id=user.id, category=data.category, monthly_limit=data.monthly_limit,
            is_flexible=data.is_flexible, flex_source_categories=data.flex_source_categories,
            effective_month=month,
        )
        session.add(budget)
    await session.commit()
    return {"code": 0, "data": {"id": budget.id}}


@router.get("/budget/status")
async def budget_status(
    month: str | None = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """获取预算使用情况"""
    if not month:
        month = datetime.utcnow().strftime('%Y-%m')

    budgets = await session.execute(
        select(Budget).where(
            and_(Budget.user_id == user.id, Budget.effective_month == month)
        )
    )

    result = []
    for b in budgets.scalars().all():
        spent_result = await session.execute(
            select(func.coalesce(func.sum(ConsumeRecord.amount), 0)).where(
                and_(
                    ConsumeRecord.user_id == user.id,
                    ConsumeRecord.category == b.category,
                    func.strftime('%Y-%m', ConsumeRecord.occurred_at) == month,
                )
            )
        )
        spent = spent_result.scalar() or 0
        result.append({
            "category": b.category,
            "limit": b.monthly_limit,
            "spent": float(spent),
            "remaining": b.monthly_limit - float(spent),
            "percentage": round(spent / b.monthly_limit * 100, 1) if b.monthly_limit > 0 else 0,
            "is_flexible": b.is_flexible,
        })

    return {"code": 0, "data": result}


# ==================== 月度复盘 ====================

@router.get("/review")
async def monthly_review(
    month: str | None = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """生成/获取月度复盘报告"""
    analyzer = ConsumeAnalyzer(session, user.id)
    review = await analyzer.generate_monthly_review(month)
    await session.commit()
    return {"code": 0, "data": {
        "month": review.month,
        "total_spent": review.total_spent,
        "total_budget": review.total_budget,
        "surplus": review.surplus,
        "category_breakdown": review.category_breakdown,
        "tag_breakdown": review.tag_breakdown,
        "waste_items": review.waste_items,
        "suggestions": review.suggestions,
        "summary": review.summary,
    }}


# ==================== 预算提醒 ====================

@router.get("/alerts")
async def budget_alerts(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """获取预算提醒"""
    analyzer = ConsumeAnalyzer(session, user.id)
    alerts = await analyzer.get_active_alerts()
    return {"code": 0, "data": [
        {"id": a.id, "category": a.category, "alert_type": a.alert_type,
         "current_amount": a.current_amount, "budget_limit": a.budget_limit,
         "percentage": a.percentage}
        for a in alerts
    ]}


@router.post("/alerts/{alert_id}/read")
async def mark_alert_read(
    alert_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """标记提醒已读"""
    alert = await session.get(BudgetAlert, alert_id)
    if alert and alert.user_id == user.id:
        alert.is_read = True
        await session.commit()
    return {"code": 0}
