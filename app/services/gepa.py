"""GEPA遗传帕累托Prompt专属进化引擎

ICLR2026 GEPA算法实现：
1. 基于用户轨迹生成多条Prompt变体
2. 多目标帕累托评分：完成率、简洁度、共情适配、准确率
3. 遗传操作：交叉、变异、选择
4. 为每位用户生成独一无二的专属系统Prompt
"""
import random
from datetime import datetime
from typing import Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gepa import PromptVariant, PromptEvolutionRecord


class GEPAEvolver:
    """GEPA帕累托Prompt进化器"""

    # 帕累托权重
    WEIGHTS = {
        "completion": 0.35,
        "conciseness": 0.20,
        "empathy": 0.25,
        "accuracy": 0.20,
    }

    # GA参数
    POPULATION_SIZE = 8
    CROSSOVER_RATE = 0.4
    MUTATION_RATE = 0.2
    ELITE_RATIO = 0.25

    # 基础Prompt模板
    BASE_PROMPTS = {
        "time_plan": "你是「时间规划助手」，帮用户规划日程、避免遗漏和延误。给出具体时间建议和冲突检测。",
        "consume": "你是「消费记账助手」，帮用户分析消费、控制预算。识别冲动消费，给出省钱建议。",
        "study": "你是「学习督导助手」，帮用户提升学习效率。根据精力状态调整任务难度。",
        "travel": "你是「出行处理助手」，帮用户安排出行计划。关注天气影响和行程冲突。",
        "item": "你是「物品收纳助手」，帮用户管理物品。提醒过期，识别闲置。",
    }

    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id

    async def evolve(self, agent_type: str, user_trajectory: dict | None = None) -> dict[str, Any]:
        """执行GEPA进化"""
        # 1. 初始化种群
        population = await self._initialize_population(agent_type)

        # 2. 评估适应度
        evaluated = await self._evaluate_population(population, user_trajectory)

        # 3. 帕累托排序
        pareto_front = self._pareto_sort(evaluated)

        # 4. 遗传操作
        offspring = self._genetic_operations(pareto_front, agent_type)

        # 5. 选择下一代
        next_gen = self._selection(pareto_front + offspring)

        # 6. 更新种群
        await self._update_population(next_gen)

        # 7. 记录进化
        best = next_gen[0] if next_gen else None
        record = PromptEvolutionRecord(
            user_id=self.user_id,
            agent_type=agent_type,
            generation=max(p.generation for p in next_gen) if next_gen else 1,
            population_size=len(next_gen),
            pareto_front_size=len(pareto_front),
            best_variant_id=best.id if best else None,
            best_fitness=best.fitness_score if best else 0,
        )
        self.session.add(record)
        await self.session.flush()

        return {
            "agent_type": agent_type,
            "generation": record.generation,
            "population_size": len(next_gen),
            "pareto_front": len(pareto_front),
            "best_fitness": round(best.fitness_score, 3) if best else 0,
            "best_prompt": best.prompt_content[:100] + "..." if best else "",
        }

    async def _initialize_population(self, agent_type: str) -> list[PromptVariant]:
        """初始化种群"""
        base = self.BASE_PROMPTS.get(agent_type, "你是智能生活助手。")

        # 获取现有活跃变体
        result = await self.session.execute(
            select(PromptVariant).where(and_(
                PromptVariant.user_id == self.user_id,
                PromptVariant.agent_type == agent_type,
                PromptVariant.is_active == True,
            )).order_by(PromptVariant.fitness_score.desc()).limit(self.POPULATION_SIZE)
        )
        existing = result.scalars().all()

        if len(existing) >= self.POPULATION_SIZE // 2:
            return list(existing)

        # 生成新变体
        variants = list(existing)
        strategies = [
            ("简洁版", self._make_concise(base)),
            ("详细版", self._make_detailed(base)),
            ("共情版", self._make_empathetic(base)),
            ("专业版", self._make_professional(base)),
            ("幽默版", self._make_humorous(base)),
            ("直接版", self._make_direct(base)),
            ("温和版", self._make_gentle(base)),
            ("激励版", self._make_motivating(base)),
        ]

        for name, content in strategies:
            if len(variants) >= self.POPULATION_SIZE:
                break
            variant = PromptVariant(
                user_id=self.user_id,
                agent_type=agent_type,
                prompt_content=content,
                origin="generated",
                generation=1,
            )
            self.session.add(variant)
            variants.append(variant)

        await self.session.flush()
        return variants

    async def _evaluate_population(self, population: list[PromptVariant],
                                    trajectory: dict | None = None) -> list[PromptVariant]:
        """评估种群（帕累托多目标）"""
        for variant in population:
            # 模拟评分（实际项目中基于用户轨迹数据计算）
            variant.completion_score = self._score_completion(variant, trajectory)
            variant.conciseness_score = self._score_conciseness(variant)
            variant.empathy_score = self._score_empathy(variant)
            variant.accuracy_score = self._score_accuracy(variant)

            # 综合适应度
            variant.fitness_score = (
                variant.completion_score * self.WEIGHTS["completion"] +
                variant.conciseness_score * self.WEIGHTS["conciseness"] +
                variant.empathy_score * self.WEIGHTS["empathy"] +
                variant.accuracy_score * self.WEIGHTS["accuracy"]
            )

        return population

    def _pareto_sort(self, population: list[PromptVariant]) -> list[PromptVariant]:
        """帕累托排序"""
        # 标记被支配个体
        for i, p in enumerate(population):
            p.is_dominated = False
            p.pareto_rank = 0
            for j, q in enumerate(population):
                if i != j and self._dominates(q, p):
                    p.is_dominated = True
                    break

        # 提取帕累托前沿
        front = [p for p in population if not p.is_dominated]
        front.sort(key=lambda p: p.fitness_score or 0, reverse=True)
        return front

    @staticmethod
    def _dominates(a: PromptVariant, b: PromptVariant) -> bool:
        """a是否帕累托支配b"""
        better_in_any = False
        objectives = [
            (a.completion_score or 0, b.completion_score or 0),
            (a.conciseness_score or 0, b.conciseness_score or 0),
            (a.empathy_score or 0, b.empathy_score or 0),
            (a.accuracy_score or 0, b.accuracy_score or 0),
        ]
        for a_val, b_val in objectives:
            if a_val < b_val:
                return False
            if a_val > b_val:
                better_in_any = True
        return better_in_any

    def _genetic_operations(self, pareto_front: list[PromptVariant],
                             agent_type: str) -> list[PromptVariant]:
        """遗传操作"""
        offspring = []

        # 交叉
        for i in range(0, len(pareto_front) - 1, 2):
            if random.random() < self.CROSSOVER_RATE:
                child = self._crossover(pareto_front[i], pareto_front[i + 1], agent_type)
                offspring.append(child)

        # 变异
        for parent in pareto_front:
            if random.random() < self.MUTATION_RATE:
                child = self._mutate(parent, agent_type)
                offspring.append(child)

        return offspring

    def _crossover(self, p1: PromptVariant, p2: PromptVariant, agent_type: str) -> PromptVariant:
        """交叉：合并两个Prompt"""
        sentences1 = p1.prompt_content.split("。")
        sentences2 = p2.prompt_content.split("。")

        # 交替选取句子
        child_sentences = []
        for s1, s2 in zip(sentences1, sentences2):
            child_sentences.append(random.choice([s1, s2]))
        if len(sentences1) > len(sentences2):
            child_sentences.extend(sentences1[len(sentences2):])
        elif len(sentences2) > len(sentences1):
            child_sentences.extend(sentences2[len(sentences1):])

        child_content = "。".join(filter(None, child_sentences))
        if not child_content.endswith("。"):
            child_content += "。"

        return PromptVariant(
            user_id=self.user_id,
            agent_type=agent_type,
            prompt_content=child_content,
            origin="crossover",
            parent_ids=[p1.id, p2.id],
            generation=max(p1.generation, p2.generation) + 1,
        )

    def _mutate(self, parent: PromptVariant, agent_type: str) -> PromptVariant:
        """变异：小幅修改Prompt"""
        mutations = [
            lambda p: p.replace("帮用户", "协助用户"),
            lambda p: p.replace("建议", "推荐"),
            lambda p: p + "回复简洁直接。",
            lambda p: p + "体现共情理解。",
            lambda p: p.replace("。", "，"),
        ]

        mutation = random.choice(mutations)
        try:
            mutated_content = mutation(parent.prompt_content)
        except Exception:
            mutated_content = parent.prompt_content

        return PromptVariant(
            user_id=self.user_id,
            agent_type=agent_type,
            prompt_content=mutated_content,
            origin="mutation",
            parent_ids=[parent.id],
            generation=parent.generation + 1,
        )

    def _selection(self, candidates: list[PromptVariant]) -> list[PromptVariant]:
        """选择下一代"""
        # 按适应度排序，保留精英
        sorted_candidates = sorted(candidates, key=lambda p: p.fitness_score, reverse=True)
        elite_count = max(1, int(len(sorted_candidates) * self.ELITE_RATIO))
        return sorted_candidates[:max(elite_count, self.POPULATION_SIZE // 2)]

    async def _update_population(self, next_gen: list[PromptVariant]) -> None:
        """更新种群"""
        # 停用旧变体
        existing = await self.session.execute(
            select(PromptVariant).where(and_(
                PromptVariant.user_id == self.user_id,
                PromptVariant.is_active == True,
            ))
        )
        for variant in existing.scalars().all():
            variant.is_active = False

        # 激活新一代
        for variant in next_gen:
            variant.is_active = True

    # ==================== Prompt变体生成 ====================

    @staticmethod
    def _make_concise(base: str) -> str:
        return base + "回复简洁，不超过3句话。"

    @staticmethod
    def _make_detailed(base: str) -> str:
        return base + "回复详细，给出具体步骤、原因分析和替代方案。"

    @staticmethod
    def _make_empathetic(base: str) -> str:
        return base + "体现共情，先理解用户处境，再给出建议。语气温和。"

    @staticmethod
    def _make_professional(base: str) -> str:
        return base + "使用专业术语，给出数据支撑的分析。语气严谨。"

    @staticmethod
    def _make_humorous(base: str) -> str:
        return base + "语气轻松幽默，适当使用比喻和例子。让建议更容易接受。"

    @staticmethod
    def _make_direct(base: str) -> str:
        return base + "直接给出结论，不废话。先说结果，再说原因。"

    @staticmethod
    def _make_gentle(base: str) -> str:
        return base + "语气温和，多用'可以试试''不妨考虑'等建议性表达。"

    @staticmethod
    def _make_motivating(base: str) -> str:
        return base + "积极正面，多鼓励用户。肯定进步，激发行动力。"

    # ==================== 评分方法 ====================

    @staticmethod
    def _score_completion(variant: PromptVariant, trajectory: dict | None) -> float:
        """完成率评分"""
        if trajectory:
            return trajectory.get("completion_rate", random.uniform(0.5, 0.9))
        return random.uniform(0.5, 0.9)

    @staticmethod
    def _score_conciseness(variant: PromptVariant) -> float:
        """简洁度评分（越短越高）"""
        length = len(variant.prompt_content)
        if length < 50:
            return 0.9
        elif length < 100:
            return 0.7
        elif length < 150:
            return 0.5
        return 0.3

    @staticmethod
    def _score_empathy(variant: PromptVariant) -> float:
        """共情评分"""
        empathy_words = ["共情", "理解", "温和", "鼓励", "肯定", "建议"]
        count = sum(1 for w in empathy_words if w in variant.prompt_content)
        return min(0.9, 0.3 + count * 0.15)

    @staticmethod
    def _score_accuracy(variant: PromptVariant) -> float:
        """准确率评分"""
        return random.uniform(0.6, 0.95)

    async def get_best_prompt(self, agent_type: str) -> str | None:
        """获取最优Prompt"""
        result = await self.session.execute(
            select(PromptVariant).where(and_(
                PromptVariant.user_id == self.user_id,
                PromptVariant.agent_type == agent_type,
                PromptVariant.is_active == True,
            )).order_by(PromptVariant.fitness_score.desc()).limit(1)
        )
        best = result.scalar_one_or_none()
        return best.prompt_content if best else self.BASE_PROMPTS.get(agent_type)
