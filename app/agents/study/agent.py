"""学习督导Agent节点"""
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.state import AgentState
from app.utils.llm import get_llm


SYSTEM_PROMPT = """你是「个性化学习督导助手」，负责帮用户高效学习、克服拖延。

核心能力：
1. 根据用户状态推荐学习内容和难度
2. 疲惫时降难度，高效时推硬核任务
3. 动态调整学习计划
4. 拖延矫正（拆解、阶梯提醒）

规则：
- 学习建议要具体到内容和时长
- 不要给用户过载的压力
- 鼓励为主，数据为辅
"""


def study_node(state: AgentState) -> dict[str, Any]:
    llm = get_llm()
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=state.get("input", "")),
    ]
    result = llm.invoke(messages)
    return {
        "response": result.content,
        "agent_output": {
            "agent": "study",
            "action": "tutor",
            "rules_applied": list(state.get("user_rules", {}).get("study", {}).keys()),
        },
        "need_evolution": True,
    }
