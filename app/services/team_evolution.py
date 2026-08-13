"""多Agent协同共进化引擎（Meta-Team三层）

三层协同：
1. 个体层：每个Agent复盘自身、优化内部Prompt
2. 交互层：优化Agent间通信协议、联动触发条件
3. 团队全局层：统一调度四维资源分配策略
"""
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.team import AgentPerformance, InteractionProtocol


class TeamEvolution:
    """多Agent协同共进化引擎"""

    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id

    async def evolve_all_layers(self) -> dict[str, Any]:
        """执行三层协同进化"""
        # 第1层：个体层进化
        individual = await self._evolve_individual_layer()

        # 第2层：交互层进化
        interaction = await self._evolve_interaction_layer()

        # 第3层：团队全局层进化
        global_layer = await self._evolve_global_layer()

        await self.session.commit()
        return {
            "individual": individual,
            "interaction": interaction,
            "global": global_layer,
        }

    async def _evolve_individual_layer(self) -> dict[str, Any]:
        """第1层：个体层进化"""
        agents = ["time_plan", "consume", "study", "travel", "item"]
        results = {}

        for agent_name in agents:
            perf = await self._get_or_create_performance(agent_name)

            # 计算成功率
            if perf.total_tasks > 0:
                success_rate = perf.success_tasks / perf.total_tasks
            else:
                success_rate = 0.5

            # 如果成功率低，标记需要优化
            if success_rate < 0.5 and perf.total_tasks >= 3:
                perf.optimization_notes = f"成功率{success_rate:.0%}过低，需要优化Prompt"
                perf.last_optimized_at = datetime.utcnow()
                results[agent_name] = {"action": "needs_optimization", "success_rate": round(success_rate, 2)}
            else:
                results[agent_name] = {"action": "stable", "success_rate": round(success_rate, 2)}

        return {"agents": results}

    async def _evolve_interaction_layer(self) -> dict[str, Any]:
        """第2层：交互层进化"""
        # 检查现有交互协议
        protocols = await self.session.execute(
            select(InteractionProtocol).where(and_(
                InteractionProtocol.user_id == self.user_id,
                InteractionProtocol.is_active == True,
            ))
        )
        existing = protocols.scalars().all()

        # 优化低效协议
        optimized = 0
        for protocol in existing:
            total = protocol.success_count + protocol.fail_count
            if total > 0:
                success_rate = protocol.success_count / total
                if success_rate < 0.3:
                    # 协议效率低，需要调整
                    protocol.is_active = False
                    optimized += 1

        return {"protocols_checked": len(existing), "optimized": optimized}

    async def _evolve_global_layer(self) -> dict[str, Any]:
        """第3层：团队全局层进化"""
        # 分析各Agent资源占用
        perfs = await self.session.execute(
            select(AgentPerformance).where(AgentPerformance.user_id == self.user_id)
        )
        all_perfs = perfs.scalars().all()

        if not all_perfs:
            return {"status": "no_data"}

        # 计算资源分配建议
        total_tasks = sum(p.total_tasks for p in all_perfs)
        if total_tasks == 0:
            return {"status": "no_tasks"}

        allocation = {}
        for perf in all_perfs:
            share = perf.total_tasks / total_tasks
            allocation[perf.agent_name] = round(share, 3)

        return {"resource_allocation": allocation, "total_tasks": total_tasks}

    async def _get_or_create_performance(self, agent_name: str) -> AgentPerformance:
        """获取或创建Agent表现记录"""
        result = await self.session.execute(
            select(AgentPerformance).where(and_(
                AgentPerformance.user_id == self.user_id,
                AgentPerformance.agent_name == agent_name,
            ))
        )
        perf = result.scalar_one_or_none()

        if not perf:
            perf = AgentPerformance(
                user_id=self.user_id,
                agent_name=agent_name,
            )
            self.session.add(perf)
            await self.session.flush()

        return perf

    async def record_agent_task(self, agent_name: str, success: bool, quality: float = 0.5) -> None:
        """记录Agent任务执行"""
        perf = await self._get_or_create_performance(agent_name)
        perf.total_tasks += 1
        if success:
            perf.success_tasks += 1
        # 移动平均更新质量分
        perf.avg_quality = perf.avg_quality * 0.8 + quality * 0.2
