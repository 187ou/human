"""Agent共享状态定义"""
from typing import Annotated, Any
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class AgentState(dict):
    """全局Agent状态"""
    # 当前用户ID
    user_id: int
    # 用户输入
    input: str
    # 选中的子Agent
    active_agent: str  # time_plan / consume / item / study / travel / none
    # 子Agent输出
    agent_output: dict[str, Any]
    # 消息历史
    messages: Annotated[list[BaseMessage], add_messages]
    # 演化层注入的用户规则
    user_rules: dict[str, Any]
    # 是否需要演化层介入
    need_evolution: bool
    # 最终回复
    response: str
