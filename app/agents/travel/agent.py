"""出行处理Agent节点"""
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.state import AgentState
from app.utils.llm import get_llm


SYSTEM_PROMPT = """你是「出行琐事处理助手」，帮用户规划出行、避免遗漏和延误。

核心能力：
1. 天气与出行影响预判
2. 通勤最优出门时间计算
3. 行程冲突检测
4. 出行全流程提醒（检票、行李、返程）

规则：
- 给出具体时间点（如"建议7:45出门"）
- 天气预警要给出防护和替代方案
"""


def travel_node(state: AgentState) -> dict[str, Any]:
    llm = get_llm()
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=state.get("input", "")),
    ]
    result = llm.invoke(messages)
    return {
        "response": result.content,
        "agent_output": {
            "agent": "travel",
            "action": "plan",
            "rules_applied": list(state.get("user_rules", {}).get("travel", {}).keys()),
        },
        "need_evolution": True,
    }
