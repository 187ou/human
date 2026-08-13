"""学习督导管理服务：知识点、错题、效率统计、动态调整、休息日"""
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.study import StudyPlan, StudyRecord, KnowledgePoint, WrongQuestion, StudyStreak


class StudyManager:
    """学习督导引擎"""

    HIGH_INTENSITY_THRESHOLD = 180  # 3小时以上为高强度
    REST_AFTER_DAYS = 5  # 连续5天高强度后休息

    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id

    # ==================== 知识点管理 ====================

    async def add_knowledge_point(self, subject: str, title: str, description: str | None = None,
                                   source: str = "manual") -> KnowledgePoint:
        """添加知识点"""
        kp = KnowledgePoint(
            user_id=self.user_id, subject=subject, title=title,
            description=description, source=source,
        )
        self.session.add(kp)
        await self.session.flush()
        return kp

    async def get_knowledge_points(self, subject: str | None = None, min_mastery: int = -1) -> list[KnowledgePoint]:
        """获取知识点列表"""
        stmt = select(KnowledgePoint).where(
            and_(KnowledgePoint.user_id == self.user_id, KnowledgePoint.is_active == True)
        )
        if subject:
            stmt = stmt.where(KnowledgePoint.subject == subject)
        if min_mastery >= 0:
            stmt = stmt.where(KnowledgePoint.mastery_level <= min_mastery)
        result = await self.session.execute(stmt.order_by(KnowledgePoint.mastery_level))
        return list(result.scalars().all())

    async def update_mastery(self, kp_id: int, correct: bool) -> None:
        """更新知识点掌握程度"""
        kp = await self.session.get(KnowledgePoint, kp_id)
        if not kp or kp.user_id != self.user_id:
            return

        kp.total_attempts += 1
        if correct:
            kp.correct_attempts += 1
            kp.mastery_level = min(100, kp.mastery_level + 10)
        else:
            kp.mastery_level = max(0, kp.mastery_level - 5)

        kp.accuracy_rate = kp.correct_attempts / kp.total_attempts if kp.total_attempts > 0 else 0
        kp.last_reviewed_at = datetime.utcnow()

    # ==================== 错题管理 ====================

    async def add_wrong_question(self, subject: str, question: str, correct_answer: str | None = None,
                                  my_answer: str | None = None, knowledge_point_id: int | None = None,
                                  analysis: str | None = None) -> WrongQuestion:
        """添加错题"""
        wq = WrongQuestion(
            user_id=self.user_id, subject=subject, question=question,
            correct_answer=correct_answer, my_answer=my_answer,
            knowledge_point_id=knowledge_point_id, analysis=analysis,
        )
        self.session.add(wq)
        await self.session.flush()
        return wq

    async def get_wrong_questions(self, subject: str | None = None, unmastered_only: bool = True) -> list[WrongQuestion]:
        """获取错题列表"""
        stmt = select(WrongQuestion).where(WrongQuestion.user_id == self.user_id)
        if subject:
            stmt = stmt.where(WrongQuestion.subject == subject)
        if unmastered_only:
            stmt = stmt.where(WrongQuestion.is_mastered == False)
        result = await self.session.execute(stmt.order_by(WrongQuestion.created_at.desc()))
        return list(result.scalars().all())

    async def mark_mastered(self, wq_id: int) -> None:
        """标记错题已掌握"""
        wq = await self.session.get(WrongQuestion, wq_id)
        if wq and wq.user_id == self.user_id:
            wq.is_mastered = True
            wq.review_count += 1
            wq.last_reviewed_at = datetime.utcnow()

    # ==================== 效率统计 ====================

    async def record_study(self, subject: str, duration_minutes: int, focus_minutes: int | None = None,
                            accuracy: float | None = None, efficiency: float | None = None,
                            content: str | None = None, plan_id: int | None = None) -> StudyRecord:
        """记录学习（含专注时长统计）"""
        now = datetime.utcnow()
        focus = focus_minutes if focus_minutes is not None else duration_minutes
        idle = max(0, duration_minutes - focus)

        record = StudyRecord(
            user_id=self.user_id, plan_id=plan_id, subject=subject, content=content,
            start_time=now - timedelta(minutes=duration_minutes), end_time=now,
            duration_minutes=duration_minutes, focus_minutes=focus, idle_minutes=idle,
            accuracy=accuracy, efficiency=efficiency,
        )
        self.session.add(record)
        await self.session.flush()

        # 更新连续学习记录
        await self._update_streak(subject, duration_minutes)

        return record

    async def _update_streak(self, subject: str, duration_minutes: int) -> None:
        """更新连续学习记录"""
        today = datetime.utcnow().strftime('%Y-%m-%d')

        existing = await self.session.execute(
            select(StudyStreak).where(
                and_(StudyStreak.user_id == self.user_id, StudyStreak.study_date == today)
            )
        )
        streak = existing.scalar_one_or_none()

        if streak:
            streak.total_minutes += duration_minutes
        else:
            intensity = "high" if duration_minutes >= self.HIGH_INTENSITY_THRESHOLD else "normal" if duration_minutes >= 60 else "light"
            streak = StudyStreak(
                user_id=self.user_id, study_date=today,
                intensity=intensity, total_minutes=duration_minutes,
            )
            self.session.add(streak)

        # 检查是否需要插入休息日
        await self._check_rest_day()

    async def _check_rest_day(self) -> None:
        """检查是否需要插入休息日"""
        # 获取最近5天的学习记录
        five_days_ago = (datetime.utcnow() - timedelta(days=5)).strftime('%Y-%m-%d')

        result = await self.session.execute(
            select(StudyStreak).where(
                and_(
                    StudyStreak.user_id == self.user_id,
                    StudyStreak.study_date >= five_days_ago,
                    StudyStreak.is_rest_day == False,
                )
            ).order_by(StudyStreak.study_date)
        )
        recent = result.scalars().all()

        # 检查是否连续5天高强度
        high_intensity_days = [s for s in recent if s.intensity == "high"]
        if len(high_intensity_days) >= self.REST_AFTER_DAYS:
            # 标记今天为建议休息日
            today = datetime.utcnow().strftime('%Y-%m-%d')
            existing = await self.session.execute(
                select(StudyStreak).where(
                    and_(StudyStreak.user_id == self.user_id, StudyStreak.study_date == today)
                )
            )
            streak = existing.scalar_one_or_none()
            if streak:
                streak.is_rest_day = True

    # ==================== 动态调整 ====================

    async def get_daily_recommendation(self) -> dict[str, Any]:
        """获取每日学习推荐（动态调整）"""
        today = datetime.utcnow().strftime('%Y-%m-%d')

        # 获取昨日学习情况
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')
        yesterday_result = await self.session.execute(
            select(func.coalesce(func.sum(StudyRecord.duration_minutes), 0),
                   func.coalesce(func.avg(StudyRecord.accuracy), 0),
                   func.coalesce(func.count(StudyRecord.id), 0)).where(
                and_(
                    StudyRecord.user_id == self.user_id,
                    func.strftime('%Y-%m-%d', StudyRecord.created_at) == yesterday,
                )
            )
        )
        row = yesterday_result.one()
        yesterday_minutes = row[0] or 0
        yesterday_accuracy = row[1] or 0
        yesterday_sessions = row[2] or 0

        # 获取平均正确率
        avg_accuracy_result = await self.session.execute(
            select(func.coalesce(func.avg(StudyRecord.accuracy), 0.7)).where(
                and_(
                    StudyRecord.user_id == self.user_id,
                    StudyRecord.accuracy != None,
                    StudyRecord.created_at >= datetime.utcnow() - timedelta(days=7),
                )
            )
        )
        avg_accuracy = avg_accuracy_result.scalar() or 0.7

        # 检查是否需要休息
        rest_check = await self.session.execute(
            select(StudyStreak).where(
                and_(
                    StudyStreak.user_id == self.user_id,
                    StudyStreak.study_date == today,
                    StudyStreak.is_rest_day == True,
                )
            )
        )
        is_rest_recommended = rest_check.scalar_one_or_none() is not None

        # 动态计算新知识点数量
        base_new_knowledge = 5
        if avg_accuracy >= 0.8:
            new_knowledge_target = base_new_knowledge + 2  # 正确率高，增加新知识
        elif avg_accuracy >= 0.6:
            new_knowledge_target = base_new_knowledge
        else:
            new_knowledge_target = max(2, base_new_knowledge - 2)  # 正确率低，减少新知识

        # 检查昨日是否达标
        unmet_adjustment = 1.0
        if yesterday_sessions > 0:
            # 获取昨日计划
            plan_result = await self.session.execute(
                select(StudyPlan).where(
                    and_(StudyPlan.user_id == self.user_id, StudyPlan.status == "active")
                ).order_by(StudyPlan.created_at.desc()).limit(1)
            )
            plan = plan_result.scalar_one_or_none()
            if plan and plan.estimated_hours > 0:
                planned_minutes = plan.estimated_hours * 60
                if yesterday_minutes < planned_minutes * 0.7:
                    # 未达标（低于70%），下调今日任务
                    unmet_adjustment = 0.7
                    new_knowledge_target = max(1, int(new_knowledge_target * 0.7))

        # 休息日推荐
        if is_rest_recommended:
            new_knowledge_target = 0
            return {
                "is_rest_day": True,
                "message": "连续5天高强度学习，今天建议轻量复盘休息",
                "new_knowledge_target": 0,
                "review_target": 10,
                "suggested_duration": 30,
            }

        return {
            "is_rest_day": False,
            "yesterday_minutes": yesterday_minutes,
            "yesterday_accuracy": round(yesterday_accuracy, 2),
            "avg_accuracy": round(avg_accuracy, 2),
            "new_knowledge_target": new_knowledge_target,
            "review_target": 10,
            "suggested_duration": int(120 * unmet_adjustment),
            "unmet_adjustment": unmet_adjustment,
        }

    # ==================== 效率报告 ====================

    async def get_efficiency_report(self, days: int = 7) -> dict[str, Any]:
        """获取学习效率报告"""
        cutoff = datetime.utcnow() - timedelta(days=days)

        result = await self.session.execute(
            select(
                func.coalesce(func.sum(StudyRecord.duration_minutes), 0),
                func.coalesce(func.sum(StudyRecord.focus_minutes), 0),
                func.coalesce(func.sum(StudyRecord.idle_minutes), 0),
                func.coalesce(func.avg(StudyRecord.accuracy), 0),
                func.coalesce(func.avg(StudyRecord.efficiency), 0),
                func.count(StudyRecord.id),
            ).where(
                and_(StudyRecord.user_id == self.user_id, StudyRecord.created_at >= cutoff)
            )
        )
        row = result.one()

        total_minutes = row[0] or 0
        focus_minutes = row[1] or 0
        idle_minutes = row[2] or 0
        avg_accuracy = row[3] or 0
        avg_efficiency = row[4] or 0
        total_sessions = row[5] or 0

        focus_rate = focus_minutes / total_minutes if total_minutes > 0 else 0

        return {
            "period_days": days,
            "total_minutes": total_minutes,
            "focus_minutes": focus_minutes,
            "idle_minutes": idle_minutes,
            "focus_rate": round(focus_rate, 3),
            "avg_accuracy": round(avg_accuracy, 3),
            "avg_efficiency": round(avg_efficiency, 3),
            "total_sessions": total_sessions,
            "message": f"近{days}天专注率{focus_rate:.0%}，平均正确率{avg_accuracy:.0%}",
        }
