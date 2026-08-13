"""时间规划Agent节点"""
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.state import AgentState
from app.utils.llm import get_llm
from app.agents.time_plan.tools import TimePlanTools


SYSTEM_PROMPT = """你是「智能时间规划助手」，负责帮用户管理日程、优化时间利用。

核心能力：
1. 解析自然语言日程，提取时间、地点、事项
2. 挖掘碎片时间并填充轻量任务
3. 检测冲突、过载、不合理计划并给出修正建议
4. 针对拖延习惯提供拆解和阶梯提醒

规则：
- 回复简洁，直接给出可执行方案
- 如果识别到多个日程冲突，按优先级排序
- 碎片时间建议不超过30分钟
"""


def time_plan_node(state: AgentState) -> dict[str, Any]:
    """时间规划Agent执行节点"""
    llm = get_llm()
    tools = TimePlanTools(state.get("user_id"), state.get("user_rules", {}))

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=state.get("input", "")),
    ]

    # 调用LLM
    result = llm.invoke(messages)
    response_text = result.content

    return {
        "response": response_text,
        "agent_output": {
            "agent": "time_plan",
            "action": "advice",
            "rules_applied": list(state.get("user_rules", {}).get("time", {}).keys()),
        },
        "need_evolution": True,
    }
