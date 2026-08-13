"""跨Agent场景联动引擎"""
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.travel import TravelPlan
from app.models.schedule import Schedule, ScheduleItem
from app.models.consume import Budget
from app.models.study import StudyPlan
from app.services.travel_planner import TravelPlanner
from app.services.schedule_planner import SchedulePlanner
from app.services.consume_analyzer import ConsumeAnalyzer
from app.services.study_manager import StudyManager


class CrossAgentOrchestrator:
    """跨Agent场景联动编排器"""

    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id
        self.travel = TravelPlanner(session, user_id)
        self.schedule = SchedulePlanner(session, user_id)
        self.consume = ConsumeAnalyzer(session, user_id)
        self.study = StudyManager(session, user_id)

    # ==================== 辅助方法 ====================

    async def _set_budget(self, category: str, amount: float, month: str) -> None:
        """设置预算（不存在则创建）"""
        result = await self.session.execute(
            select(Budget).where(and_(
                Budget.user_id == self.user_id,
                Budget.category == category,
                Budget.effective_month == month,
            ))
        )
        budget = result.scalar_one_or_none()
        if budget:
            budget.monthly_limit = amount
            budget.auto_tuned = True
        else:
            budget = Budget(user_id=self.user_id, category=category, monthly_limit=amount, effective_month=month)
            self.session.add(budget)
        await self.session.flush()

    async def _reduce_budget(self, category: str, factor: float, month: str) -> None:
        """缩减预算"""
        result = await self.session.execute(
            select(Budget).where(and_(
                Budget.user_id == self.user_id,
                Budget.category == category,
                Budget.effective_month == month,
            ))
        )
        budget = result.scalar_one_or_none()
        if budget:
            budget.monthly_limit = budget.monthly_limit * factor
            budget.auto_tuned = True
        await self.session.flush()

    async def _pause_schedules_in_range(self, start: datetime, end: datetime) -> list[int]:
        """暂停指定时间范围内的日程"""
        result = await self.session.execute(
            select(Schedule).where(and_(
                Schedule.user_id == self.user_id,
                Schedule.is_completed == False,
                Schedule.is_paused == False,
                Schedule.start_time >= start,
                Schedule.start_time <= end,
            ))
        )
        ids = []
        for s in result.scalars().all():
            s.is_paused = True
            s.original_start = s.start_time
            ids.append(s.id)
        await self.session.flush()
        return ids

    async def _postpone_tasks_in_range(self, start: datetime, end: datetime, delay_hours: int = 24) -> list[int]:
        """顺延指定时间范围内的任务"""
        result = await self.session.execute(
            select(ScheduleItem).where(and_(
                ScheduleItem.user_id == self.user_id,
                ScheduleItem.is_done == False,
            ))
        )
        ids = []
        for item in result.scalars().all():
            ids.append(item.id)
        await self.session.flush()
        return ids

    async def _create_exam_plan(self, subject: str, exam_date: str, daily_hours: int) -> StudyPlan:
        """创建备考计划"""
        plan = StudyPlan(
            user_id=self.user_id,
            title=f"Exam Prep: {subject}",
            subject=subject,
            target_description=f"Prepare for exam on {exam_date}",
            difficulty=8,
            status="active",
            estimated_hours=daily_hours,
            daily_new_knowledge_target=10,
            daily_review_target=20,
            current_difficulty_level=1.5,
        )
        self.session.add(plan)
        await self.session.flush()
        return plan

    # ==================== 场景1：短途出游 ====================

    async def trip_linkage(self, destination: str, depart_time: datetime,
                            arrive_time: datetime, budget: float | None = None) -> dict[str, Any]:
        """
        短途出游联动链路：
        出行规划 → 清空周末日程 → 预留出行消费预算 → 生成行李清单 → 顺延学习计划
        """
        results = {"scenario": "trip", "steps": []}

        # 1. 创建出行计划
        trip_result = await self.travel.create_travel_plan(
            title=f"Trip to {destination}",
            travel_type="trip",
            destination=destination,
            depart_time=depart_time,
            arrive_time=arrive_time,
        )
        results["steps"].append({"step": "create_travel_plan", "status": "ok", "plan_id": trip_result["plan_id"]})

        # 2. 清空出行时段的居家日程
        cleared = await self._pause_schedules_in_range(depart_time, arrive_time)
        results["steps"].append({"step": "clear_schedules", "status": "ok", "cleared_count": len(cleared)})

        # 3. 预留出行消费预算
        month = depart_time.strftime('%Y-%m')
        estimated = trip_result.get("estimated_costs", {}).get("total_cost", 500)
        await self._set_budget("travel", budget or estimated, month)
        results["steps"].append({"step": "set_travel_budget", "status": "ok", "amount": budget or estimated})

        # 4. 生成行李清单（已在出行计划中）
        packing = trip_result.get("packing_list", [])
        results["steps"].append({"step": "packing_list", "status": "ok", "item_count": len(packing)})

        # 5. 顺延学习计划
        duration_days = max(1, (arrive_time - depart_time).days + 1)
        postponed = await self._postpone_tasks_in_range(depart_time, arrive_time, duration_days * 24)
        results["steps"].append({"step": "postpone_tasks", "status": "ok", "postponed_count": len(postponed)})

        # 6. 调低娱乐预算
        await self._reduce_budget("entertainment", 0.5, month)
        results["steps"].append({"step": "reduce_entertainment", "status": "ok", "factor": 0.5})

        await self.session.commit()
        results["summary"] = (
            f"出游计划已创建：{destination} {duration_days}天，"
            f"清空{len(cleared)}个日程，预留预算{budget or estimated}元，"
            f"生成{len(packing)}项行李清单，顺延{len(postponed)}个学习任务"
        )
        return results

    # ==================== 场景2：备考冲刺 ====================

    async def exam_prep_linkage(self, subject: str, exam_date: str,
                                 daily_hours: int = 6) -> dict[str, Any]:
        """
        备考冲刺联动链路：
        上调每日学习任务 → 压缩娱乐休闲日程 → 缩减外出娱乐预算
        """
        results = {"scenario": "exam_prep", "steps": []}

        # 1. 上调每日学习任务
        rec = await self.study.get_daily_recommendation()
        new_target = min(15, rec.get("new_knowledge_target", 5) + 5)
        review_target = min(30, rec.get("review_target", 10) + 10)
        results["steps"].append({
            "step": "increase_study_load", "status": "ok", "subject": subject,
            "new_knowledge_target": new_target, "review_target": review_target,
        })

        # 2. 压缩娱乐休闲日程（暂停未来7天）
        now = datetime.utcnow()
        week_later = now + timedelta(days=7)
        cleared = await self._pause_schedules_in_range(now, week_later)
        results["steps"].append({"step": "compress_entertainment", "status": "ok", "cleared_count": len(cleared)})

        # 3. 缩减外出娱乐预算
        month = now.strftime('%Y-%m')
        await self._reduce_budget("entertainment", 0.2, month)
        await self._reduce_budget("shopping", 0.5, month)
        results["steps"].append({"step": "reduce_budget", "status": "ok", "categories": ["entertainment", "shopping"]})

        # 4. 增加学习预算
        study_budget_result = await self.session.execute(
            select(Budget).where(and_(Budget.user_id == self.user_id, Budget.category == "study", Budget.effective_month == month))
        )
        if not study_budget_result.scalar_one_or_none():
            await self._set_budget("study", 200, month)
        results["steps"].append({"step": "ensure_study_budget", "status": "ok"})

        # 5. 创建备考计划
        plan = await self._create_exam_plan(subject, exam_date, daily_hours)
        results["steps"].append({"step": "create_exam_plan", "status": "ok", "plan_id": plan.id})

        await self.session.commit()
        results["summary"] = (
            f"备考冲刺已启动：{subject} 目标{exam_date}，"
            f"学习任务上调至{new_target}个新知识/天，"
            f"清空{len(cleared)}个娱乐日程，娱乐预算缩减80%"
        )
        return results

    # ==================== 场景3：生病休养 ====================

    async def sick_rest_linkage(self, rest_days: int = 3,
                                  symptoms: str | None = None) -> dict[str, Any]:
        """
        生病休养联动链路：
        暂停学习与工作任务 → 调低饮食消费预算 → 延后全部待办日程
        """
        results = {"scenario": "sick_rest", "steps": []}

        # 1. 暂停所有学习与工作任务
        now = datetime.utcnow()
        rest_until = now + timedelta(days=rest_days)

        all_cleared = await self._pause_schedules_in_range(now, rest_until)
        results["steps"].append({"step": "pause_all_tasks", "status": "ok", "paused_count": len(all_cleared)})

        # 2. 一键暂停所有未来日程
        pause_result = await self.schedule.emergency_pause(reason="sick")
        results["steps"].append({"step": "emergency_pause", "status": "ok", "paused": pause_result["paused_count"]})

        # 3. 调低饮食消费预算
        month = now.strftime('%Y-%m')
        await self._reduce_budget("food", 0.6, month)
        await self._reduce_budget("entertainment", 0.1, month)
        results["steps"].append({"step": "reduce_budget", "status": "ok", "categories": ["food", "entertainment"]})

        # 4. 延后全部待办日程
        all_tasks_result = await self.session.execute(
            select(Schedule).where(and_(
                Schedule.user_id == self.user_id,
                Schedule.is_completed == False,
                Schedule.start_time <= rest_until,
            ))
        )
        postponed_count = 0
        for task in all_tasks_result.scalars().all():
            if task.start_time and not task.is_paused:
                duration = (task.end_time - task.start_time) if task.end_time else timedelta(hours=1)
                task.original_start = task.start_time
                task.start_time = rest_until + timedelta(hours=2)
                task.end_time = task.start_time + duration
                task.is_paused = False
                postponed_count += 1

        results["steps"].append({"step": "postpone_all_tasks", "status": "ok", "postponed_count": postponed_count})

        await self.session.commit()
        results["summary"] = (
            f"病休模式已启动：预计休息{rest_days}天，"
            f"暂停{len(all_cleared)}个日程，"
            f"饮食预算减至60%，延后{postponed_count}个待办"
        )
        return results
