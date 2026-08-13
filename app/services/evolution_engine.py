"""分层闭环自演化引擎（总控核心）"""
import hashlib
import json
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.engine import EvolutionLayer, GitSnapshot, SandboxSimulation
from app.models.rule import UserRule


class EvolutionEngine:
    """三段式分层进化架构

    三层闭环：
    1. 在线即时反射（Online Immediate Reflection）- 单次任务后微调
    2. 夜间轻量化演化（Nightly Lightweight）- 仅处理当日新数据
    3. 周度全局深度演化（Weekly Deep）- 全量复盘重构
    """

    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id

    # ==================== 第1层：在线即时反射 ====================

    async def online_reflection(self, event_type: str, event_data: dict) -> dict[str, Any]:
        """在线即时反射：单次任务完成后立刻微调规则参数

        触发时机：任务完成/失败/拖延后立即执行
        计算开销：极低（仅调整数值参数，不生成新规则）
        """
        # 查找受影响的相关规则
        affected_rules = await self._find_related_rules(event_data)

        modifications = []
        for rule in affected_rules:
            # 小幅调整置信度（±0.05）
            old_confidence = rule.confidence

            if event_type == "task_completed":
                rule.confidence = min(0.95, rule.confidence + 0.02)
            elif event_type == "task_failed":
                rule.confidence = max(0.1, rule.confidence - 0.05)
            elif event_type == "task_delayed":
                rule.confidence = max(0.1, rule.confidence - 0.03)

            if rule.confidence != old_confidence:
                modifications.append({
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "old_confidence": old_confidence,
                    "new_confidence": rule.confidence,
                })

        # 记录
        layer = EvolutionLayer(
            user_id=self.user_id,
            layer_type="online",
            trigger_event=event_type,
            rules_affected=len(modifications),
            rules_modified=len(modifications),
            details={"modifications": modifications, "event_data": event_data},
        )
        self.session.add(layer)
        await self.session.flush()

        return {
            "layer": "online",
            "modifications": len(modifications),
            "details": modifications,
        }

    # ==================== 第2层：夜间轻量化演化 ====================

    async def nightly_evolution(self) -> dict[str, Any]:
        """夜间轻量化演化：仅处理当日新增行为日志

        触发时机：每日凌晨2点（APScheduler调度）
        计算开销：低（仅处理增量数据，不调用LLM）
        """
        today = datetime.utcnow().strftime('%Y-%m-%d')

        # 获取当日新增行为
        from app.models.behavior import BehaviorLog
        from sqlalchemy import func, Integer

        new_logs = await self.session.execute(
            select(BehaviorLog).where(and_(
                BehaviorLog.user_id == self.user_id,
                func.strftime('%Y-%m-%d', BehaviorLog.created_at) == today,
            ))
        )
        daily_logs = new_logs.scalars().all()

        if not daily_logs:
            return {"layer": "nightly", "status": "no_new_data"}

        # 更新已有规则的置信度（基于新数据验证）
        rules = await self.session.execute(
            select(UserRule).where(and_(
                UserRule.user_id == self.user_id,
                UserRule.is_active == True,
            ))
        )
        active_rules = rules.scalars().all()

        updated = 0
        for rule in active_rules:
            # 验证规则是否被新数据支持
            matching = sum(1 for log in daily_logs if self._log_matches_rule(log, rule))
            contradicting = sum(1 for log in daily_logs if self._log_contradicts_rule(log, rule))

            if matching > 0:
                rule.confidence = min(0.95, rule.confidence + matching * 0.01)
                updated += 1
            if contradicting > 0:
                rule.confidence = max(0.1, rule.confidence - contradicting * 0.02)
                updated += 1

        # 记录
        layer = EvolutionLayer(
            user_id=self.user_id,
            layer_type="nightly",
            trigger_event="daily_incremental",
            rules_affected=updated,
            rules_modified=updated,
            details={"new_logs": len(daily_logs), "rules_updated": updated},
        )
        self.session.add(layer)
        await self.session.flush()

        return {
            "layer": "nightly",
            "new_logs": len(daily_logs),
            "rules_updated": updated,
        }

    # ==================== 第3层：周度全局深度演化 ====================

    async def weekly_evolution(self) -> dict[str, Any]:
        """周度全局深度演化：全量复盘+规则重构+Prompt迭代

        触发时机：每周日凌晨（APScheduler调度）
        计算开销：高（全量数据分析+LLM调用）
        """
        # 1. 创建演化快照
        snapshot = await self._create_snapshot("weekly_deep_evolution")

        # 2. 全量行为分析
        all_logs = await self._get_all_behavior_logs()

        # 3. 规则重构
        rules = await self.session.execute(
            select(UserRule).where(UserRule.user_id == self.user_id)
        )
        all_rules = rules.scalars().all()

        # 标记过时规则
        deprecated = 0
        for rule in all_rules:
            days_old = (datetime.utcnow() - rule.updated_at).days
            if days_old > 30 and rule.confidence < 0.3:
                rule.is_active = False
                deprecated += 1

        # 4. 生成新规则（基于统计学挖掘）
        from app.evolution.miner import RuleMiner
        miner = RuleMiner(self.session, self.user_id)
        new_rules = await miner.mine_all()

        # 沙箱验证
        safe_rules = []
        for rule_data in new_rules:
            check = await self._sandbox_check(rule_data)
            if check["is_safe"]:
                safe_rules.append(rule_data)

        # 保存安全规则
        created = 0
        for rule_data in safe_rules:
            rule = UserRule(
                user_id=self.user_id,
                dimension=rule_data.get("dimension", "general"),
                name=rule_data["name"],
                description=rule_data["description"],
                rule_expr=rule_data["rule_expr"],
                confidence=rule_data["confidence"],
                version=1,
                is_active=True,
            )
            self.session.add(rule)
            created += 1

        # 记录
        layer = EvolutionLayer(
            user_id=self.user_id,
            layer_type="weekly",
            trigger_event="weekly_full_review",
            rules_affected=len(all_rules),
            rules_created=created,
            rules_deprecated=deprecated,
            details={"new_rules": created, "deprecated": deprecated, "snapshot_hash": snapshot["hash"]},
        )
        self.session.add(layer)
        await self.session.flush()

        return {
            "layer": "weekly",
            "new_rules": created,
            "deprecated": deprecated,
            "snapshot_hash": snapshot["hash"],
        }

    # ==================== 辅助方法 ====================

    async def _find_related_rules(self, event_data: dict) -> list[UserRule]:
        """查找与事件相关的规则"""
        dimension = event_data.get("dimension", "general")
        result = await self.session.execute(
            select(UserRule).where(and_(
                UserRule.user_id == self.user_id,
                UserRule.dimension == dimension,
                UserRule.is_active == True,
            ))
        )
        return list(result.scalars().all())

    @staticmethod
    def _log_matches_rule(log, rule: UserRule) -> bool:
        """日志是否支持规则"""
        if log.dimension != rule.dimension:
            return False
        if log.dimension == "time" and log.schedule_completed:
            return True
        if log.dimension == "study" and log.study_accuracy and log.study_accuracy > 0.7:
            return True
        return False

    @staticmethod
    def _log_contradicts_rule(log, rule: UserRule) -> bool:
        """日志是否反驳规则"""
        if log.dimension != rule.dimension:
            return False
        if log.dimension == "time" and log.schedule_completed is False:
            return True
        if log.dimension == "study" and log.study_accuracy and log.study_accuracy < 0.3:
            return True
        return False

    async def _create_snapshot(self, message: str) -> dict:
        """创建Git式快照"""
        rules = await self.session.execute(
            select(UserRule).where(UserRule.user_id == self.user_id)
        )
        all_rules = rules.scalars().all()

        rules_data = [{"id": r.id, "name": r.name, "expr": r.rule_expr, "confidence": r.confidence} for r in all_rules]
        content_hash = hashlib.md5(json.dumps(rules_data, sort_keys=True, default=str).encode()).hexdigest()[:12]

        snapshot = GitSnapshot(
            user_id=self.user_id,
            commit_hash=content_hash,
            message=message,
            rules_snapshot=rules_data,
            changes_count=len(all_rules),
        )
        self.session.add(snapshot)
        await self.session.flush()
        return {"hash": content_hash, "id": snapshot.id}

    async def _sandbox_check(self, rule_data: dict) -> dict:
        """沙箱安全验证"""
        # 简化的安全检查
        risks = []

        # 检查是否会导致任务过载
        if rule_data.get("rule_expr", {}).get("task_count_boost", 0) > 5:
            risks.append("task_overload")

        # 检查是否会导致预算问题
        if rule_data.get("rule_expr", {}).get("budget_factor", 1.0) > 2.0:
            risks.append("budget_risk")

        is_safe = len(risks) == 0

        sim = SandboxSimulation(
            user_id=self.user_id,
            content_type="rule",
            content=rule_data,
            content_name=rule_data.get("name", ""),
            is_safe=is_safe,
            risk_checks={"risks": risks},
            action="approved" if is_safe else "rejected",
        )
        self.session.add(sim)
        await self.session.flush()

        return {"is_safe": is_safe, "risks": risks}

    async def _get_all_behavior_logs(self):
        """获取全量行为日志"""
        from app.models.behavior import BehaviorLog
        result = await self.session.execute(
            select(BehaviorLog).where(BehaviorLog.user_id == self.user_id)
        )
        return result.scalars().all()
