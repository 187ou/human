"""大额支出守护服务：自动重核算+调整方案"""
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.snapshot import LargeExpenseRecord, LLMRejectLog
from app.models.consume import ConsumeRecord, Budget


class ExpenseGuard:
    """大额支出守护"""

    # 大额支出阈值（占月收入比例）
    LARGE_EXPENSE_RATIO = 0.1  # 单笔超过月收入10%视为大额
    ABSOLUTE_THRESHOLD = 500  # 或绝对值超过500元

    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id

    async def check_large_expense(self, amount: float, category: str,
                                   merchant: str | None = None) -> dict[str, Any]:
        """检查是否为大额支出并自动重核算"""
        # 获取用户月收入
        from app.models.user import User
        user = await self.session.get(User, self.user_id)
        monthly_income = user.monthly_income if user else 5000

        # 判定阈值
        threshold = max(monthly_income * self.LARGE_EXPENSE_RATIO, self.ABSOLUTE_THRESHOLD)
        is_large = amount >= threshold

        if not is_large:
            return {"is_large": False}

        month = datetime.utcnow().strftime('%Y-%m')

        # 获取当前预算
        budget_result = await self.session.execute(
            select(Budget).where(and_(
                Budget.user_id == self.user_id,
                Budget.category == category,
                Budget.effective_month == month,
            ))
        )
        budget = budget_result.scalar_one_or_none()
        original_budget = budget.monthly_limit if budget else 0

        # 计算已用
        spent_result = await self.session.execute(
            select(func.coalesce(func.sum(ConsumeRecord.amount), 0)).where(and_(
                ConsumeRecord.user_id == self.user_id,
                ConsumeRecord.category == category,
                func.strftime('%Y-%m', ConsumeRecord.occurred_at) == month,
            ))
        )
        spent = spent_result.scalar() or 0

        # 重核算
        remaining_budget = original_budget - spent
        days_in_month = 30
        day_of_month = datetime.utcnow().day
        remaining_days = days_in_month - day_of_month

        adjustment_plan = {}
        if remaining_budget < 0:
            # 已超支
            daily_limit = 0
            adjustment_plan = {
                "status": "overspent",
                "message": f"品类{category}已超支¥{abs(remaining_budget):.0f}",
                "suggestions": [
                    f"暂停{category}非必要支出",
                    f"从娱乐/购物预算划拨¥{abs(remaining_budget) * 0.5:.00:.0f}",
                    f"下月预算建议上调¥{abs(remaining_budget) * 0.3:.0f}",
                ],
            }
        elif remaining_days > 0:
            daily_limit = remaining_budget / remaining_days
            adjustment_plan = {
                "status": "warning",
                "message": f"大额支出¥{amount:.0f}，剩余预算¥{remaining_budget:.0f}",
                "daily_limit": round(daily_limit, 2),
                "remaining_days": remaining_days,
                "suggestions": [
                    f"剩余{remaining_days}天日均控制在¥{daily_limit:.0f}以内",
                    f"建议减少非必要{category}支出",
                ],
            }

        # 记录大额支出
        record = LargeExpenseRecord(
            user_id=self.user_id,
            amount=amount,
            category=category,
            merchant=merchant,
            threshold_amount=threshold,
            is_large=True,
            original_budget=original_budget,
            adjusted_budget=remaining_budget,
            adjustment_plan=adjustment_plan,
        )
        self.session.add(record)
        await self.session.flush()

        return {
            "is_large": True,
            "amount": amount,
            "threshold": threshold,
            "original_budget": original_budget,
            "remaining_budget": remaining_budget,
            "adjustment_plan": adjustment_plan,
            "record_id": record.id,
        }


class LLMGuard:
    """LLM生成内容守护"""

    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id

    async def reject_content(self, content_type: str, original_content: dict,
                              reason: str | None = None) -> LLMRejectLog:
        """驳回LLM生成内容"""
        log = LLMRejectLog(
            user_id=self.user_id,
            content_type=content_type,
            original_content=original_content,
            reject_reason=reason,
        )
        self.session.add(log)
        await self.session.flush()
        return log

    async def correct_content(self, log_id: int, corrected_content: dict) -> bool:
        """提交修正后内容"""
        log = await self.session.get(LLMRejectLog, log_id)
        if log and log.user_id == self.user_id:
            log.corrected_content = corrected_content
            log.is_corrected = True
            await self.session.flush()
            return True
        return False

    async def get_reject_history(self, limit: int = 10) -> list[LLMRejectLog]:
        """获取驳回历史"""
        result = await self.session.execute(
            select(LLMRejectLog)
            .where(LLMRejectLog.user_id == self.user_id)
            .order_by(LLMRejectLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
