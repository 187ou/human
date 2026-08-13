"""个性化Prompt专属进化：千人千模型"""
from datetime import datetime
from typing import Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.advanced import PersonalPrompt


class PromptEvolver:
    """个性化Prompt进化器

    为每个用户独立进化专属Agent Prompt模板。
    基于用户历史交互反馈，持续优化Prompt。
    """

    # 基础Prompt模板
    BASE_PROMPTS = {
        "time_plan": "你是「时间规划助手」，帮用户规划出行、避免遗漏和延误。",
        "consume": "你是「消费记账助手」，帮用户分析消费、控制预算。",
        "study": "你是「学习督导助手」，帮用户提升学习效率。",
        "travel": "你是「出行处理助手」，帮用户安排出行计划。",
        "item": "你是「物品收纳助手」，帮用户管理物品。",
    }

    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id

    async def get_or_create_prompt(self, agent_type: str) -> PersonalPrompt:
        """获取或创建个性化Prompt"""
        result = await self.session.execute(
            select(PersonalPrompt).where(and_(
                PersonalPrompt.user_id == self.user_id,
                PersonalPrompt.agent_type == agent_type,
                PersonalPrompt.is_active == True,
            ))
        )
        prompt = result.scalar_one_or_none()

        if not prompt:
            # 创建基础Prompt
            base = self.BASE_PROMPTS.get(agent_type, "你是智能生活助手。")
            prompt = PersonalPrompt(
                user_id=self.user_id,
                agent_type=agent_type,
                system_prompt=base,
                version=1,
            )
            self.session.add(prompt)
            await self.session.flush()

        return prompt

    async def evolve_prompt(self, agent_type: str, feedback: dict) -> PersonalPrompt:
        """进化Prompt（基于用户反馈）"""
        current = await self.get_or_create_prompt(agent_type)

        # 根据反馈调整Prompt
        additions = []

        if feedback.get("too_verbose"):
            additions.append("回复简洁直接，不超过3句话。")
        if feedback.get("too_brief"):
            additions.append("回复详细，给出具体建议和原因。")
        if feedback.get("wrong_tone"):
            additions.append(f"语气调整为{feedback.get('preferred_tone', 'friendly')}。")
        if feedback.get("missing_info"):
            additions.append(f"重点关注：{feedback['missing_info']}。")
        if feedback.get("user_style"):
            additions.append(f"用户偏好的沟通风格：{feedback['user_style']}。")

        if additions:
            new_prompt = current.system_prompt + "\n\n用户偏好：\n" + "\n".join(f"- {a}" for a in additions)

            # 创建新版本
            new_version = PersonalPrompt(
                user_id=self.user_id,
                agent_type=agent_type,
                system_prompt=new_prompt,
                version=current.version + 1,
                evolved_from=str(feedback),
                performance_score=0.5,
            )
            current.is_active = False
            self.session.add(new_version)
            await self.session.flush()
            return new_version

        return current

    async def rate_prompt(self, agent_type: str, score: float) -> None:
        """评分Prompt效果"""
        prompt = await self.get_or_create_prompt(agent_type)
        # 移动平均
        prompt.performance_score = prompt.performance_score * 0.7 + score * 0.3

    async def get_all_active_prompts(self) -> dict[str, PersonalPrompt]:
        """获取所有活跃Prompt"""
        result = await self.session.execute(
            select(PersonalPrompt).where(and_(
                PersonalPrompt.user_id == self.user_id,
                PersonalPrompt.is_active == True,
            ))
        )
        prompts = result.scalars().all()
        return {p.agent_type: p for p in prompts}
