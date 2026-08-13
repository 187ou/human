"""规则种群遗传演化引擎（GA遗传算法）

将用户个性化规则视作种群个体，具备：
- 交叉（Crossover）：合并两条有效规则
- 变异（Mutation）：小幅调整规则参数
- 筛选（Selection）：依据适应度打分
- 淘汰（Elimination）：劣质规则清除
"""
import random
from datetime import datetime
from typing import Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rule_population import RuleIndividual


class GeneticRuleEvolution:
    """规则遗传演化引擎"""

    # GA参数
    MUTATION_RATE = 0.15
    CROSSOVER_RATE = 0.3
    ELITE_RATIO = 0.2
    POPULATION_SIZE = 10

    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id

    async def evolve_generation(self) -> dict[str, Any]:
        """执行一代演化"""
        # 获取当前种群
        population = await self._get_population()

        if len(population) < 2:
            return {"status": "insufficient_population"}

        # 1. 评估适应度
        evaluated = await self._evaluate_fitness(population)

        # 2. 精英保留
        elites = self._select_elites(evaluated)

        # 3. 交叉产生后代
        offspring = self._crossover(evaluated)

        # 4. 变异
        mutated = self._mutate(offspring + elites)

        # 5. 淘汰劣质
        survivors = self._selection(mutated)

        # 6. 更新种群
        await self._update_population(survivors)

        await self.session.commit()
        return {
            "status": "evolved",
            "generation": max(r.generation for r in survivors) if survivors else 1,
            "population_size": len(survivors),
            "elites": len(elites),
            "offspring": len(offspring),
        }

    async def _get_population(self) -> list[RuleIndividual]:
        """获取当前种群"""
        result = await self.session.execute(
            select(RuleIndividual).where(and_(
                RuleIndividual.user_id == self.user_id,
                RuleIndividual.is_active == True,
            )).order_by(RuleIndividual.fitness_score.desc())
        )
        return list(result.scalars().all())

    async def _evaluate_fitness(self, population: list[RuleIndividual]) -> list[RuleIndividual]:
        """评估适应度"""
        for rule in population:
            if rule.total_samples > 0:
                # 适应度 = 成功率 * 置信度
                success_rate = rule.success_samples / rule.total_samples
                rule.fitness_score = success_rate * rule.confidence
            else:
                rule.fitness_score = 0.3  # 默认值
        return population

    def _select_elites(self, population: list[RuleIndividual]) -> list[RuleIndividual]:
        """精英保留"""
        sorted_pop = sorted(population, key=lambda r: r.fitness_score, reverse=True)
        elite_count = max(1, int(len(sorted_pop) * self.ELITE_RATIO))
        return sorted_pop[:elite_count]

    def _crossover(self, population: list[RuleIndividual]) -> list[RuleIndividual]:
        """交叉：合并两条有效规则"""
        offspring = []
        sorted_pop = sorted(population, key=lambda r: r.fitness_score, reverse=True)

        for i in range(0, len(sorted_pop) - 1, 2):
            if random.random() < self.CROSSOVER_RATE:
                parent1 = sorted_pop[i]
                parent2 = sorted_pop[i + 1]

                # 合并规则表达式
                child_expr = self._merge_expr(parent1.rule_expr, parent2.rule_expr)

                child = RuleIndividual(
                    user_id=self.user_id,
                    name=f"crossover_{parent1.id}_{parent2.id}",
                    dimension=parent1.dimension,
                    rule_expr=child_expr,
                    origin="crossover",
                    parent_ids=[parent1.id, parent2.id],
                    generation=max(parent1.generation, parent2.generation) + 1,
                )
                offspring.append(child)

        return offspring

    def _merge_expr(self, expr1: dict, expr2: dict) -> dict:
        """合并两个规则表达式"""
        merged = {}
        all_keys = set(expr1.keys()) | set(expr2.keys())
        for key in all_keys:
            v1 = expr1.get(key)
            v2 = expr2.get(key)
            if v1 is not None and v2 is not None:
                # 数值取平均
                if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                    merged[key] = (v1 + v2) / 2
                else:
                    merged[key] = random.choice([v1, v2])
            elif v1 is not None:
                merged[key] = v1
            else:
                merged[key] = v2
        return merged

    def _mutate(self, population: list[RuleIndividual]) -> list[RuleIndividual]:
        """变异：小幅调整规则参数"""
        for rule in population:
            if random.random() < self.MUTATION_RATE:
                mutated_expr = dict(rule.rule_expr)
                for key in mutated_expr:
                    if isinstance(mutated_expr[key], (int, float)):
                        # ±20% 变异
                        delta = mutated_expr[key] * random.uniform(-0.2, 0.2)
                        mutated_expr[key] = max(0, mutated_expr[key] + delta)

                mutated = RuleIndividual(
                    user_id=self.user_id,
                    name=f"mutation_{rule.id}",
                    dimension=rule.dimension,
                    rule_expr=mutated_expr,
                    origin="mutation",
                    parent_ids=[rule.id],
                    generation=rule.generation + 1,
                )
                population.append(mutated)

        return population

    def _selection(self, population: list[RuleIndividual]) -> list[RuleIndividual]:
        """筛选：优胜劣汰"""
        # 按适应度排序，保留前N个
        sorted_pop = sorted(population, key=lambda r: r.fitness_score, reverse=True)
        survivors = sorted_pop[:self.POPULATION_SIZE]

        # 标记淘汰
        for rule in sorted_pop[self.POPULATION_SIZE:]:
            rule.is_active = False
            rule.status = "eliminated"

        return survivors

    async def _update_population(self, survivors: list[RuleIndividual]) -> None:
        """更新种群"""
        for rule in survivors:
            existing = await self.session.get(RuleIndividual, rule.id)
            if not existing:
                self.session.add(rule)

    async def create_rule(self, name: str, dimension: str, rule_expr: dict) -> RuleIndividual:
        """创建新规则个体"""
        rule = RuleIndividual(
            user_id=self.user_id,
            name=name,
            dimension=dimension,
            rule_expr=rule_expr,
            origin="generated",
            generation=1,
        )
        self.session.add(rule)
        await self.session.flush()
        return rule

    async def record_sample(self, rule_id: int, success: bool) -> None:
        """记录规则样本"""
        rule = await self.session.get(RuleIndividual, rule_id)
        if rule and rule.user_id == self.user_id:
            rule.total_samples += 1
            if success:
                rule.success_samples += 1
            # 更新适应度
            if rule.total_samples > 0:
                rule.confidence = rule.success_samples / rule.total_samples
                rule.fitness_score = rule.confidence

    async def get_best_rules(self, limit: int = 5) -> list[RuleIndividual]:
        """获取最优规则"""
        result = await self.session.execute(
            select(RuleIndividual).where(and_(
                RuleIndividual.user_id == self.user_id,
                RuleIndividual.is_active == True,
            )).order_by(RuleIndividual.fitness_score.desc()).limit(limit)
        )
        return list(result.scalars().all())
