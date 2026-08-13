"""工具调用节点：LangChain Tools 集成"""
import json
from typing import Any

from app.agents.state import AgentState

# 导入所有工具
from app.tools import weather_tool, search_tool, calc_tool, time_tool

# 工具映射表
TOOLS_MAP = {
    "weather": weather_tool,
    "search": search_tool,
    "calc": calc_tool,
    "time": time_tool,
}

# 关键词→工具路由
TOOL_ROUTING = {
    "weather": ["天气", "气温", "下雨", "下雪", "刮风"],
    "search": ["搜索", "查找", "查一下", "搜一下", "查询"],
    "calc": ["计算", "算一下", "等于", "多少加", "多少减", "多少乘", "多少除"],
    "time": ["几点", "现在", "时间", "几天后", "几天前", "今天", "明天", "昨天"],
}


def tools_node(state: AgentState) -> dict[str, Any]:
    """工具调用节点（关键词路由+直接调用）"""
    user_input = state.get("input", "")

    # 1. 关键词路由（无需LLM）
    for tool_name, keywords in TOOL_ROUTING.items():
        for kw in keywords:
            if kw in user_input:
                tool = TOOLS_MAP[tool_name]
                args = _extract_args(tool_name, user_input)
                try:
                    tool_result = tool.invoke(args)
                    return {
                        "response": f"【{tool_name}工具调用结果】\n{tool_result}",
                        "agent_output": {"agent": "tools", "tool": tool_name, "args": args, "result": tool_result},
                        "need_evolution": False,
                    }
                except Exception as e:
                    return {
                        "response": f"工具调用失败: {e}",
                        "agent_output": {"agent": "tools", "error": str(e)},
                        "need_evolution": False,
                    }

    # 2. 无匹配工具，尝试LLM路由
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from app.utils.llm import get_llm

        llm = get_llm()
        messages = [
            SystemMessage(content="你是工具调用助手。可用工具：weather(city)查天气、search(query)搜索、calc(expression)计算、time(query)查时间。如需调用工具，回复JSON：{\"tool\":\"工具名\",\"args\":{\"参数\":\"值\"}}。否则直接回复。"),
            HumanMessage(content=user_input),
        ]
        result = llm.invoke(messages)
        response_text = result.content.strip()

        if response_text.startswith("{"):
            tool_call = json.loads(response_text)
            tool_name = tool_call.get("tool", "")
            tool_args = tool_call.get("args", {})
            if tool_name in TOOLS_MAP:
                tool = TOOLS_MAP[tool_name]
                tool_result = tool.invoke(tool_args)
                return {
                    "response": f"【{tool_name}工具调用结果】\n{tool_result}",
                    "agent_output": {"agent": "tools", "tool": tool_name, "args": tool_args, "result": tool_result},
                    "need_evolution": False,
                }
        return {
            "response": response_text,
            "agent_output": {"agent": "tools", "action": "llm_response"},
            "need_evolution": False,
        }
    except Exception as e:
        return {
            "response": f"抱歉，工具调用暂时不可用（{str(e)[:50]}）。请检查LLM配置。",
            "agent_output": {"agent": "tools", "error": str(e)[:100]},
            "need_evolution": False,
        }


def _extract_args(tool_name: str, user_input: str) -> dict:
    """从用户输入提取工具参数"""
    import re

    if tool_name == "weather":
        # 提取城市名
        match = re.search(r'(.+?)(?:的)?天气', user_input)
        if match:
            return {"city": match.group(1).strip()}
        return {"city": "北京"}  # 默认

    elif tool_name == "calc":
        # 提取表达式
        expr = re.sub(r'[计算算一下等于]', '', user_input).strip()
        return {"expression": expr}

    elif tool_name == "time":
        return {"query": user_input}

    elif tool_name == "search":
        return {"query": user_input}

    return {}

