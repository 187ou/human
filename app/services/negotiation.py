"""多智能体冲突自主博弈协商"""
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.innovation import AgentNegotiation


class NegotiationEngine:
    """多智能体博弈协商引擎

    当五大Agent需求冲突时，通过加权投票+折中算法输出最优方案。
    """

    # Agent权重（根据场景动态调整）
    AGENT_WEIGHTS = {
        "study": 0.30,
        "time_plan": 0.25,
        "consume": 0.20,
        "travel": 0.15,
        "item": 0.10,
    }

    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id

    async def negotiate(self, topic: str, proposals: dict[str, dict]) -> dict[str, Any]:
        """
        执行博弈协商

        Args:
            topic: 协商主题
            proposals: {agent_name: {demand, priority, reason}}

        Returns:
            协商结果
        """
        if not proposals:
            return {"success": False, "message": "无提案"}

        rounds = []
        max_rounds = 3

        for round_num in range(1, max_rounds + 1):
            round_result = self._negotiation_round(proposals, round_num)
            rounds.append(round_result)

            # 如果达成共识，提前结束
            if round_result["consensus"]:
                break

        # 生成最终决策
        final = self._generate_decision(proposals, rounds)

        # 记录协商
        negotiation = AgentNegotiation(
            user_id=self.user_id,
            topic=topic,
            conflict_type=final.get("conflict_type", "general"),
            proposals=proposals,
            final_decision=final,
            winner_agent=final.get("winner"),
            compromise_score=final.get("compromise_score", 0),
            rounds=len(rounds),
            negotiation_log=rounds,
        )
        self.session.add(negotiation)
        await self.session.flush()

        return {
            "success": True,
            "negotiation_id": negotiation.id,
            "final_decision": final,
            "rounds": rounds,
        }

    def _negotiation_round(self, proposals: dict, round_num: int) -> dict:
        """单轮协商"""
        # 计算加权得分
        scores = {}
        for agent, proposal in proposals.items():
            weight = self.AGENT_WEIGHTS.get(agent, 0.1)
            priority = proposal.get("priority", 5)
            scores[agent] = weight * priority

        # 排序
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        # 检查是否达成共识（第一名得分远超第二名）
        consensus = False
        if len(ranked) >= 2:
            top_score = ranked[0][1]
            second_score = ranked[1][1]
            if top_score > second_score * 1.5:
                consensus = True

        return {
            "round": round_num,
            "scores": dict(ranked),
            "consensus": consensus,
            "leader": ranked[0][0] if ranked else None,
        }

    def _generate_decision(self, proposals: dict, rounds: list) -> dict:
        """生成最终决策"""
        if not rounds:
            return {}

        final_round = rounds[-1]
        scores = final_round.get("scores", {})

        if not scores:
            return {"winner": None, "compromise_score": 0}

        # 胜出者
        winner = max(scores, key=scores.get)

        # 折中程度（得分差异越小，折中程度越高）
        if len(scores) >= 2:
            sorted_scores = sorted(scores.values(), reverse=True)
            gap = (sorted_scores[0] - sorted_scores[1]) / max(sorted_scores[0], 0.01)
            compromise = max(0, 1 - gap)
        else:
            compromise = 0

        return {
            "winner": winner,
            "winner_proposal": proposals.get(winner, {}),
            "compromise_score": round(compromise, 3),
            "conflict_type": self._detect_conflict_type(proposals),
            "all_scores": scores,
        }

    @staticmethod
    def _detect_conflict_type(proposals: dict) -> str:
        """检测冲突类型"""
        agents = set(proposals.keys())

        if "study" in agents and "travel" in agents:
            return "study_vs_travel"
        elif "study" in agents and "consume" in agents:
            return "study_vs_spending"
        elif "time_plan" in agents and "travel" in agents:
            return "schedule_vs_travel"
        elif len(agents) >= 3:
            return "multi_agent"

        return "general"
