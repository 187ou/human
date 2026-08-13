"""生活稳态维持演化目标函数

核心思想：演化不止追求效率最高，同时维持用户身心稳态。

目标函数 = 效率 × 0.3 + 幸福感 × 0.3 + 可持续性 × 0.25 + 成长性 × 0.15

干预策略：
- 连续高压 → 插入休息日、下调任务负荷
- 长期摆烂 → 缓慢小幅提升任务量
- 收支失衡 → 逐步优化消费结构
"""
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, and_, func, Integer
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stability import StabilityObjective, StabilityIntervention


class StabilityObjectiveFunction:
    """生活稳态维持目标函数"""

    # 干预阈值
    HIGH_PRESSURE_THRESHOLD = 3  # 连续3天高压
    SLUMP_THRESHOLD = 5  # 连续5天摆烂
    BUDGET_IMBALANCE = 1.2  # 超支20%

    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id

    async def evaluate_and_intervene(self) -> dict[str, Any]:
        """评估稳态并执行干预"""
        # 获取或创建目标函数配置
        config = await self._get_or_create_config()

        # 检测当前状态
        pressure_days = await self._count_consecutive_high_pressure()
        slump_days = await self._count_consecutive_slump()
        budget_status = await self._check_budget_balance()

        interventions = []

        # 1. 连续高压检测
        if pressure_days >= config.max_consecutive_high_days:
            intervention = await self._intervene_rest_insert(pressure_days)
            interventions.append(intervention)

        # 2. 长期摆烂检测
        if slump_days >= config.max_consecutive_slump_days:
            intervention = await self._intervene_task_ramp_up(slump_days)
            interventions.append(intervention)

        # 3. 收支失衡检测
        if budget_status.get("imbalanced"):
            intervention = await self._intervene_budget_smooth(budget_status)
            interventions.append(intervention)

        # 4. 动态调整目标权重
        weights = self._adjust_objective_weights(pressure_days, slump_days, budget_status)
        config.efficiency_weight = weights["efficiency"]
        config.well_being_weight = weights["well_being"]
        config.sustainability_weight = weights["sustainability"]
        config.growth_weight = weights["growth"]

        await self.session.flush()

        return {
            "pressure_days": pressure_days,
            "slump_days": slump_days,
            "budget_status": budget_status,
            "interventions": interventions,
            "objective_weights": weights,
        }

    async def _get_or_create_config(self) -> StabilityObjective:
        """获取或创建配置"""
        result = await self.session.execute(
            select(StabilityObjective).where(StabilityObjective.user_id == self.user_id)
        )
        config = result.scalar_one_or_none()

        if not config:
            config = StabilityObjective(user_id=self.user_id)
            self.session.add(config)
            await self.session.flush()

        return config

    async def _count_consecutive_high_pressure(self) -> int:
        """计算连续高压天数"""
        from app.models.innovation import EnergyRecord

        cutoff = (datetime.utcnow() - timedelta(days=14)).strftime('%Y-%m-%d')
        result = await self.session.execute(
            select(EnergyRecord).where(and_(
                EnergyRecord.user_id == self.user_id,
                EnergyRecord.record_date >= cutoff,
            )).order_by(EnergyRecord.record_date.desc())
        )
        records = result.scalars().all()

        consecutive = 0
        for record in records:
            if record.total_energy > 75:  # 高精力=高压
                consecutive += 1
            else:
                break

        return consecutive

    async def _count_consecutive_slump(self) -> int:
        """计算连续摆烂天数"""
        from app.models.innovation import EnergyRecord

        cutoff = (datetime.utcnow() - timedelta(days=14)).strftime('%Y-%m-%d')
        result = await self.session.execute(
            select(EnergyRecord).where(and_(
                EnergyRecord.user_id == self.user_id,
                EnergyRecord.record_date >= cutoff,
            )).order_by(EnergyRecord.record_date.desc())
        )
        records = result.scalars().all()

        consecutive = 0
        for record in records:
            if record.total_energy < 30:  # 低精力=摆烂
                consecutive += 1
            else:
                break

        return consecutive

    async def _check_budget_balance(self) -> dict[str, Any]:
        """检查收支平衡"""
        from app.models.consume import ConsumeRecord, Budget

        month = datetime.utcnow().strftime('%Y-%m')

        # 总消费
        result = await self.session.execute(
            select(func.coalesce(func.sum(ConsumeRecord.amount), 0)).where(and_(
                ConsumeRecord.user_id == self.user_id,
                func.strftime('%Y-%m', ConsumeRecord.occurred_at) == month,
            ))
        )
        total_spend = float(result.scalar() or 0)

        # 总收入（预算总和）
        result = await self.session.execute(
            select(func.coalesce(func.sum(Budget.monthly_limit), 0)).where(and_(
                Budget.user_id == self.user_id,
                Budget.effective_month == month,
            ))
        )
        total_budget = float(result.scalar() or 0)

        if total_budget == 0:
            return {"imbalanced": False, "ratio": 0}

        ratio = total_spend / total_budget
        return {
            "imbalanced": ratio > self.BUDGET_IMBALANCE,
            "ratio": round(ratio, 2),
            "total_spend": total_spend,
            "total_budget": total_budget,
        }

    async def _intervene_rest_insert(self, pressure_days: int) -> dict[str, Any]:
        """插入休息日干预"""
        intervention = StabilityIntervention(
            user_id=self.user_id,
            intervention_type="rest_insert",
            trigger=f"连续{pressure_days}天高压",
            severity="high" if pressure_days >= 5 else "medium",
            action_taken="插入休息日，下调任务负荷30%",
            parameters={"rest_days": 1, "task_reduction": 0.3},
        )
        self.session.add(intervention)
        return {"type": "rest_insert", "action": "插入休息日，下调任务负荷30%"}

    async def _intervene_task_ramp_up(self, slump_days: int) -> dict[str, Any]:
        """缓慢提升任务量干预"""
        intervention = StabilityIntervention(
            user_id=self.user_id,
            intervention_type="task_ramp_up",
            trigger=f"连续{slump_days}天摆烂",
            severity="medium",
            action_taken="缓慢小幅提升任务量10%",
            parameters={"ramp_rate": 0.1, "max_increase": 0.3},
        )
        self.session.add(intervention)
        return {"type": "task_ramp_up", "action": "缓慢小幅提升任务量10%"}

    async def _intervene_budget_smooth(self, budget_status: dict) -> dict[str, Any]:
        """消费结构平滑优化干预"""
        intervention = StabilityIntervention(
            user_id=self.user_id,
            intervention_type="budget_smooth",
            trigger=f"收支比{budget_status['ratio']}",
            severity="high" if budget_status["ratio"] > 1.5 else "medium",
            action_taken="逐步优化消费结构，削减非必要支出15%",
            parameters={"adjust_rate": 0.15, "priority": "non_essential"},
        )
        self.session.add(intervention)
        return {"type": "budget_smooth", "action": "逐步优化消费结构15%"}

    def _adjust_objective_weights(self, pressure_days: int, slump_days: int,
                                   budget_status: dict) -> dict[str, float]:
        """动态调整目标权重"""
        # 基础权重
        efficiency = 0.3
        well_being = 0.3
        sustainability = 0.25
        growth = 0.15

        # 根据状态调整
        if pressure_days >= self.HIGH_PRESSURE_THRESHOLD:
            # 高压状态：提升幸福感权重，降低效率权重
            well_being += 0.15
            efficiency -= 0.1
            sustainability += 0.05

        if slump_days >= self.SLUMP_THRESHOLD:
            # 摆烂状态：提升成长性权重，缓慢激励
            growth += 0.1
            well_being += 0.05
            efficiency -= 0.05

        if budget_status.get("imbalanced"):
            # 收支失衡：提升可持续性权重
            sustainability += 0.1
            efficiency -= 0.05

        # 归一化
        total = efficiency + well_being + sustainability + growth
        return {
            "efficiency": round(efficiency / total, 3),
            "well_being": round(well_being / total, 3),
            "sustainability": round(sustainability / total, 3),
            "growth": round(growth / total, 3),
        }
