"""可复用生活技能自动封装蒸馏（SkillCraft范式）

将重复多步骤任务链路自动封装为可复用技能函数。
高频场景：月度消费复盘、短途出行打包、考前学习规划。
"""
from datetime import datetime
from typing import Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import LifeSkill


class SkillCraft:
    """技能封装蒸馏器"""

    # 技能模板
    SKILL_TEMPLATES = {
        "consume_review": {
            "name": "月度消费复盘",
            "description": "自动生成月度消费报告，分析支出结构，给出省钱建议",
            "steps": [
                {"action": "fetch_consume_data", "params": {"period": "month"}},
                {"action": "categorize_spending", "params": {}},
                {"action": "identify_waste", "params": {}},
                {"action": "generate_suggestions", "params": {}},
            ],
        },
        "travel_pack": {
            "name": "短途出行打包",
            "description": "根据目的地、天数、天气自动生成行李清单",
            "steps": [
                {"action": "check_weather", "params": {"destination": "target"}},
                {"action": "generate_packing_list", "params": {"days": "duration"}},
                {"action": "reserve_budget", "params": {"category": "travel"}},
            ],
        },
        "study_plan": {
            "name": "考前学习规划",
            "description": "根据考试日期和科目自动生成学习计划",
            "steps": [
                {"action": "assess_current_level", "params": {}},
                {"action": "calculate_available_time", "params": {"exam_date": "target"}},
                {"action": "distribute_tasks", "params": {"subjects": "targets"}},
                {"action": "set_milestones", "params": {}},
            ],
        },
    }

    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id

    async def get_or_create_skill(self, skill_type: str) -> LifeSkill:
        """获取或创建技能"""
        result = await self.session.execute(
            select(LifeSkill).where(and_(
                LifeSkill.user_id == self.user_id,
                LifeSkill.skill_type == skill_type,
                LifeSkill.is_active == True,
            ))
        )
        skill = result.scalar_one_or_none()

        if not skill:
            template = self.SKILL_TEMPLATES.get(skill_type)
            if template:
                skill = LifeSkill(
                    user_id=self.user_id,
                    name=template["name"],
                    description=template["description"],
                    skill_type=skill_type,
                    steps=template["steps"],
                    source="auto",
                )
                self.session.add(skill)
                await self.session.flush()

        return skill

    async def invoke_skill(self, skill_type: str, params: dict) -> dict[str, Any]:
        """调用技能"""
        skill = await self.get_or_create_skill(skill_type)
        if not skill:
            return {"success": False, "message": "技能不存在"}

        # 更新使用统计
        skill.use_count += 1
        await self.session.flush()

        return {
            "success": True,
            "skill_name": skill.name,
            "steps": skill.steps,
            "use_count": skill.use_count,
            "estimated_duration": skill.avg_duration_min,
        }

    async def learn_from_execution(self, skill_type: str, execution_result: dict) -> None:
        """从执行结果学习，优化技能"""
        skill = await self.get_or_create_skill(skill_type)
        if not skill:
            return

        # 更新成功率
        if execution_result.get("success"):
            total = skill.success_rate * skill.use_count
            skill.success_rate = (total + 1) / (skill.use_count + 1)
        else:
            total = skill.success_rate * skill.use_count
            skill.success_rate = total / (skill.use_count + 1)

        # 更新平均耗时
        if "duration_min" in execution_result:
            total_time = skill.avg_duration_min * skill.use_count
            skill.avg_duration_min = (total_time + execution_result["duration_min"]) / (skill.use_count + 1)

        await self.session.flush()

    async def get_all_skills(self) -> list[LifeSkill]:
        """获取所有技能"""
        result = await self.session.execute(
            select(LifeSkill).where(and_(
                LifeSkill.user_id == self.user_id,
                LifeSkill.is_active == True,
            )).order_by(LifeSkill.use_count.desc())
        )
        return list(result.scalars().all())
