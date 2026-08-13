"""消息推送服务：聚合所有模块的提醒"""
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.models.schedule import Schedule
from app.models.item import Item
from app.models.consume import Budget, ConsumeRecord, BudgetAlert
from app.models.study import StudyRecord


class NotificationService:
    """消息推送引擎"""

    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id

    # ==================== 聚合所有通知 ====================

    async def collect_all_notifications(self) -> list[dict[str, Any]]:
        """收集所有模块的最新通知"""
        notifications = []

        # 1. 日程预告（未来2小时内的日程）
        schedule_alerts = await self._collect_schedule_reminders()
        notifications.extend(schedule_alerts)

        # 2. 物品临期预警
        item_alerts = await self._collect_item_expirations()
        notifications.extend(item_alerts)

        # 3. 预算预警
        budget_alerts = await self._collect_budget_alerts()
        notifications.extend(budget_alerts)

        # 4. 学习打卡提醒
        study_alerts = await self._collect_study_checkin()
        notifications.extend(study_alerts)

        return notifications

    async def _collect_schedule_reminders(self) -> list[dict[str, Any]]:
        """收集日程预告"""
        now = datetime.utcnow()
        two_hours_later = now + timedelta(hours=2)

        result = await self.session.execute(
            select(Schedule).where(and_(
                Schedule.user_id == self.user_id,
                Schedule.is_completed == False,
                Schedule.is_paused == False,
                Schedule.start_time >= now,
                Schedule.start_time <= two_hours_later,
            )).order_by(Schedule.start_time)
        )

        alerts = []
        for s in result.scalars().all():
            minutes_until = (s.start_time - now).total_seconds() / 60
            notif = Notification(
                user_id=self.user_id,
                type="schedule_reminder",
                source="schedule",
                title=f"日程即将开始: {s.title}",
                content=f"还有{int(minutes_until)}分钟开始：{s.title}" + (f" @ {s.location}" if s.location else ""),
                related_id=s.id,
                related_type="schedule",
                priority="high" if minutes_until <= 30 else "normal",
            )
            self.session.add(notif)
            alerts.append({"type": "schedule_reminder", "title": notif.title, "content": notif.content})

        return alerts

    async def _collect_item_expirations(self) -> list[dict[str, Any]]:
        """收集物品临期预警"""
        now = datetime.utcnow()

        result = await self.session.execute(
            select(Item).where(and_(
                Item.user_id == self.user_id,
                Item.expire_at != None,
                Item.expire_at >= now,
                Item.expire_at <= now + timedelta(days=7),
            )).order_by(Item.expire_at)
        )

        alerts = []
        for item in result.scalars().all():
            days_left = (item.expire_at - now).days
            notif = Notification(
                user_id=self.user_id,
                type="item_expire",
                source="item",
                title=f"物品即将过期: {item.name}",
                content=f"「{item.name}」{days_left}天后过期" + (f"，位置：{item.location_path}" if item.location_path else ""),
                related_id=item.id,
                related_type="item",
                priority="urgent" if days_left <= 2 else "high" if days_left <= 5 else "normal",
            )
            self.session.add(notif)
            alerts.append({"type": "item_expire", "title": notif.title, "content": notif.content})

        return alerts

    async def _collect_budget_alerts(self) -> list[dict[str, Any]]:
        """收集预算预警"""
        month = datetime.utcnow().strftime('%Y-%m')

        result = await self.session.execute(
            select(Budget).where(and_(
                Budget.user_id == self.user_id,
                Budget.effective_month == month,
            ))
        )

        alerts = []
        for budget in result.scalars().all():
            spent_result = await self.session.execute(
                select(func.coalesce(func.sum(ConsumeRecord.amount), 0)).where(and_(
                    ConsumeRecord.user_id == self.user_id,
                    ConsumeRecord.category == budget.category,
                    func.strftime('%Y-%m', ConsumeRecord.occurred_at) == month,
                ))
            )
            spent = spent_result.scalar() or 0
            percentage = spent / budget.monthly_limit if budget.monthly_limit > 0 else 0

            if percentage >= 0.8:
                if percentage >= 1.0:
                    alert_type = "budget_exceeded"
                    title = f"预算已超支: {budget.category}"
                elif percentage >= 0.95:
                    alert_type = "budget_critical"
                    title = f"预算即将用尽: {budget.category}"
                else:
                    alert_type = "budget_warning"
                    title = f"预算使用超80%: {budget.category}"

                notif = Notification(
                    user_id=self.user_id,
                    type=alert_type,
                    source="consume",
                    title=title,
                    content=f"品类{budget.category}已用¥{spent:.0f}/¥{budget.monthly_limit:.0f}（{percentage:.0%}）",
                    priority="urgent" if percentage >= 1.0 else "high",
                )
                self.session.add(notif)
                alerts.append({"type": alert_type, "title": notif.title, "content": notif.content})

        return alerts

    async def _collect_study_checkin(self) -> list[dict[str, Any]]:
        """收集学习打卡提醒"""
        today = datetime.utcnow().strftime('%Y-%m-%d')

        result = await self.session.execute(
            select(func.coalesce(func.sum(StudyRecord.duration_minutes), 0)).where(and_(
                StudyRecord.user_id == self.user_id,
                func.strftime('%Y-%m-%d', StudyRecord.created_at) == today,
            ))
        )
        today_minutes = result.scalar() or 0

        alerts = []
        if today_minutes == 0:
            notif = Notification(
                user_id=self.user_id,
                type="study_checkin",
                source="study",
                title="今日学习打卡提醒",
                content="今天还没有学习记录，记得保持学习节奏哦！",
                priority="normal",
            )
            self.session.add(notif)
            alerts.append({"type": "study_checkin", "title": notif.title, "content": notif.content})
        elif today_minutes < 30:
            notif = Notification(
                user_id=self.user_id,
                type="study_checkin",
                source="study",
                title="今日学习时长不足",
                content=f"今天已学习{int(today_minutes)}分钟，建议至少30分钟",
                priority="low",
            )
            self.session.add(notif)
            alerts.append({"type": "study_checkin", "title": notif.title, "content": notif.content})

        return alerts

    # ==================== 通知管理 ====================

    async def get_unread_notifications(self, limit: int = 50) -> list[Notification]:
        """获取未读通知"""
        result = await self.session.execute(
            select(Notification).where(and_(
                Notification.user_id == self.user_id,
                Notification.is_read.is_(False),
            )).order_by(Notification.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def mark_as_read(self, notification_id: int) -> bool:
        """标记已读"""
        notif = await self.session.get(Notification, notification_id)
        if notif and notif.user_id == self.user_id:
            notif.is_read = True
            await self.session.commit()
            return True
        return False

    async def mark_all_as_read(self) -> int:
        """全部标记已读"""
        result = await self.session.execute(
            select(Notification).where(and_(
                Notification.user_id == self.user_id,
                Notification.is_read == False,
            ))
        )
        count = 0
        for notif in result.scalars().all():
            notif.is_read = True
            count += 1
        await self.session.commit()
        return count

    async def get_notification_count(self) -> dict[str, int]:
        """获取各类通知数量"""
        unread = await self.session.scalar(
            select(func.count(Notification.id)).where(and_(
                Notification.user_id == self.user_id,
                Notification.is_read.is_(False),
            ))
        )
        total = await self.session.scalar(
            select(func.count(Notification.id)).where(Notification.user_id == self.user_id)
        )
        return {"unread": unread or 0, "total": total or 0}
