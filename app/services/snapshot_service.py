"""演化快照服务：存档+回滚"""
import json
from datetime import datetime
from typing import Any

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.snapshot import EvolutionSnapshot
from app.models.rule import UserRule


class SnapshotService:
    """演化快照管理器"""

    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id

    async def create_snapshot(self, snapshot_type: str = "full",
                               description: str | None = None) -> EvolutionSnapshot:
        """创建演化快照"""
        # 获取当前版本号
        latest = await self.session.scalar(
            select(func.max(EvolutionSnapshot.version)).where(
                EvolutionSnapshot.user_id == self.user_id
            )
        )
        version = (latest or 0) + 1

        # 获取当前规则
        rules = await self.session.execute(
            select(UserRule).where(and_(
                UserRule.user_id == self.user_id,
                UserRule.is_active == True,
            ))
        )
        active_rules = rules.scalars().all()

        rules_data = []
        confidence_sum = 0
        for rule in active_rules:
            rules_data.append({
                "id": rule.id,
                "name": rule.name,
                "dimension": rule.dimension,
                "description": rule.description,
                "rule_expr": rule.rule_expr,
                "confidence": rule.confidence,
                "version": rule.version,
                "priority": rule.priority,
            })
            confidence_sum += rule.confidence

        confidence_avg = confidence_sum / len(rules_data) if rules_data else 0

        snapshot = EvolutionSnapshot(
            user_id=self.user_id,
            version=version,
            snapshot_type=snapshot_type,
            rules_snapshot=rules_data,
            preferences_snapshot={},
            behavior_summary={"rules_count": len(rules_data)},
            rules_count=len(rules_data),
            confidence_avg=round(confidence_avg, 3),
            description=description or f"{snapshot_type} snapshot v{version}",
        )
        self.session.add(snapshot)
        await self.session.flush()
        return snapshot

    async def rollback_to_version(self, version: int) -> dict[str, Any]:
        """回滚到指定版本"""
        snapshot = await self.session.execute(
            select(EvolutionSnapshot).where(and_(
                EvolutionSnapshot.user_id == self.user_id,
                EvolutionSnapshot.version == version,
            ))
        )
        snap = snapshot.scalar_one_or_none()
        if not snap:
            return {"success": False, "message": "快照不存在"}

        # 禁用当前所有规则
        current_rules = await self.session.execute(
            select(UserRule).where(and_(
                UserRule.user_id == self.user_id,
                UserRule.is_active == True,
            ))
        )
        for rule in current_rules.scalars().all():
            rule.is_active = False

        # 恢复快照中的规则
        restored_count = 0
        for rule_data in snap.rules_snapshot:
            existing = await self.session.execute(
                select(UserRule).where(and_(
                    UserRule.user_id == self.user_id,
                    UserRule.name == rule_data["name"],
                ))
            )
            rule = existing.scalar_one_or_none()
            if rule:
                rule.is_active = True
                rule.rule_expr = rule_data["rule_expr"]
                rule.confidence = rule_data["confidence"]
                rule.version = rule_data["version"]
                rule.priority = rule_data.get("priority", 1)
            else:
                new_rule = UserRule(
                    user_id=self.user_id,
                    dimension=rule_data["dimension"],
                    name=rule_data["name"],
                    description=rule_data["description"],
                    rule_expr=rule_data["rule_expr"],
                    confidence=rule_data["confidence"],
                    version=rule_data["version"],
                    priority=rule_data.get("priority", 1),
                    is_active=True,
                )
                self.session.add(new_rule)
            restored_count += 1

        await self.session.flush()
        return {
            "success": True,
            "restored_count": restored_count,
            "version": version,
            "message": f"已回滚到版本 v{version}，恢复{restored_count}条规则",
        }

    async def list_snapshots(self, limit: int = 20) -> list[EvolutionSnapshot]:
        """获取快照列表"""
        result = await self.session.execute(
            select(EvolutionSnapshot)
            .where(EvolutionSnapshot.user_id == self.user_id)
            .order_by(EvolutionSnapshot.version.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
