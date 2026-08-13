"""演化风险自检机制：任务过载/预算崩盘/作息紊乱拦截"""
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, and_, func, Integer
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evolution import RiskCheckResult
from app.models.rule import UserRule
from app.models.behavior import BehaviorLog


class RiskGuard:
    """演化风险自检守卫

    在规则生效前，模拟应用该规则可能产生的后果：
    1. 任务过载检测 - 规则是否导致日程密度超标
    2. 预算崩盘检测 - 规则是否导致消费超支
    3. 作息紊乱检测 - 规则是否导致睡眠不足
    """

    # 风险阈值
    MAX_DAILY_TASKS = 10
    MAX_DAILY_STUDY_HOURS = 10
    MIN_SLEEP_HOURS = 6
    BUDGET_OVERRUN_RATIO = 1.2

    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id

    async def check_rule_safety(self, rule_name: str, rule_expr: dict) -> dict[str, Any]:
        """检测规则安全性"""
        risks = []

        # 1. 任务过载检测
        overload = await self._check_task_overload(rule_expr)
        if overload["risky"]:
            risks.append(overload)

        # 2. 预算崩盘检测
        budget = await self._check_budget_collapse(rule_expr)
        if budget["risky"]:
            risks.append(budget)

        # 3. 作息紊乱检测
        schedule = await self._check_schedule_disruption(rule_expr)
        if schedule["risky"]:
            risks.append(schedule)

        # 综合评估
        is_safe = len(risks) == 0
        max_risk = max((r["score"] for r in risks), default=0)
        risk_level = self._classify_risk_level(max_risk)

        # 处置决策
        if risk_level == "critical":
            action = "blocked"
        elif risk_level == "high":
            action = "modified"
        else:
            action = "approved"

        # 记录
        check = RiskCheckResult(
            user_id=self.user_id,
            rule_name=rule_name,
            rule_expr=rule_expr,
            risk_type=risks[0]["type"] if risks else "none",
            risk_level=risk_level,
            is_safe=is_safe,
            risk_score=max_risk,
            details=str(risks) if risks else "安全",
            action_taken=action,
        )
        self.session.add(check)
        await self.session.flush()

        return {
            "is_safe": is_safe,
            "risk_level": risk_level,
            "risks": risks,
            "action": action,
            "message": f"规则「{rule_name}」{ '通过检测' if is_safe else '被' + action }",
        }

    async def _check_task_overload(self, rule_expr: dict) -> dict:
        """任务过载检测"""
        # 获取当前日程密度
        today = datetime.utcnow().strftime('%Y-%m-%d')
        result = await self.session.execute(
            select(func.count(BehaviorLog.id)).where(and_(
                BehaviorLog.user_id == self.user_id,
                BehaviorLog.dimension == "time",
                func.strftime('%Y-%m-%d', BehaviorLog.created_at) == today,
            ))
        )
        current_tasks = result.scalar() or 0

        # 规则可能增加的任务数
        rule_task_boost = rule_expr.get("task_count_boost", 0)
        projected = current_tasks + rule_task_boost

        risky = projected > self.MAX_DAILY_TASKS
        score = projected / self.MAX_DAILY_TASKS if self.MAX_DAILY_TASKS > 0 else 0

        return {
            "type": "task_overload",
            "risky": risky,
            "score": min(1.0, score),
            "detail": f"预计任务数{projected}，阈值{self.MAX_DAILY_TASKS}",
        }

    async def _check_budget_collapse(self, rule_expr: dict) -> dict:
        """预算崩盘检测"""
        if "budget_factor" not in rule_expr:
            return {"type": "budget_collapse", "risky": False, "score": 0, "detail": "无预算影响"}

        factor = rule_expr.get("budget_factor", 1.0)

        # 获取本月消费
        month = datetime.utcnow().strftime('%Y-%m')
        result = await self.session.execute(
            select(func.coalesce(func.sum(BehaviorLog.value), 0)).where(and_(
                BehaviorLog.user_id == self.user_id,
                BehaviorLog.dimension == "consume",
                func.strftime('%Y-%m', BehaviorLog.created_at) == month,
            ))
        )
        current_spend = float(result.scalar() or 0)

        # 规则影响后的预计消费
        projected = current_spend * factor
        monthly_income = await self._get_monthly_income()

        risky = monthly_income > 0 and projected > monthly_income * self.BUDGET_OVERRUN_RATIO
        score = projected / max(monthly_income, 1)

        return {
            "type": "budget_collapse",
            "risky": risky,
            "score": min(1.0, score),
            "detail": f"预计月消费¥{projected:.0f}，收入¥{monthly_income:.0f}",
        }

    async def _check_schedule_disruption(self, rule_expr: dict) -> dict:
        """作息紊乱检测"""
        from app.models.user import User
        user = await self.session.get(User, self.user_id)
        if not user:
            return {"type": "schedule_disruption", "risky": False, "score": 0, "detail": "无用户数据"}

        sleep_hour = user.sleep_hour
        wake_hour = user.wake_hour

        # 计算睡眠时长
        if sleep_hour > wake_hour:
            sleep_duration = sleep_hour - wake_hour
        else:
            sleep_duration = (24 - wake_hour) + sleep_hour

        # 规则是否进一步压缩睡眠
        sleep_reduction = rule_expr.get("sleep_reduction", 0)
        projected_sleep = sleep_duration - sleep_reduction

        risky = projected_sleep < self.MIN_SLEEP_HOURS
        score = 1.0 - (projected_sleep / self.MIN_SLEEP_HOURS) if projected_sleep < self.MIN_SLEEP_HOURS else 0

        return {
            "type": "schedule_disruption",
            "risky": risky,
            "score": max(0, min(1.0, score)),
            "detail": f"预计睡眠{projected_sleep:.1f}小时，最低{self.MIN_SLEEP_HOURS}小时",
        }

    async def _get_monthly_income(self) -> float:
        """获取月收入"""
        from app.models.user import User
        user = await self.session.get(User, self.user_id)
        return user.monthly_income if user else 5000.0

    @staticmethod
    def _classify_risk_level(score: float) -> str:
        """分类风险等级"""
        if score >= 0.9:
            return "critical"
        elif score >= 0.7:
            return "high"
        elif score >= 0.4:
            return "medium"
        return "low"
