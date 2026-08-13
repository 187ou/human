"""失败轨迹专项复盘学习（Reflexion反思机制）

优先挖掘拖延、取消、超支、倦怠等负面行为轨迹，
定位失败诱因并生成规避策略。
"""
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import FailureMemory


class FailureLearner:
    """失败学习器"""

    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id

    async def record_failure(self, failure_type: str, title: str, description: str,
                              severity: int = 5, trigger: dict | None = None) -> FailureMemory:
        """记录失败"""
        # 根因分析
        root_cause = await self._analyze_root_cause(failure_type, description)

        # 生成规避策略
        strategy = await self._generate_avoidance(failure_type, root_cause)

        memory = FailureMemory(
            user_id=self.user_id,
            failure_type=failure_type,
            title=title,
            description=description,
            root_cause=root_cause,
            trigger_conditions=trigger or {},
            avoidance_strategy=strategy,
            severity=severity,
        )
        self.session.add(memory)
        await self.session.flush()
        return memory

    async def _analyze_root_cause(self, failure_type: str, description: str) -> str:
        """分析根因"""
        causes = {
            "delay": "任务难度过高或时间预估不足，导致拖延",
            "cancel": "计划冲突或优先级变化，导致取消",
            "overspend": "冲动消费或缺乏预算意识，导致超支",
            "burnout": "连续高压或休息不足，导致倦怠",
            "skip": "动力不足或习惯未养成，导致跳过",
        }
        return causes.get(failure_type, "待分析")

    async def _generate_avoidance(self, failure_type: str, root_cause: str) -> str:
        """生成规避策略"""
        strategies = {
            "delay": "将大任务拆解为15分钟微任务，设置阶梯式提醒",
            "cancel": "减少承诺数量，预留缓冲时间，提前确认优先级",
            "overspend": "大额消费前设置48小时冷静期，启用预算预警",
            "burnout": "连续高强度3天后强制安排休息日，降低任务量",
            "skip": "设置最低执行时长（如10分钟），完成后给予奖励",
        }
        return strategies.get(failure_type, "需要针对性分析")

    async def get_failure_patterns(self) -> dict[str, Any]:
        """获取失败模式"""
        result = await self.session.execute(
            select(FailureMemory).where(and_(
                FailureMemory.user_id == self.user_id,
                FailureMemory.is_resolved == False,
            )).order_by(FailureMemory.severity.desc())
        )
        failures = result.scalars().all()

        if not failures:
            return {"has_failures": False}

        # 统计
        type_counts = {}
        for f in failures:
            type_counts[f.failure_type] = type_counts.get(f.failure_type, 0) + 1

        worst_type = max(type_counts, key=type_counts.get) if type_counts else None

        return {
            "has_failures": True,
            "total_failures": len(failures),
            "type_distribution": type_counts,
            "worst_type": worst_type,
            "recent_failures": [
                {"title": f.title, "type": f.failure_type, "severity": f.severity, "strategy": f.avoidance_strategy}
                for f in failures[:5]
            ],
        }

    async def generate_counter_rules(self) -> list[dict]:
        """生成反向约束规则"""
        patterns = await self.get_failure_patterns()
        if not patterns["has_failures"]:
            return []

        rules = []
        for failure_type, count in patterns.get("type_distribution", {}).items():
            if count >= 2:  # 同类失败出现2次以上
                rule = self._create_counter_rule(failure_type)
                if rule:
                    rules.append(rule)

        return rules

    @staticmethod
    def _create_counter_rule(failure_type: str) -> dict | None:
        """创建反向约束规则"""
        counter_rules = {
            "delay": {
                "name": "拖延规避规则",
                "rule_expr": {"action": "split_task", "max_chunk_min": 15, "reminder_steps": 3},
            },
            "overspend": {
                "name": "冲动消费规避规则",
                "rule_expr": {"action": "cooling_period", "hours": 48, "threshold": 200},
            },
            "burnout": {
                "name": "倦怠规避规则",
                "rule_expr": {"action": "force_rest", "after_days": 3, "rest_hours": 24},
            },
            "skip": {
                "name": "跳过规避规则",
                "rule_expr": {"action": "minimum_execution", "min_minutes": 10},
            },
        }
        return counter_rules.get(failure_type)

    async def mark_resolved(self, failure_id: int) -> bool:
        """标记失败已解决"""
        memory = await self.session.get(FailureMemory, failure_id)
        if memory and memory.user_id == self.user_id:
            memory.is_resolved = True
            await self.session.flush()
            return True
        return False
