"""元演化调控Agent（进化的管理者）

专职监控演化效果，不处理生活业务。
判断演化状态、调整频次、触发探索性变异。
"""
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.engine import MetaEvolutionState, EvolutionLayer


class MetaEvolutionAgent:
    """元演化调控Agent

    职责：
    1. 监控演化收敛度
    2. 检测停滞/局部最优
    3. 调整演化频次和采样权重
    4. 触发探索性变异
    """

    # 调控阈值
    STAGNATION_THRESHOLD = 3  # 连续3次无改进视为停滞
    CONVERGENCE_THRESHOLD = 0.8  # 收敛度超过此值视为收敛
    EXPLORATION_INTERVAL = 7  # 每7天考虑一次探索

    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id

    async def evaluate_and_adjust(self) -> dict[str, Any]:
        """评估演化状态并调整"""
        # 获取或创建元状态
        state = await self._get_or_create_state()

        # 评估近期演化效果
        recent_layers = await self._get_recent_layers(days=7)

        # 计算收敛度
        convergence = self._calc_convergence(recent_layers)

        # 检测停滞
        stagnation = self._detect_stagnation(recent_layers, state)

        # 做出调控决策
        decision = self._make_decision(state, convergence, stagnation)

        # 更新状态
        state.convergence_score = convergence
        state.stagnation_counter = stagnation["counter"]
        state.current_phase = decision["phase"]
        state.evolution_speed = decision["speed"]
        state.exploration_rate = decision["exploration_rate"]
        state.last_decision = decision["action"]
        state.decision_reason = decision["reason"]

        await self.session.flush()

        return {
            "phase": decision["phase"],
            "speed": decision["speed"],
            "convergence": round(convergence, 3),
            "stagnation_counter": stagnation["counter"],
            "action": decision["action"],
            "reason": decision["reason"],
        }

    async def _get_or_create_state(self) -> MetaEvolutionState:
        """获取或创建元状态"""
        result = await self.session.execute(
            select(MetaEvolutionState).where(MetaEvolutionState.user_id == self.user_id)
        )
        state = result.scalar_one_or_none()

        if not state:
            state = MetaEvolutionState(user_id=self.user_id)
            self.session.add(state)
            await self.session.flush()

        return state

    async def _get_recent_layers(self, days: int = 7) -> list[EvolutionLayer]:
        """获取近期演化记录"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        result = await self.session.execute(
            select(EvolutionLayer).where(and_(
                EvolutionLayer.user_id == self.user_id,
                EvolutionLayer.triggered_at >= cutoff,
            )).order_by(EvolutionLayer.triggered_at)
        )
        return list(result.scalars().all())

    def _calc_convergence(self, layers: list[EvolutionLayer]) -> float:
        """计算收敛度"""
        if len(layers) < 2:
            return 0.5

        # 计算效果分数的方差
        scores = [l.effectiveness_score for l in layers if l.effectiveness_score > 0]
        if len(scores) < 2:
            return 0.5

        avg = sum(scores) / len(scores)
        variance = sum((s - avg) ** 2 for s in scores) / len(scores)

        # 方差越小，收敛度越高
        convergence = max(0, 1 - variance)
        return convergence

    def _detect_stagnation(self, layers: list[EvolutionLayer], state: MetaEvolutionState) -> dict:
        """检测停滞"""
        if not layers:
            return {"counter": state.stagnation_counter, "is_stagnant": False}

        # 最近几次演化是否有改进
        recent = layers[-3:]
        improvements = sum(1 for l in recent if l.effectiveness_score > 0.5)

        if improvements == 0:
            counter = state.stagnation_counter + 1
        else:
            counter = 0

        return {
            "counter": counter,
            "is_stagnant": counter >= self.STAGNATION_THRESHOLD,
        }

    def _make_decision(self, state: MetaEvolutionState, convergence: float,
                        stagnation: dict) -> dict:
        """做出调控决策"""
        # 停滞检测
        if stagnation["is_stagnant"]:
            return {
                "phase": "exploring",
                "speed": "fast",
                "exploration_rate": 0.3,
                "action": "trigger_exploratory_mutation",
                "reason": f"连续{stagnation['counter']}次无改进，触发探索性变异",
            }

        # 收敛检测
        if convergence > self.CONVERGENCE_THRESHOLD:
            return {
                "phase": "converging",
                "speed": "slow",
                "exploration_rate": 0.05,
                "action": "reduce_frequency",
                "reason": f"收敛度{convergence:.0%}，降低演化频次",
            }

        # 正常状态
        return {
            "phase": "stable",
            "speed": "normal",
            "exploration_rate": 0.1,
            "action": "maintain",
            "reason": "演化状态正常，维持当前参数",
        }
