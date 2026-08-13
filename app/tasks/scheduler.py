"""APScheduler定时任务：每日复盘、临期巡检、消息推送、夜间增量演化"""
import asyncio
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from app.db import AsyncSessionLocal
from app.services.notification_service import NotificationService
from app.services.consume_analyzer import ConsumeAnalyzer
from app.services.item_manager import ItemManager
from app.services.study_manager import StudyManager
from app.evolution.engine import EvolutionEngine

scheduler = AsyncIOScheduler()


async def daily_review_task():
    """每日复盘任务：22:00执行"""
    logger.info("[Scheduler] 开始每日复盘...")
    async with AsyncSessionLocal() as session:
        try:
            # 1. 生成所有用户的月度消费复盘
            from sqlalchemy import select
            from app.models.user import User
            users = await session.execute(select(User.id))
            for (user_id,) in users.all():
                try:
                    analyzer = ConsumeAnalyzer(session, user_id)
                    await analyzer.generate_monthly_review()
                    await session.flush()
                except Exception as e:
                    logger.error(f"用户{user_id}消费复盘失败: {e}")
            await session.commit()
            logger.info("[Scheduler] 每日复盘完成")
        except Exception as e:
            logger.error(f"每日复盘任务失败: {e}")


async def expiration_check_task():
    """临期巡检任务：每天8:00和18:00执行"""
    logger.info("[Scheduler] 开始临期巡检...")
    async with AsyncSessionLocal() as session:
        try:
            from sqlalchemy import select
            from app.models.user import User
            users = await session.execute(select(User.id))
            total_alerts = 0
            for (user_id,) in users.all():
                try:
                    item_mgr = ItemManager(session, user_id)
                    alerts = await item_mgr.check_expiration_alerts()
                    notif_svc = NotificationService(session, user_id)
                    notif_alerts = await notif_svc.collect_all_notifications()
                    total_alerts += len(alerts) + len(notif_alerts)
                    await session.flush()
                except Exception as e:
                    logger.error(f"用户{user_id}临期巡检失败: {e}")
            await session.commit()
            logger.info(f"[Scheduler] 临期巡检完成，共{total_alerts}条提醒")
        except Exception as e:
            logger.error(f"临期巡检任务失败: {e}")


async def notification_push_task():
    """消息推送任务：每天7:00、12:00、18:00执行"""
    logger.info("[Scheduler] 开始消息推送...")
    async with AsyncSessionLocal() as session:
        try:
            from sqlalchemy import select
            from app.models.user import User
            users = await session.execute(select(User.id))
            total_pushed = 0
            for (user_id,) in users.all():
                try:
                    notif_svc = NotificationService(session, user.id)
                    notifications = await notif_svc.collect_all_notifications()
                    total_pushed += len(notifications)
                    await session.flush()
                except Exception as e:
                    logger.error(f"用户{user_id}消息推送失败: {e}")
            await session.commit()
            logger.info(f"[Scheduler] 消息推送完成，共{total_pushed}条通知")
        except Exception as e:
            logger.error(f"消息推送任务失败: {e}")


async def nightly_evolution_task():
    """夜间增量演化任务：每天2:00执行（第2层：轻量化演化）"""
    logger.info("[Scheduler] 开始夜间增量演化...")
    async with AsyncSessionLocal() as session:
        try:
            from sqlalchemy import select
            from app.models.user import User
            users = await session.execute(select(User.id))
            total_rules = 0
            for (user_id,) in users.all():
                try:
                    from app.services.evolution_engine import EvolutionEngine as LayeredEngine
                    engine = LayeredEngine(session, user_id)
                    result = await engine.nightly_evolution()
                    total_rules += result.get("rules_updated", 0)
                    await session.flush()
                except Exception as e:
                    logger.error(f"用户{user_id}增量演化失败: {e}")
            await session.commit()
            logger.info(f"[Scheduler] 夜间增量演化完成，更新{total_rules}条规则")
        except Exception as e:
            logger.error(f"夜间增量演化任务失败: {e}")


