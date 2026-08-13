"""编排器：路由用户请求到对应子Agent（含工具调用+LangSmith追踪）"""
import re
from typing import Any

from langgraph.graph import StateGraph, END

from app.agents.state import AgentState
from app.agents.time_plan.agent import time_plan_node
from app.agents.consume.agent import consume_node
from app.agents.item.agent import item_node
from app.agents.study.agent import study_node
from app.agents.travel.agent import travel_node
from app.agents.tools_node import tools_node

# 关键词路由表（含工具触发词）
ROUTE_PATTERNS: list[tuple[str, list[str]]] = [
    ("tools", ["天气", "搜索", "计算", "几点", "现在时间", "几天后"]),  # 工具调用优先
    ("time_plan", ["日程", "计划", "时间", "安排", "会议", "提醒", "排班", "碎片", "拖延"]),
    ("consume", ["消费", "记账", "账单", "花钱", "预算", "超支", "省钱", "浪费", "支出", "收入"]),
    ("item", ["物品", "收纳", "东西", "找到", "过期", "闲置", "存放", "位置"]),
    ("study", ["学习", "考研", "刷题", "背诵", "笔记", "课程", "复习", "效率"]),
    ("travel", ["出行", "通勤", "机票", "高铁", "酒店", "路程", "迟到"]),
]


def router_node(state: AgentState) -> dict[str, Any]:
    """根据用户输入路由到子Agent"""
    text = state.get("input", "")
    for agent_name, keywords in ROUTE_PATTERNS:
        if any(kw in text for kw in keywords):
            return {"active_agent": agent_name}
    return {"active_agent": "none"}


def dispatch(state: AgentState) -> str:
    """LangGraph条件边"""
    return state.get("active_agent", "none")


def noop_node(state: AgentState) -> dict[str, Any]:
    """无匹配Agent时的兜底"""
    return {
        "response": "抱歉，我暂时没理解你的需求。你可以告诉我关于日程、消费、物品、学习或出行的问题。",
        "agent_output": {},
    }


def build_orchestrator() -> StateGraph:
    """构建编排图"""
    graph = StateGraph(AgentState)

    graph.add_node("router", router_node)
    graph.add_node("tools", tools_node)  # 工具调用节点
    graph.add_node("time_plan", time_plan_node)
    graph.add_node("consume", consume_node)
    graph.add_node("item", item_node)
    graph.add_node("study", study_node)
    graph.add_node("travel", travel_node)
    graph.add_node("noop", noop_node)

    graph.set_entry_point("router")
    graph.add_conditional_edges(
        "router",
        dispatch,
        {
            "tools": "tools",
            "time_plan": "time_plan",
            "consume": "consume",
            "item": "item",
            "study": "study",
            "travel": "travel",
            "none": "noop",
        },
    )

    for name in ["tools", "time_plan", "consume", "item", "study", "travel", "noop"]:
        graph.add_edge(name, END)

    return graph.compile()


orchestrator_graph = build_orchestrator()
