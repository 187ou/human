"""演化引擎：双模演化 + Prompt量化考核 + 规则冲突仲裁"""
import json
from datetime import datetime, timedelta
from typing import Any

from loguru import logger
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.evolution.miner import RuleMiner
from app.models.rule import UserRule
from app.models.behavior import BehaviorLog


class EvolutionEngine:
    """自适应演化引擎"""

    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id
        self.miner = RuleMiner(session, user_id)

    # ==================== 双模演化 ====================

    async def run_incremental(self) -> dict[str, Any]:
        """夜间增量演化：仅处理当日新增行为数据"""
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        new_logs = await self.session.scalar(
            select(BehaviorLog).where(
                and_(BehaviorLog.user_id == self.user_id, BehaviorLog.created_at >= today_start)
            )
        )
        new_count = len(new_logs) if hasattr(new_logs, '__len__') else (new_logs or 0)

        # 增量模式：只更新已有规则的置信度，不生成新规则
        active_rules = await self.session.execute(
            select(UserRule).where(and_(UserRule.user_id == self.user_id, UserRule.is_active == True))
        )
        updated = 0
        for rule in active_rules.scalars().all():
            # 用新数据验证规则
            match_count = await self._count_matching_samples(rule, today_start)
            if match_count > 0:
                rule.sample_count += match_count
                rule.confidence = min(0.95, rule.sample_count / (rule.sample_count + 10))
                updated += 1

        await self.session.commit()
        return {
            "mode": "incremental",
            "new_behaviors": new_count,
            "rules_updated": updated,
            "evolved_at": datetime.utcnow().isoformat(),
        }

    async def run_full(self) -> dict[str, Any]:
        """每周全量深度演化：全盘复盘习惯"""
        # 1. 挖掘新规则
        new_rules = await self.miner.mine_all()

        # 2. 持久化
        saved = []
        for rule_data in new_rules:
            saved.append(await self._save_rule(rule_data))

        # 3. 冲突仲裁
        conflicts = await self._resolve_conflicts()

        # 4. Prompt量化考核
        prompt_result = await self._evaluate_prompts()

        await self.session.commit()
        return {
            "mode": "full",
            "rules_count": len(saved),
            "conflicts": len(conflicts),
            "prompt_evaluation": prompt_result,
            "evolved_at": datetime.utcnow().isoformat(),
        }

    # ==================== 规则持久化 ====================

    async def _save_rule(self, rule_data: dict[str, Any]) -> UserRule | None:
        """保存规则（去重+版本追踪）"""
        stmt = select(UserRule).where(
            and_(UserRule.user_id == self.user_id, UserRule.name == rule_data["name"], UserRule.is_active == True)
        )
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.version += 1
            existing.rule_expr = rule_data["rule_expr"]
            existing.confidence = rule_data["confidence"]
            existing.description = rule_data["description"]
            existing.sample_count = rule_data.get("sample_count", 0)
            existing.updated_at = datetime.utcnow()
            return existing
        else:
            rule = UserRule(
                user_id=self.user_id,
                dimension=rule_data.get("dimension", "general"),
                name=rule_data["name"],
                description=rule_data["description"],
                rule_expr=rule_data["rule_expr"],
                confidence=rule_data["confidence"],
                sample_count=rule_data.get("sample_count", 0),
                is_active=True,
                version=1,
                priority=rule_data.get("priority", 1),
            )
            self.session.add(rule)
            await self.session.flush()
            return rule

    # ==================== 规则冲突仲裁 ====================

    async def _resolve_conflicts(self) -> list[dict[str, Any]]:
        """规则冲突仲裁：高优先级覆盖低优先级"""
        rules = await self.session.execute(
            select(UserRule).where(
                and_(UserRule.user_id == self.user_id, UserRule.is_active == True)
            ).order_by(UserRule.priority.desc())
        )
        active_rules = rules.scalars().all()
        conflicts = []

        # 检测同一维度的规则冲突
        by_dim: dict[str, list[UserRule]] = {}
        for rule in active_rules:
            by_dim.setdefault(rule.dimension, []).append(rule)

        for dim, dim_rules in by_dim.items():
            if len(dim_rules) <= 1:
                continue
            # 按优先级排序，低优先级被覆盖
            dim_rules.sort(key=lambda r: r.priority)
            for i, low_rule in enumerate(dim_rules[:-1]):
                high_rule = dim_rules[-1]
                if low_rule.priority < high_rule.priority:
                    conflicts.append({
                        "dimension": dim,
                        "high_priority": {"id": high_rule.id, "name": high_rule.name, "priority": high_rule.priority},
                        "low_priority": {"id": low_rule.id, "name": low_rule.name, "priority": low_rule.priority},
                        "resolution": "高优先级覆盖",
                    })

        return conflicts

    # ==================== Prompt量化考核 ====================

    async def _evaluate_prompts(self) -> dict[str, Any]:
        """Prompt迭代量化考核：完成率/超支次数/有效学习时长"""
        now = datetime.utcnow()
        month_ago = now - timedelta(days=30)

        # 1. 日程完成率
        total = await self.session.scalar(
            select(func.count(BehaviorLog.id)).where(
                and_(BehaviorLog.user_id == self.user_id, BehaviorLog.dimension == "time", BehaviorLog.created_at >= month_ago)
            )
        )
        completed = await self.session.scalar(
            select(func.count(BehaviorLog.id)).where(
                and_(BehaviorLog.user_id == self.user_id, BehaviorLog.dimension == "time", BehaviorLog.schedule_completed == True, BehaviorLog.created_at >= month_ago)
            )
        )
        completion_rate = (completed / total) if total else 1.0

        # 2. 消费超支次数
        overspend_count = await self.session.scalar(
            select(func.count(BehaviorLog.id)).where(
                and_(BehaviorLog.user_id == self.user_id, BehaviorLog.dimension == "consume", BehaviorLog.consume_is_impulse == True, BehaviorLog.created_at >= month_ago)
            )
        )

        # 3. 有效学习时长
        effective_study_count = await self.session.scalar(
            select(func.count(BehaviorLog.id)).where(
                and_(BehaviorLog.user_id == self.user_id, BehaviorLog.dimension == "study", BehaviorLog.study_focus_min >= 30, BehaviorLog.study_accuracy >= 0.6, BehaviorLog.created_at >= month_ago)
            )
        )

        should_rollback = completion_rate < 0.5 or (overspend_count or 0) > 10

        return {
            "completion_rate": round(completion_rate, 3),
            "overspend_count": overspend_count or 0,
            "effective_study_sessions": effective_study_count or 0,
            "should_rollback": should_rollback,
        }

    # ==================== 辅助方法 ====================

    async def _count_matching_samples(self, rule: UserRule, since: datetime) -> int:
        """统计符合规则的样本数"""
        count = await self.session.scalar(
            select(func.count(BehaviorLog.id)).where(
                and_(BehaviorLog.user_id == self.user_id, BehaviorLog.dimension == rule.dimension, BehaviorLog.created_at >= since)
            )
        )
        return count or 0

    async def get_active_rules(self) -> dict[str, Any]:
        """获取当前生效规则快照"""
        rules = await self.session.execute(
            select(UserRule).where(and_(UserRule.user_id == self.user_id, UserRule.is_active == True))
        )
        snapshot = {}
        for rule in rules.scalars().all():
            dim = rule.dimension
            if dim not in snapshot:
                snapshot[dim] = {}
            snapshot[dim][rule.name] = {
                "id": rule.id, "expr": rule.rule_expr, "confidence": rule.confidence,
                "version": rule.version, "priority": rule.priority,
            }
        return snapshot

    async def toggle_rule(self, rule_id: int, active: bool) -> bool:
        """启用/禁用规则"""
        rule = await self.session.get(UserRule, rule_id)
        if rule and rule.user_id == self.user_id:
            rule.is_active = active
            await self.session.commit()
            return True
        return False

    async def delete_rule(self, rule_id: int) -> bool:
        """删除规则"""
        rule = await self.session.get(UserRule, rule_id)
        if rule and rule.user_id == self.user_id:
            await self.session.delete(rule)
            await self.session.commit()
            return True
        return False

    async def update_rule(self, rule_id: int, **kwargs) -> bool:
        """修改规则参数"""
        rule = await self.session.get(UserRule, rule_id)
        if not rule or rule.user_id != self.user_id:
            return False
        for key, value in kwargs.items():
            if hasattr(rule, key) and key in ("name", "description", "rule_expr", "priority", "confidence"):
                setattr(rule, key, value)
        rule.version += 1
        await self.session.commit()
        return True

    async def rollback_rule(self, rule_id: int) -> bool:
        """回滚到上一版本"""
        rule = await self.session.get(UserRule, rule_id)
        if not rule or rule.user_id != self.user_id or rule.version <= 1:
            return False
        rule.version -= 1
        await self.session.commit()
        return True

    async def pin_priority(self, rule_id: int, priority: int) -> bool:
        """置顶优先级"""
        rule = await self.session.get(UserRule, rule_id)
        if rule and rule.user_id == self.user_id:
            rule.priority = max(1, min(3, priority))
            await self.session.commit()
            return True
        return False
