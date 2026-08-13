"""生活状态全局上下文记忆：30天画像"""
from collections import Counter
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.innovation import LifeStateSnapshot
from app.models.behavior import BehaviorLog


class LifeStateManager:
    """生活状态全局上下文记忆

    识别人生阶段：
    - exam: 备考期（学习时长显著增加）
    - slump: 摆烂期（各项指标下降）
    - busy: 忙碌期（日程密度高）
    - vacation: 假期期（出行/娱乐增加）
    - normal: 正常期
    """

    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id

    async def generate_snapshot(self, target_date: datetime | None = None) -> LifeStateSnapshot:
        """生成生活状态快照"""
        if not target_date:
            target_date = datetime.utcnow()

        date_str = target_date.strftime('%Y-%m-%d')
        days_30 = (target_date - timedelta(days=30)).strftime('%Y-%m-%d')

        # 获取近30天行为数据
        result = await self.session.execute(
            select(BehaviorLog).where(and_(
                BehaviorLog.user_id == self.user_id,
                func.strftime('%Y-%m-%d', BehaviorLog.created_at) >= days_30,
            ))
        )
        logs = result.scalars().all()

        # 计算指标
        study_logs = [l for l in logs if l.dimension == "study"]
        consume_logs = [l for l in logs if l.dimension == "consume"]
        schedule_logs = [l for l in logs if l.dimension == "time"]

        avg_study = sum(l.study_focus_min or 0 for l in study_logs) / 30
        avg_consume = sum(l.value or 0 for l in consume_logs) / 30
        schedule_density = len(schedule_logs) / 30

        # 判定人生阶段
        phase, confidence = self._detect_phase(avg_study, avg_consume, schedule_density, len(logs))

        # 计算趋势
        trend = self._calc_trend(logs)

        # 生成摘要
        summary = self._generate_summary(phase, avg_study, avg_consume, trend)

        # 上下文记忆
        context_memory = {
            "recent_study_avg": round(avg_study, 1),
            "recent_consume_avg": round(avg_consume, 1),
            "schedule_density": round(schedule_density, 2),
            "total_events_30d": len(logs),
            "phase": phase,
        }

        # 查找或创建
        existing = await self.session.execute(
            select(LifeStateSnapshot).where(and_(
                LifeStateSnapshot.user_id == self.user_id,
                LifeStateSnapshot.snapshot_date == date_str,
            ))
        )
        snapshot = existing.scalar_one_or_none()

        if snapshot:
            snapshot.life_phase = phase
            snapshot.phase_confidence = confidence
            snapshot.avg_study_minutes = avg_study
            snapshot.avg_consume_amount = avg_consume
            snapshot.schedule_density = schedule_density
            snapshot.trend = trend
            snapshot.summary = summary
            snapshot.context_memory = context_memory
        else:
            snapshot = LifeStateSnapshot(
                user_id=self.user_id,
                snapshot_date=date_str,
                life_phase=phase,
                phase_confidence=confidence,
                avg_study_minutes=avg_study,
                avg_consume_amount=avg_consume,
                schedule_density=schedule_density,
                trend=trend,
                summary=summary,
                context_memory=context_memory,
            )
            self.session.add(snapshot)

        await self.session.flush()
        return snapshot

    def _detect_phase(self, avg_study: float, avg_consume: float,
                       schedule_density: float, total_events: int) -> tuple[str, float]:
        """检测人生阶段"""
        scores = {
            "normal": 0.3,
            "exam": 0.0,
            "slump": 0.0,
            "busy": 0.0,
            "vacation": 0.0,
        }

        # 备考期判定：学习时长>90分钟/天
        if avg_study > 90:
            scores["exam"] += 0.5
        elif avg_study > 60:
            scores["exam"] += 0.3

        # 摆烂期判定：总事件数少、学习时长低
        if total_events < 30:
            scores["slump"] += 0.4
        if avg_study < 20:
            scores["slump"] += 0.3

        # 忙碌期判定：日程密度>5
        if schedule_density > 5:
            scores["busy"] += 0.5
        elif schedule_density > 3:
            scores["busy"] += 0.3

        # 假期期判定：消费高、学习低
        if avg_consume > 200 and avg_study < 30:
            scores["vacation"] += 0.5

        # 取最高分阶段
        best_phase = max(scores, key=scores.get)
        confidence = scores[best_phase]

        return best_phase, round(confidence, 3)

    def _calc_trend(self, logs: list[BehaviorLog]) -> str:
        """计算趋势"""
        if len(logs) < 10:
            return "stable"

        # 分前后两半比较
        mid = len(logs) // 2
        first_half = logs[:mid]
        second_half = logs[mid:]

        first_avg = sum(l.value or 0 for l in first_half) / max(len(first_half), 1)
        second_avg = sum(l.value or 0 for l in second_half) / max(len(second_half), 1)

        if second_avg > first_avg * 1.2:
            return "rising"
        elif second_avg < first_avg * 0.8:
            return "declining"
        return "stable"

    def _generate_summary(self, phase: str, avg_study: float,
                           avg_consume: float, trend: str) -> str:
        """生成状态描述"""
        phase_desc = {
            "exam": "备考冲刺期",
            "slump": "低迷摆烂期",
            "busy": "忙碌高压期",
            "vacation": "假期放松期",
            "normal": "正常稳定期",
        }

        trend_desc = {
            "rising": "状态上升中",
            "declining": "状态下滑中",
            "stable": "状态平稳",
        }

        return f"当前处于{phase_desc.get(phase, '未知')}，{trend_desc.get(trend, '未知')}。日均学习{avg_study:.0f}分钟，日均消费¥{avg_consume:.0f}。"

    async def get_current_phase(self) -> dict[str, Any]:
        """获取当前生活阶段"""
        today = datetime.utcnow().strftime('%Y-%m-%d')
        result = await self.session.execute(
            select(LifeStateSnapshot).where(and_(
                LifeStateSnapshot.user_id == self.user_id,
                LifeStateSnapshot.snapshot_date <= today,
            )).order_by(LifeStateSnapshot.snapshot_date.desc()).limit(1)
        )
        snapshot = result.scalar_one_or_none()

        if not snapshot:
            snapshot = await self.generate_snapshot()

        return {
            "phase": snapshot.life_phase,
            "confidence": snapshot.phase_confidence,
            "trend": snapshot.trend,
            "summary": snapshot.summary,
            "context": snapshot.context_memory,
        }

    async def get_recent_snapshots(self, days: int = 7) -> list[LifeStateSnapshot]:
        """获取近期快照"""
        cutoff = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')
        result = await self.session.execute(
            select(LifeStateSnapshot).where(and_(
                LifeStateSnapshot.user_id == self.user_id,
                LifeStateSnapshot.snapshot_date >= cutoff,
            )).order_by(LifeStateSnapshot.snapshot_date)
        )
        return list(result.scalars().all())
