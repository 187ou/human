"""生活行为因果DAG图构建引擎

基于DoWhy因果推断框架原理，构建用户生活有向无环因果图。
区分相关性与因果性，挖掘深层因果链路。
"""
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mining import CausalDAGNode, CausalDAGEdge
from app.models.behavior import BehaviorLog


class CausalDAGBuilder:
    """因果DAG构建器

    核心方法：
    1. 节点发现：从行为日志提取因果变量节点
    2. 边发现：基于时间优先性+共变分析发现因果方向
    3. 环检测：确保DAG无环
    4. 因果效应估计：量化因果强度
    """

    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id

    async def build_dag(self) -> dict[str, Any]:
        """构建完整因果DAG"""
        # 获取行为数据
        logs = await self._get_behavior_data()
        if len(logs) < 20:
            return {"status": "insufficient_data", "nodes": 0, "edges": 0}

        # 1. 创建节点
        nodes = await self._create_nodes(logs)

        # 2. 发现因果边
        edges = await self._discover_edges(logs, nodes)

        # 3. 检测并打破环
        edges = self._break_cycles(edges)

        # 4. 持久化
        await self._persist_dag(nodes, edges)

        await self.session.commit()
        return {
            "status": "success",
            "nodes": len(nodes),
            "edges": len(edges),
            "causal_paths": self._extract_causal_paths(edges),
        }

    async def _get_behavior_data(self) -> list[BehaviorLog]:
        """获取行为数据"""
        cutoff = datetime.utcnow() - timedelta(days=60)
        result = await self.session.execute(
            select(BehaviorLog).where(and_(
                BehaviorLog.user_id == self.user_id,
                BehaviorLog.created_at >= cutoff,
            )).order_by(BehaviorLog.created_at)
        )
        return result.scalars().all()

    async def _create_nodes(self, logs: list[BehaviorLog]) -> list[CausalDAGNode]:
        """创建因果节点"""
        node_data = {
            "sleep_duration": [],
            "energy_level": [],
            "task_completion": [],
            "task_delay": [],
            "study_accuracy": [],
            "consume_impulse": [],
            "focus_minutes": [],
        }

        # 按天聚合
        daily = defaultdict(dict)
        for log in logs:
            day = log.created_at.strftime('%Y-%m-%d')
            if log.dimension == "time":
                daily[day]["task_completion"] = 1.0 if log.schedule_completed else 0.0
                daily[day]["task_delay"] = 1.0 if log.schedule_is_delayed else 0.0
            elif log.dimension == "study" and log.study_accuracy is not None:
                daily[day]["study_accuracy"] = log.study_accuracy
                daily[day]["focus_minutes"] = log.study_focus_min or 0
            elif log.dimension == "consume":
                daily[day]["consume_impulse"] = 1.0 if log.consume_is_impulse else 0.0

        # 获取用户睡眠数据
        from app.models.user import User
        user = await self.session.get(User, self.user_id)
        if user and user.sleep_hour and user.wake_hour:
            sleep = user.sleep_hour - user.wake_hour if user.sleep_hour > user.wake_hour else (24 - user.wake_hour) + user.sleep_hour
            for day in daily:
                daily[day]["sleep_duration"] = sleep
                # 精力值基于睡眠估算
                daily[day]["energy_level"] = min(100, sleep * 12)

        # 创建节点
        nodes = []
        for node_name, values in node_data.items():
            vals = [daily[d].get(node_name, 0) for d in daily if daily[d].get(node_name) is not None]
            if vals:
                node = CausalDAGNode(
                    user_id=self.user_id,
                    node_name=node_name,
                    node_type=self._classify_node_type(node_name),
                    description=self._node_description(node_name),
                    mean_value=sum(vals) / len(vals),
                    std_value=self._std(vals),
                    sample_count=len(vals),
                )
                self.session.add(node)
                nodes.append(node)

        await self.session.flush()
        return nodes

    async def _discover_edges(self, logs: list[BehaviorLog], nodes: list[CausalDAGNode]) -> list[dict]:
        """发现因果边"""
        edges = []
        node_names = [n.node_name for n in nodes]

        # 预定义因果假设（基于领域知识）
        causal_hypotheses = [
            ("sleep_duration", "energy_level"),
            ("energy_level", "task_completion"),
            ("energy_level", "study_accuracy"),
            ("energy_level", "focus_minutes"),
            ("task_delay", "energy_level"),
            ("consume_impulse", "energy_level"),
            ("focus_minutes", "study_accuracy"),
        ]

        for cause, effect in causal_hypotheses:
            if cause in node_names and effect in node_names:
                strength = self._estimate_causal_strength(logs, cause, effect)
                if strength > 0.2:
                    edges.append({
                        "cause": cause,
                        "effect": effect,
                        "strength": round(strength, 3),
                        "confidence": min(0.9, strength * 1.2),
                    })

        return edges

    def _estimate_causal_strength(self, logs: list[BehaviorLog], cause: str, effect: str) -> float:
        """估计因果强度（基于时间滞后相关）"""
        # 简化版：计算当日cause与次日effect的相关系数
        daily = defaultdict(dict)
        for log in logs:
            day = log.created_at.strftime('%Y-%m-%d')
            self._extract_metric(log, day, daily)

        days = sorted(daily.keys())
        cause_vals = []
        effect_vals_lagged = []

        for i in range(len(days) - 1):
            c_val = daily[days[i]].get(cause)
            e_val = daily[days[i + 1]].get(effect)
            if c_val is not None and e_val is not None:
                cause_vals.append(c_val)
                effect_vals_lagged.append(e_val)

        if len(cause_vals) < 3:
            return 0.0

        return abs(self._correlation(cause_vals, effect_vals_lagged))

    def _extract_metric(self, log: BehaviorLog, day: str, daily: dict):
        """提取指标"""
        if log.dimension == "time":
            daily[day]["task_completion"] = 1.0 if log.schedule_completed else 0.0
            daily[day]["task_delay"] = 1.0 if log.schedule_is_delayed else 0.0
        elif log.dimension == "study" and log.study_accuracy is not None:
            daily[day]["study_accuracy"] = log.study_accuracy
            daily[day]["focus_minutes"] = log.study_focus_min or 0
        elif log.dimension == "consume":
            daily[day]["consume_impulse"] = 1.0 if log.consume_is_impulse else 0.0

    def _break_cycles(self, edges: list[dict]) -> list[dict]:
        """检测并打破环"""
        # 构建邻接表
        adj = defaultdict(list)
        for e in edges:
            adj[e["cause"]].append(e["effect"])

        # DFS检测环
        visited = set()
        rec_stack = set()

        def has_cycle(node):
            visited.add(node)
            rec_stack.add(node)
            for neighbor in adj.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.remove(node)
            return False

        # 移除最弱的边打破环
        for edge in sorted(edges, key=lambda e: e["strength"]):
            adj[edge["cause"]].remove(edge["effect"])
            visited.clear()
            rec_stack.clear()
            has_cycle_flag = False
            for node in adj:
                if node not in visited:
                    if has_cycle(node):
                        has_cycle_flag = True
                        break
            if has_cycle_flag:
                adj[edge["cause"]].append(edge["effect"])  # 恢复
            else:
                edges.remove(edge)  # 移除该边

        return edges

    async def _persist_dag(self, nodes: list[CausalDAGNode], edges: list[dict]):
        """持久化DAG"""
        for edge in edges:
            dag_edge = CausalDAGEdge(
                user_id=self.user_id,
                cause_node=edge["cause"],
                effect_node=edge["effect"],
                causal_strength=edge["strength"],
                confidence=edge["confidence"],
                path_description=f"{edge['cause']} → {edge['effect']}",
            )
            self.session.add(dag_edge)

    def _extract_causal_paths(self, edges: list[dict]) -> list[str]:
        """提取因果路径"""
        return [f"{e['cause']} → {e['effect']} (强度{e['strength']:.2f})" for e in edges]

    @staticmethod
    def _classify_node_type(name: str) -> str:
        types = {
            "sleep_duration": "sleep", "energy_level": "energy",
            "task_completion": "task", "task_delay": "task",
            "study_accuracy": "study", "consume_impulse": "consume",
            "focus_minutes": "study",
        }
        return types.get(name, "other")

    @staticmethod
    def _node_description(name: str) -> str:
        descs = {
            "sleep_duration": "睡眠时长",
            "energy_level": "精力水平",
            "task_completion": "任务完成率",
            "task_delay": "任务拖延率",
            "study_accuracy": "学习正确率",
            "consume_impulse": "冲动消费倾向",
            "focus_minutes": "专注时长",
        }
        return descs.get(name, name)

    @staticmethod
    def _std(values: list[float]) -> float:
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        return (sum((v - mean) ** 2 for v in values) / len(values)) ** 0.5

    @staticmethod
    def _correlation(x: list[float], y: list[float]) -> float:
        n = len(x)
        if n < 2:
            return 0.0
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        num = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
        dx = sum((xi - mean_x) ** 2 for xi in x) ** 0.5
        dy = sum((yi - mean_y) ** 2 for yi in y) ** 0.5
        if dx == 0 or dy == 0:
            return 0.0
        return num / (dx * dy)
