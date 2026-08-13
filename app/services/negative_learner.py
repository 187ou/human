"""行为负反馈学习机制：从失败中学习"""
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.advanced import NegativeFeedback
from app.models.behavior import BehaviorLog


class NegativeLearner:
    """负反馈学习器

    专门学习用户的失败、拖延、取消、未完成数据。
    重点规避用户短板。
    """

    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id

    async def record_feedback(self, feedback_type: str, dimension: str,
                               description: str, severity: int = 5,
                               related_id: int | None = None) -> NegativeFeedback:
        """记录负反馈"""
        # 根因分析
        root_cause = await self._analyze_root_cause(feedback_type, dimension, description)
        lesson = self._generate_lesson(feedback_type, dimension, root_cause)

        feedback = NegativeFeedback(
            user_id=self.user_id,
            feedback_type=feedback_type,
            dimension=dimension,
            related_id=related_id,
            description=description,
            severity=severity,
            root_cause=root_cause,
            lesson=lesson,
        )
        self.session.add(feedback)
        await self.session.flush()
        return feedback

    async def get_weakness_profile(self) -> dict[str, Any]:
        """获取用户短板画像"""
        cutoff = (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%d')
        result = await self.session.execute(
            select(NegativeFeedback).where(and_(
                NegativeFeedback.user_id == self.user_id,
                func.strftime('%Y-%m-%d', NegativeFeedback.created_at) >= cutoff,
            ))
        )
        feedbacks = result.scalars().all()

        if not feedbacks:
            return {"has_weakness": False}

        # 统计各类负反馈
        type_counts = defaultdict(int)
        dimension_counts = defaultdict(int)
        severity_sum = 0
        lessons = []

        for fb in feedbacks:
            type_counts[fb.feedback_type] += 1
            dimension_counts[fb.dimension] += 1
            severity_sum += fb.severity
            if fb.lesson:
                lessons.append(fb.lesson)

        avg_severity = severity_sum / len(feedbacks)

        # 找出最严重短板
        worst_type = max(type_counts, key=type_counts.get) if type_counts else None
        worst_dimension = max(dimension_counts, key=dimension_counts.get) if dimension_counts else None

        return {
            "has_weakness": True,
            "total_feedbacks": len(feedbacks),
            "avg_severity": round(avg_severity, 1),
            "worst_type": worst_type,
            "worst_dimension": worst_dimension,
            "type_distribution": dict(type_counts),
            "dimension_distribution": dict(dimension_counts),
            "key_lessons": lessons[:5],
            "recommendation": self._weakness_recommendation(worst_type, worst_dimension),
        }

    def _weakness_recommendation(self, worst_type: str | None, worst_dimension: str | None) -> str:
        """生成短板建议"""
        if not worst_type:
            return "暂无明显短板"

        recommendations = {
            ("delay", "time"): "您经常在时间规划上拖延，建议将大任务拆解为15分钟微任务",
            ("delay", "study"): "您在学习上容易拖延，建议采用番茄钟+奖励机制",
            ("cancel", "time"): "您经常取消日程，建议减少承诺、预留缓冲时间",
            ("fail", "study"): "学习任务经常失败，建议降低难度、从基础开始",
            ("skip", "study"): "您经常跳过学习，建议设置最低学习时长（如10分钟）",
            ("waste", "consume"): "消费浪费较多，建议大额消费前设置48小时冷静期",
        }
        return recommendations.get((worst_type, worst_dimension), f"需要关注{worst_type}类{worst_dimension}问题")

    async def _analyze_root_cause(self, feedback_type: str, dimension: str, description: str) -> str:
        """分析根因"""
        causes = {
            "delay": "任务难度过高或时间预估不足",
            "cancel": "计划冲突或优先级变化",
            "fail": "能力与任务不匹配或准备不足",
            "skip": "动力不足或习惯未养成",
            "waste": "冲动消费或缺乏规划",
        }
        return causes.get(feedback_type, "待分析")

    def _generate_lesson(self, feedback_type: str, dimension: str, root_cause: str) -> str:
        """生成教训"""
        return f"负面事件：{feedback_type}（{dimension}），根因：{root_cause}"
