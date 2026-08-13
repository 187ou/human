"""消费记账Agent节点"""
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.state import AgentState
from app.utils.llm import get_llm
from app.agents.consume.tools import ConsumeTools


SYSTEM_PROMPT = """你是「消费记账分析助手」，负责帮用户管钱、省钱、避免浪费。

核心能力：
1. 解析消费记录，分类统计
2. 识别冲动消费、无效消费、浪费行为
3. 生成个性化省钱方案
4. 动态调整品类预算

规则：
- 超支预警要明确金额和百分比
- 省钱建议要具体可执行（替代方案、阈值）
- 语气友好，不要指责用户
"""


def consume_node(state: AgentState) -> dict[str, Any]:
    llm = get_llm()
    tools = ConsumeTools(state.get("user_id"), state.get("user_rules", {}))

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=state.get("input", "")),
    ]

    result = llm.invoke(messages)
    return {
        "response": result.content,
        "agent_output": {
            "agent": "consume",
            "action": "analysis",
            "rules_applied": list(state.get("user_rules", {}).get("consume", {}).keys()),
        },
        "need_evolution": True,
    }
