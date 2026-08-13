"""跨模块预测性智能：预判用户需求"""
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, and_, func, Integer
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fsm import PredictionRecord


class Predictor:
    """跨模块预测引擎

    预测类型：
    - overspend: 超支预测
    - burnout: 倦怠预测
    - hoarding: 囤货预测
    - conflict: 日程冲突预测
    - energy_crash: 精力崩溃预测
    """

    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id

    async def generate_predictions(self) -> list[dict[str, Any]]:
        """生成预测"""
        predictions = []

        # 1. 超支预测
        overspend = await self._predict_overspend()
        if overspend:
            predictions.append(overspend)

        # 2. 倦怠预测
        burnout = await self._predict_burnout()
        if burnout:
            predictions.append(burnout)

        # 3. 囤货预测
        hoarding = await self._predict_hoarding()
        if hoarding:
            predictions.append(hoarding)

        # 4. 精力崩溃预测
        energy = await self._predict_energy_crash()
        if energy:
            predictions.append(energy)

        # 持久化
        saved = []
        for pred in predictions:
            record = PredictionRecord(
                user_id=self.user_id,
                prediction_type=pred["type"],
                description=pred["description"],
                probability=pred["probability"],
                severity=pred["severity"],
                evidence=pred.get("evidence", {}),
                suggestion=pred.get("suggestion", ""),
            )
            self.session.add(record)
            saved.append(pred)

        await self.session.flush()
        return saved

    async def _predict_overspend(self) -> dict | None:
        """超支预测"""
        from app.models.consume import ConsumeRecord, Budget

        month = datetime.utcnow().strftime('%Y-%m-%d')[:7]
        day = datetime.utcnow().day

        # 计算本月已用
        result = await self.session.execute(
            select(ConsumeRecord.category, func.sum(ConsumeRecord.amount)).where(and_(
                ConsumeRecord.user_id == self.user_id,
                func.strftime('%Y-%m-%m', ConsumeRecord.occurred_at) == month,
            )).group_by(ConsumeRecord.category)
        )
        spending = {row[0]: float(row[1]) for row in result.all()}

        # 获取预算
        budget_result = await self.session.execute(
            select(Budget.category, Budget.monthly_limit).where(and_(
                Budget.user_id == self.user_id,
                Budget.effective_month == month,
            ))
        )
        budgets = {row[0]: float(row[1]) for row in budget_result.all()}

        # 预测超支品类
        overspend_cats = []
        for cat, spent in spending.items():
            budget = budgets.get(cat, 0)
            if budget > 0:
                pace = spent / budget
                projected = spent / max(day, 1) * 30  # 月末预计
                if projected > budget * 1.2:
                    overspend_cats.append({
                        "category": cat,
                        "spent": spent,
                        "budget": budget,
                        "projected": round(projected, 0),
                    })

        if overspend_cats:
            worst = max(overspend_cats, key=lambda x: x["projected"] / max(x["budget"], 1))
            return {
                "type": "overspend",
                "description": f"品类{worst['category']}预计超支¥{worst['projected'] - worst['budget']:.0f}",
                "probability": min(0.9, worst["projected"] / max(worst["budget"], 1) - 0.5),
                "severity": "high" if worst["projected"] > worst["budget"] * 1.5 else "medium",
                "evidence": {"overspend_categories": overspend_cats},
                "suggestion": f"建议削减{worst['category']}支出，或从其他品类调配预算",
            }
        return None

    async def _predict_burnout(self) -> dict | None:
        """倦怠预测"""
        from app.models.innovation import EnergyRecord

        # 获取近7天精力趋势
        cutoff = (datetime.utcnow() - timedelta(days=7)).strftime('%Y-%m-%d')
        result = await self.session.execute(
            select(EnergyRecord.total_energy, EnergyRecord.record_date).where(and_(
                EnergyRecord.user_id == self.user_id,
                EnergyRecord.record_date >= cutoff,
            )).order_by(EnergyRecord.record_date)
        )
        energies = result.all()

        if len(energies) < 3:
            return None

        # 检测持续下降趋势
        values = [e[0] for e in energies]
        declining_count = sum(1 for i in range(1, len(values)) if values[i] < values[i - 1])

        if declining_count >= len(values) * 0.6:
            return {
                "type": "burnout",
                "description": f"近{len(values)}天精力持续下降，存在倦怠风险",
                "probability": declining_count / len(values),
                "severity": "high" if values[-1] < 40 else "medium",
                "evidence": {"energy_trend": values},
                "suggestion": "建议减少高难度任务，增加休息和娱乐活动",
            }
        return None

    async def _predict_hoarding(self) -> dict | None:
        """囤货预测"""
        from app.models.item import Item

        result = await self.session.execute(
            select(Item.name, func.count(Item.id)).where(
                Item.user_id == self.user_id
            ).group_by(Item.name).having(func.count(Item.id) > 2)
        )
        duplicates = result.all()

        if duplicates:
            worst = max(duplicates, key=lambda x: x[1])
            return {
                "type": "hoarding",
                "description": f"「{worst[0]}」囤积{worst[1]}件，存在浪费风险",
                "probability": min(0.9, worst[1] / 10),
                "severity": "high" if worst[1] > 5 else "medium",
                "evidence": {"duplicates": [{"name": d[0], "count": d[1]} for d in duplicates]},
                "suggestion": f"建议清理多余{worst[0]}，转手或捐赠",
            }
        return None

    async def _predict_energy_crash(self) -> dict | None:
        """精力崩溃预测"""
        from app.models.advanced import LifeStabilityState

        result = await self.session.execute(
            select(LifeStabilityState).where(and_(
                LifeStabilityState.user_id == self.user_id,
            )).order_by(LifeStabilityState.state_date.desc()).limit(1)
        )
        state = result.scalar_one_or_none()

        if state and state.consecutive_high_days >= 3:
            return {
                "type": "energy_crash",
                "description": f"连续{state.consecutive_high_days}天高压，精力崩溃风险",
                "probability": min(0.9, state.consecutive_high_days / 7),
                "severity": "high" if state.consecutive_high_days >= 5 else "medium",
                "evidence": {"consecutive_high": state.consecutive_high_days},
                "suggestion": "建议立即安排休息缓冲，暂停非紧急任务",
            }
        return None
