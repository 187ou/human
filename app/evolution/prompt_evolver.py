"""Prompt自迭代：根据用户交互反馈优化提示词"""
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.utils.llm import get_llm_with_temp


META_PROMPT = """你是一个Prompt优化专家。给定原始Prompt、用户反馈样本和交互统计数据，输出优化后的Prompt。

优化原则：
1. 保持原意和核心能力不变
2. 根据用户沟通风格调整语气（简洁/详细、严肃/轻松）
3. 根据高频问题补充针对性指令
4. 不要添加与原始目标无关的内容

直接输出优化后的完整Prompt，不要解释。
"""


class PromptEvolver:
    """根据用户反馈演化Prompt"""

    def __init__(self, user_id: int):
        self.user_id = user_id

    async def evolve(
        self,
        original_prompt: str,
        feedback_samples: list[dict[str, Any]],
        interaction_stats: dict[str, Any],
    ) -> str:
        """演化Prompt"""
        llm = get_llm_with_temp(temperature=0.4)

        feedback_text = "\n".join(
            f"- 用户: {f.get('input','')} | 反馈: {f.get('feedback','')}"
            for f in feedback_samples[-20:]
        )

        user_message = f"""原始Prompt:
{original_prompt}

用户沟通风格: {interaction_stats.get('comm_style', 'balanced')}
语气偏好: {interaction_stats.get('tone', 'friendly')}
高频意图: {interaction_stats.get('top_intents', [])}

最近反馈:
{feedback_text}

请输出优化后的Prompt。"""

        messages = [
            SystemMessage(content=META_PROMPT),
            HumanMessage(content=user_message),
        ]

        result = llm.invoke(messages)
        return result.content.strip()