async def weekly_evolution_task():
    """周度全局深度演化任务：每周日3:00执行（第3层：深度演化）"""
    logger.info("[Scheduler] 开始周度全局深度演化...")
    async with AsyncSessionLocal() as session:
        try:
            from sqlalchemy import select
            from app.models.user import User
            users = await session.execute(select(User.id))
            for (user_id,) in users.all():
                try:
                    from app.services.evolution_engine import EvolutionEngine as LayeredEngine
                    engine = LayeredEngine(session, user_id)
                    result = await engine.weekly_evolution()
                    await session.flush()
                except Exception as e:
                    logger.error(f"用户{user_id}深度演化失败: {e}")
            await session.commit()
            logger.info("[Scheduler] 周度全局深度演化完成")
        except Exception as e:
            logger.error(f"周度全局深度演化任务失败: {e}")


async def meta_evolution_task():
    """元演化调控任务：每天0:00执行"""
    logger.info("[Scheduler] 开始元演化调控...")
    async with AsyncSessionLocal() as session:
        try:
            from sqlalchemy import select
            from app.models.user import User
            users = await session.execute(select(User.id))
            for (user_id,) in users.all():
                try:
                    from app.services.meta_agent import MetaEvolutionAgent
                    agent = MetaEvolutionAgent(session, user_id)
                    await agent.evaluate_and_adjust()
                    await session.flush()
                except Exception as e:
                    logger.error(f"用户{user_id}元演化调控失败: {e}")
            await session.commit()
            logger.info("[Scheduler] 元演化调控完成")
        except Exception as e:
            logger.error(f"元演化调控任务失败: {e}")


async def study_checkin_reminder_task():
    """学习打卡提醒：每天20:00执行"""
    logger.info("[Scheduler] 开始学习打卡提醒...")
    async with AsyncSessionLocal() as session:
        try:
            from sqlalchemy import select
            from app.models.user import User
            users = await session.execute(select(User.id))
            for (user_id,) in users.all():
                try:
                    notif_svc = NotificationService(session, user_id)
                    await notif_svc.collect_all_notifications()
                    await session.flush()
                except Exception as e:
                    logger.error(f"用户{user_id}打卡提醒失败: {e}")
            await session.commit()
            logger.info("[Scheduler] 学习打卡提醒完成")
        except Exception as e:
            logger.error(f"学习打卡提醒任务失败: {e}")


def init_scheduler():
    """初始化并启动定时任务调度器"""
    # 每日复盘：22:00
    scheduler.add_job(daily_review_task, CronTrigger(hour=22, minute=0), id="daily_review")
    # 临期巡检：8:00 和 18:00
    scheduler.add_job(expiration_check_task, CronTrigger(hour=8, minute=0), id="expiration_morning")
    scheduler.add_job(expiration_check_task, CronTrigger(hour=18, minute=0), id="expiration_evening")
    # 消息推送：7:00、12:00、18:00
    scheduler.add_job(notification_push_task, CronTrigger(hour=7, minute=0), id="notify_morning")
    scheduler.add_job(notification_push_task, CronTrigger(hour=12, minute=0), id="notify_noon")
    scheduler.add_job(notification_push_task, CronTrigger(hour=18, minute=0), id="notify_evening")
    # 夜间增量演化：2:00（第2层）
    scheduler.add_job(nightly_evolution_task, CronTrigger(hour=2, minute=0), id="nightly_evolution")
    # 周度全局深度演化：周日3:00（第3层）
    scheduler.add_job(weekly_evolution_task, CronTrigger(day_of_week="sun", hour=3, minute=0), id="weekly_evolution")
    # 元演化调控：每天0:00（Meta-Agent）
    scheduler.add_job(meta_evolution_task, CronTrigger(hour=0, minute=0), id="meta_evolution")
    # 学习打卡提醒：20:00
    scheduler.add_job(study_checkin_reminder_task, CronTrigger(hour=20, minute=0), id="study_checkin")
    scheduler.start()
    logger.info("[Scheduler] 定时任务调度器已启动")
    return scheduler


def shutdown_scheduler():
    """关闭调度器"""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("[Scheduler] 定时任务调度器已关闭")
