"""物品收纳Agent节点"""
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.state import AgentState
from app.utils.llm import get_llm


SYSTEM_PROMPT = """你是「物品收纳管理助手」，帮用户管理个人物品、避免东西找不到或过期浪费。

核心能力：
1. 记录物品及其存放位置
2. 过期预警（食品、护肤品、药品、证件、会员卡）
3. 识别闲置物品并建议处理
4. 收纳习惯优化

规则：
- 回复包含具体位置和操作建议
- 过期提醒要提前，给出处理选项
"""


def item_node(state: AgentState) -> dict[str, Any]:
    llm = get_llm()
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=state.get("input", "")),
    ]
    result = llm.invoke(messages)
    return {
        "response": result.content,
        "agent_output": {
            "agent": "item",
            "action": "manage",
            "rules_applied": list(state.get("user_rules", {}).get("item", {}).keys()),
        },
        "need_evolution": True,
    }
