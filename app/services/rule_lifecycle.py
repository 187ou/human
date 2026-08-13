"""规则全生命周期自治管理：诞生→生效→迭代→休眠→过期销毁"""
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rule import UserRule
from app.models.innovation import RuleLifecycleLog


class RuleLifecycleManager:
    """规则生命周期全自动管理"""

    # 过期规则：30天未触发
    EXPIRY_DAYS = 30
    # 淘汰规则：置信度<0.2且60天未触发
    ELIMINATE_CONFIDENCE = 0.2
    ELIMINATE_DAYS = 60

    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id

    async def process_lifecycle(self) -> dict[str, list[str]]:
        """处理所有规则的生命周期"""
        result = {"expired": [], "eliminated": [], "activated": []}

        rules = await self.session.execute(
            select(UserRule).where(UserRule.user_id == self.user_id)
        )
        all_rules = rules.scalars().all()

        for rule in all_rules:
            days_since_update = (datetime.utcnow() - rule.updated_at).days

            # 检查过期
            if rule.is_active and days_since_update >= self.EXPIRY_DAYS:
                if rule.confidence < 0.5:
                    rule.is_active = False
                    await self._log_lifecycle(rule.id, "expired", "expired",
                        f"{days_since_update}天未触发，自动过期")
                    result["expired"].append(rule.name)

            # 检查淘汰
            if days_since_update >= self.ELIMINATE_DAYS:
                if rule.confidence < self.ELIMINATE_CONFIDENCE:
                    rule.is_active = False
                    await self._log_lifecycle(rule.id, "eliminated", "eliminated",
                        f"置信度{rule.confidence:.2f}过低且{days_since_update}天未触发，淘汰")
                    result["eliminated"].append(rule.name)

            # 自动激活高置信度规则
            if not rule.is_active and rule.confidence >= 0.7:
                rule.is_active = True
                await self._log_lifecycle(rule.id, "activated", "active",
                    f"置信度{rule.confidence:.2f}恢复，自动激活")
                result["activated"].append(rule.name)

        await self.session.flush()
        return result

    async def _log_lifecycle(self, rule_id: int, stage: str, action: str,
                              reason: str = "") -> None:
        """记录生命周期日志"""
        log = RuleLifecycleLog(
            user_id=self.user_id,
            rule_id=rule_id,
            stage=stage,
            action=action,
            reason=reason,
        )
        self.session.add(log)

    async def get_lifecycle_stats(self) -> dict[str, Any]:
        """获取生命周期统计"""
        rules = await self.session.execute(
            select(UserRule).where(UserRule.user_id == self.user_id)
        )
        all_rules = rules.scalars().all()

        active = [r for r in all_rules if r.is_active]
        inactive = [r for r in all_rules if not r.is_active]

        return {
            "total": len(all_rules),
            "active": len(active),
            "inactive": len(inactive),
            "avg_confidence": sum(r.confidence for r in active) / len(active) if active else 0,
            "expiring_soon": len([r for r in active if (datetime.utcnow() - r.updated_at).days >= 20]),
        }
