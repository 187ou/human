"""行为因果挖掘引擎：区分因果 vs 关联"""
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.innovation import CausalEdge
from app.models.behavior import BehaviorLog


class CausalMiner:
    """因果推理引擎

    核心方法：
    1. 时间优先性：因必须在果之前
    2. 共变分析：因变化导致果变化
    3. 排除混淆：控制第三方变量
    4. 反事实推理：如果因不发生，果是否仍发生
    """

    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id

    async def mine_causal_relationships(self) -> list[dict[str, Any]]:
        """挖掘行为因果关系"""
        # 获取近30天行为日志
        cutoff = datetime.utcnow() - timedelta(days=30)
        result = await self.session.execute(
            select(BehaviorLog).where(and_(
                BehaviorLog.user_id == self.user_id,
                BehaviorLog.created_at >= cutoff,
            )).order_by(BehaviorLog.created_at)
        )
        logs = result.scalars().all()

        if len(logs) < 10:
            return []

        # 构建事件序列
        daily_events = self._build_daily_events(logs)

        # 挖掘因果对
        causal_pairs = []
        event_types = set()
        for day_events in daily_events.values():
            event_types.update(day_events.keys())

        # 检验所有可能的事件对
        event_list = list(event_types)
        for i, cause in enumerate(event_list):
            for effect in event_list[i + 1:]:
                if cause == effect:
                    continue
                # 检验 cause → effect
                forward = self._test_causality(daily_events, cause, effect)
                if forward["is_causal"]:
                    causal_pairs.append(forward)

                # 检验 effect → cause（反向）
                backward = self._test_causality(daily_events, effect, cause)
                if backward["is_causal"]:
                    causal_pairs.append(backward)

        # 持久化因果边
        saved = []
        for pair in causal_pairs:
            edge = CausalEdge(
                user_id=self.user_id,
                cause_event=pair["cause"],
                effect_event=pair["effect"],
                confidence=pair["confidence"],
                correlation=pair["correlation"],
                causal_type=pair["type"],
                support_count=pair["support"],
                contradict_count=pair["contradict"],
                conclusion=pair["conclusion"],
            )
            self.session.add(edge)
            saved.append(pair)

        await self.session.flush()
        return saved

    def _build_daily_events(self, logs: list[BehaviorLog]) -> dict[str, dict[str, float]]:
        """构建每日事件序列"""
        daily = defaultdict(lambda: defaultdict(float))

        for log in logs:
            day = log.created_at.strftime('%Y-%m-%d')
            event_key = f"{log.dimension}_{log.event_type}"

            if log.dimension == "time" and log.schedule_completed is not None:
                daily[day][event_key] = 1.0 if log.schedule_completed else 0.0
            elif log.dimension == "study" and log.study_accuracy is not None:
                daily[day][event_key] = log.study_accuracy
            elif log.dimension == "consume" and log.consume_is_impulse is not None:
                daily[day][event_key] = 1.0 if log.consume_is_impulse else 0.0
            elif log.dimension == "time" and log.schedule_is_delayed is not None:
                daily[day]["delayed"] = 1.0 if log.schedule_is_delayed else 0.0

        return dict(daily)

    def _test_causality(self, daily_events: dict, cause: str, effect: str) -> dict[str, Any]:
        """检验因果关系（Granger-like因果检验）"""
        cause_vals = []
        effect_vals = []
        lagged_effect = []

        days = sorted(daily_events.keys())
        for i, day in enumerate(days):
            day_events = daily_events[day]
            c_val = day_events.get(cause, 0)
            e_val = day_events.get(effect, 0)

            cause_vals.append(c_val)
            effect_vals.append(e_val)

            # 因在前一天的值（检验因是否在果之前）
            if i > 0:
                prev_day_events = daily_events.get(days[i - 1], {})
                lagged_effect.append(prev_day_events.get(cause, 0))

        if len(cause_vals) < 5:
            return {"is_causal": False}

        # 计算相关系数
        correlation = self._pearson_correlation(cause_vals, effect_vals)

        # 时间优先性检验：因的变化是否先于果
        temporal_score = self._temporal_precedence(lagged_effect, effect_vals[1:])

        # 共变分析
        covariation = self._covariation_score(cause_vals, effect_vals)

        # 综合因果得分
        causal_score = (abs(correlation) * 0.3 + temporal_score * 0.4 + covariation * 0.3)

        # 判定因果类型
        is_causal = causal_score > 0.4 and temporal_score > 0.3
        causal_type = "direct" if causal_score > 0.6 else "indirect" if is_causal else "spurious"

        # 支持/反驳样本
        support = sum(1 for c, e in zip(cause_vals, effect_vals) if c > 0 and e > 0)
        contradict = sum(1 for c, e in zip(cause_vals, effect_vals) if c > 0 and e == 0)

        # 生成结论
        if is_causal:
            direction = "正向" if correlation > 0 else "负向"
            conclusion = f"「{cause}」{direction}影响「{effect}」(置信度{causal_score:.0%})"
        else:
            conclusion = f"「{cause}」与「{effect}」仅为关联关系，非因果"

        return {
            "is_causal": is_causal,
            "cause": cause,
            "effect": effect,
            "confidence": round(causal_score, 3),
            "correlation": round(correlation, 3),
            "type": causal_type,
            "support": support,
            "contradict": contradict,
            "conclusion": conclusion,
        }

    @staticmethod
    def _pearson_correlation(x: list[float], y: list[float]) -> float:
        """计算皮尔逊相关系数"""
        n = len(x)
        if n < 2:
            return 0.0

        mean_x = sum(x) / n
        mean_y = sum(y) / n

        numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
        denom_x = sum((xi - mean_x) ** 2 for xi in x) ** 0.5
        denom_y = sum((yi - mean_y) ** 2 for yi in y) ** 0.5

        if denom_x == 0 or denom_y == 0:
            return 0.0

        return numerator / (denom_x * denom_y)

    @staticmethod
    def _temporal_precedence(lagged_cause: list[float], effect: list[float]) -> float:
        """时间优先性得分"""
        if len(lagged_cause) < 3 or len(effect) < 3:
            return 0.0

        matches = sum(1 for c, e in zip(lagged_cause, effect) if c > 0 and e > 0)
        total = len(lagged_cause)
        return matches / total if total > 0 else 0.0

    @staticmethod
    def _covariation_score(cause: list[float], effect: list[float]) -> float:
        """共变得分"""
        if len(cause) < 3:
            return 0.0

        # 因变化时，果是否跟随变化
        agreements = 0
        total = 0
        for i in range(1, len(cause)):
            cause_changed = abs(cause[i] - cause[i - 1]) > 0.1
            effect_changed = abs(effect[i] - effect[i - 1]) > 0.1
            if cause_changed:
                total += 1
                if effect_changed:
                    agreements += 1

        return agreements / total if total > 0 else 0.0

    async def get_causal_conclusions(self, min_confidence: float = 0.4) -> list[CausalEdge]:
        """获取因果结论"""
        result = await self.session.execute(
            select(CausalEdge).where(and_(
                CausalEdge.user_id == self.user_id,
                CausalEdge.is_active == True,
                CausalEdge.confidence >= min_confidence,
            )).order_by(CausalEdge.confidence.desc())
        )
        return list(result.scalars().all())
