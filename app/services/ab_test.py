"""多版本规则A/B测试引擎"""
from datetime import datetime
from typing import Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evolution import RuleABTest
from app.models.rule import UserRule


class ABTestManager:
    """规则A/B测试管理器

    同一行为同时保留两套规则小版本：
    - A版本：现有规则
    - B版本：新生成规则
    - 自动对比效果，择优留存
    """

    MIN_SAMPLES = 5  # 最少样本数才能判定胜负

    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id

    async def create_test(self, test_name: str, dimension: str,
                           rule_a_expr: dict, rule_b_expr: dict) -> RuleABTest:
        """创建A/B测试"""
        # 创建A版本规则
        rule_a = UserRule(
            user_id=self.user_id,
            dimension=dimension,
            name=f"{test_name}_A",
            description=f"A/B测试A版本: {test_name}",
            rule_expr=rule_a_expr,
            confidence=0.5,
            version=1,
            is_active=True,
        )
        self.session.add(rule_a)
        await self.session.flush()

        # 创建B版本规则
        rule_b = UserRule(
            user_id=self.user_id,
            dimension=dimension,
            name=f"{test_name}_B",
            description=f"A/B测试B版本: {test_name}",
            rule_expr=rule_b_expr,
            confidence=0.5,
            version=1,
            is_active=True,
        )
        self.session.add(rule_b)
        await self.session.flush()

        # 创建测试记录
        test = RuleABTest(
            user_id=self.user_id,
            test_name=test_name,
            dimension=dimension,
            rule_a_id=rule_a.id,
            rule_a_expr=rule_a_expr,
            rule_b_id=rule_b.id,
            rule_b_expr=rule_b_expr,
            status="running",
        )
        self.session.add(test)
        await self.session.flush()
        return test

    async def record_sample(self, test_id: int, version: str, score: float) -> None:
        """记录测试样本"""
        test = await self.session.get(RuleABTest, test_id)
        if not test or test.user_id != self.user_id:
            return

        if version == "A":
            # 移动平均
            total_score = test.a_score * test.a_samples + score
            test.a_samples += 1
            test.a_score = total_score / test.a_samples
        elif version == "B":
            total_score = test.b_score * test.b_samples + score
            test.b_samples += 1
            test.b_score = total_score / test.b_samples

        # 检查是否可以判定胜负
        if test.a_samples >= self.MIN_SAMPLES and test.b_samples >= self.MIN_SAMPLES:
            await self._evaluate_test(test)

        await self.session.flush()

    async def _evaluate_test(self, test: RuleABTest) -> None:
        """评估测试结果"""
        diff = abs(test.a_score - test.b_score)
        threshold = 0.1  # 差异阈值

        if diff < threshold:
            test.status = "tie"
            test.winner = None
        elif test.a_score > test.b_score:
            test.status = "a_wins"
            test.winner = "A"
            # 禁用B版本
            await self._disable_rule(test.rule_b_id)
        else:
            test.status = "b_wins"
            test.winner = "B"
            # 禁用A版本
            await self._disable_rule(test.rule_a_id)

        test.ended_at = datetime.utcnow()

    async def _disable_rule(self, rule_id: int | None) -> None:
        """禁用规则"""
        if not rule_id:
            return
        rule = await self.session.get(UserRule, rule_id)
        if rule:
            rule.is_active = False

    async def get_active_tests(self) -> list[RuleABTest]:
        """获取进行中的测试"""
        result = await self.session.execute(
            select(RuleABTest).where(and_(
                RuleABTest.user_id == self.user_id,
                RuleABTest.status == "running",
            )).order_by(RuleABTest.started_at.desc())
        )
        return list(result.scalars().all())

    async def get_test_history(self, limit: int = 10) -> list[RuleABTest]:
        """获取测试历史"""
        result = await self.session.execute(
            select(RuleABTest).where(
                RuleABTest.user_id == self.user_id
            ).order_by(RuleABTest.started_at.desc()).limit(limit)
        )
        return list(result.scalars().all())
