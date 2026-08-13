"""生活稳态维持机制：防止用户生活崩盘"""
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, and_, func, Integer
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.advanced import LifeStabilityState, TaskDifficultyLog, NegativeFeedback
from app.models.behavior import BehaviorLog


class StabilityKeeper:
    """生活稳态维持引擎

    核心逻辑：
    - 连续摆烂(3天+)→降低压力、增加轻松任务
    - 连续高压(5天+)→主动安排休息缓冲
    - 任务难度动态缩放→根据完成率实时调整
    """

    SLUMP_THRESHOLD = 3  # 连续3天低完成率=摆烂
    HIGH_PRESSURE_THRESHOLD = 5  # 连续5天高负荷=高压

    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id

    async def check_and_intervene(self) -> dict[str, Any]:
        """检查稳态并干预"""
        # 计算近7天状态
        states = await self._calc_recent_states()

        # 检测连续状态
        consecutive_slump = 0
        consecutive_high = 0
        for state in reversed(states):
            if state["is_slump"]:
                consecutive_slump += 1
            else:
                break
        for state in reversed(states):
            if state["is_high_pressure"]:
                consecutive_high += 1
            else:
                break

        # 判定干预
        intervention = None
        if consecutive_slump >= self.SLUMP_THRESHOLD:
            intervention = "reduce_pressure"
        elif consecutive_high >= self.HIGH_PRESSURE_THRESHOLD:
            intervention = "add_rest"

        # 记录稳态
        stability_score = self._calc_stability_score(states)
        pressure = self._determine_pressure(consecutive_slump, consecutive_high)

        record = LifeStabilityState(
            user_id=self.user_id,
            state_date=datetime.utcnow().strftime('%Y-%m-%d'),
            stability_score=stability_score,
            pressure_level=pressure,
            consecutive_slump_days=consecutive_slump,
            consecutive_high_days=consecutive_high,
            intervention=intervention,
            intervention_applied=intervention is not None,
        )
        self.session.add(record)
        await self.session.flush()

        return {
            "stability_score": stability_score,
            "pressure_level": pressure,
            "consecutive_slump": consecutive_slump,
            "consecutive_high": consecutive_high,
            "intervention": intervention,
            "message": self._intervention_message(intervention),
        }

    async def adjust_task_difficulty(self) -> dict[str, Any]:
        """任务难度自适应缩放"""
        # 获取近3天完成率
        completion_rate = await self._recent_completion_rate(days=3)
        energy = await self._current_energy()
        negative_feedback = await self._recent_negative_feedback()

        # 基础参数
        base_difficulty = 5.0
        base_count = 5

        # 调整因子
        factors = {}

        # 完成率调整
        if completion_rate > 0.8:
            base_difficulty *= 1.3
            base_count = int(base_count * 1.2)
            factors["completion"] = "high → increase"
        elif completion_rate < 0.5:
            base_difficulty *= 0.6
            base_count = max(2, int(base_count * 0.6))
            factors["completion"] = "low → decrease"

        # 精力调整
        if energy < 40:
            base_difficulty *= 0.7
            base_count = max(2, base_count - 2)
            factors["energy"] = "low → decrease"
        elif energy > 75:
            base_difficulty *= 1.2
            factors["energy"] = "high → increase"

        # 负反馈调整
        if negative_feedback >= 3:
            base_difficulty *= 0.5
            base_count = max(1, base_count - 3)
            factors["negative_feedback"] = "high → significant decrease"

        # 限制范围
        adjusted_difficulty = max(1.0, min(10.0, base_difficulty))
        adjusted_count = max(1, min(10, base_count))

        # 记录
        log = TaskDifficultyLog(
            user_id=self.user_id,
            task_date=datetime.utcnow().strftime('%Y-%m-%d'),
            original_difficulty=5.0,
            original_count=5,
            adjusted_difficulty=round(adjusted_difficulty, 1),
            adjusted_count=adjusted_count,
            adjustment_reason=str(factors),
            adjustment_factors=factors,
        )
        self.session.add(log)
        await self.session.flush()

        return {
            "original": {"difficulty": 5.0, "count": 5},
            "adjusted": {"difficulty": round(adjusted_difficulty, 1), "count": adjusted_count},
            "factors": factors,
        }

    async def _calc_recent_states(self, days: int = 7) -> list[dict]:
        """计算近N天状态"""
        states = []
        for i in range(days):
            day = (datetime.utcnow() - timedelta(days=i)).strftime('%Y-%m-%d')
            result = await self.session.execute(
                select(
                    func.count(BehaviorLog.id),
                    func.sum(func.cast(BehaviorLog.schedule_completed, Integer)),
                ).where(and_(
                    BehaviorLog.user_id == self.user_id,
                    BehaviorLog.dimension == "time",
                    func.strftime('%Y-%m-%d', BehaviorLog.created_at) == day,
                ))
            )
            row = result.one()
            total = row[0] or 0
            completed = row[1] or 0
            rate = completed / total if total > 0 else 0.5

            states.append({
                "date": day,
                "completion_rate": rate,
                "is_slump": rate < 0.3 and total > 0,
                "is_high_pressure": total >= 8,
            })
        return list(reversed(states))

    def _calc_stability_score(self, states: list[dict]) -> float:
        """计算稳态得分"""
        if not states:
            return 50.0

        # 完成率方差越小越稳定
        rates = [s["completion_rate"] for s in states if s.get("completion_rate", 0) > 0]
        if not rates:
            return 50.0

        avg = sum(rates) / len(rates)
        variance = sum((r - avg) ** 2 for r in rates) / len(rates)

        # 方差越小得分越高
        stability = max(0, 100 - variance * 200)
        return round(stability, 1)

    @staticmethod
    def _determine_pressure(slump: int, high: int) -> str:
        """判定压力等级"""
        if slump >= 5:
            return "critical"
        elif slump >= 3:
            return "low"  # 摆烂期=低压
        elif high >= 7:
            return "critical"
        elif high >= 5:
            return "high"
        return "normal"

    @staticmethod
    def _intervention_message(intervention: str | None) -> str:
        """干预消息"""
        messages = {
            "reduce_pressure": "检测到连续摆烂，已自动降低后续任务压力，增加轻松任务",
            "add_rest": "检测到连续高压，已主动安排休息缓冲",
            None: "生活状态正常，无需干预",
        }
        return messages.get(intervention, "状态正常")

    async def _recent_completion_rate(self, days: int = 3) -> float:
        """近N天完成率"""
        cutoff = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')
        result = await self.session.execute(
            select(
                func.count(BehaviorLog.id),
                func.sum(func.cast(BehaviorLog.schedule_completed, Integer)),
            ).where(and_(
                BehaviorLog.user_id == self.user_id,
                BehaviorLog.dimension == "time",
                func.strftime('%Y-%m-%d', BehaviorLog.created_at) >= cutoff,
            ))
        )
        row = result.one()
        total = row[0] or 0
        completed = row[1] or 0
        return completed / total if total > 0 else 0.5

    async def _current_energy(self) -> float:
        """当前精力值"""
        from app.services.energy_model import EnergyModel
        model = EnergyModel(self.session, self.user_id)
        record = await model.calculate_daily_energy()
        return record.total_energy

    async def _recent_negative_feedback(self, days: int = 3) -> int:
        """近N天负反馈数"""
        cutoff = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')
        result = await self.session.scalar(
            select(func.count(NegativeFeedback.id)).where(and_(
                NegativeFeedback.user_id == self.user_id,
                func.strftime('%Y-%m-%d', NegativeFeedback.created_at) >= cutoff,
            ))
        )
        return result or 0


