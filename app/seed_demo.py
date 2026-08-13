"""初始化演示数据"""
import asyncio
from datetime import datetime, timedelta
from app.db import AsyncSessionLocal, init_db, engine, Base
from app.models.user import User
from app.models.schedule import Schedule
from app.models.consume import ConsumeRecord, Budget
from app.models.item import Item
from app.models.study import StudyRecord
from app.models.travel import TravelPlan
from app.models.behavior import BehaviorLog
from app.models.innovation import EnergyRecord
from app.models.rule import UserRule


async def seed():
    await init_db()
    async with AsyncSessionLocal() as s:
        # 检查是否已有数据
        result = await s.execute(__import__("sqlalchemy").select(User).where(User.id == 1))
        if result.scalar_one_or_none():
            print("[OK] 用户1已存在，跳过初始化")
            return

        now = datetime.utcnow()

        # === 用户 ===
        s.add(User(id=1, username="学生小明", hashed_password="x", user_type="student",
                    wake_hour=7, sleep_hour=23, commute_minutes=30,
                    monthly_income=3000, chronotype="early_bird", has_kitchen=True,
                    study_goal="考研成功", study_subject="计算机科学"))

        # === 日程 ===
        schedules = [
            Schedule(user_id=1, title="高数复习", category="study",
                     start_time=now + timedelta(hours=2), end_time=now + timedelta(hours=4),
                     is_completed=False),
            Schedule(user_id=1, title="英语阅读", category="study",
                     start_time=now + timedelta(days=1, hours=9), end_time=now + timedelta(days=1, hours=10, minutes=30),
                     is_completed=False),
            Schedule(user_id=1, title="健身", category="sport",
                     start_time=now + timedelta(days=1, hours=18), end_time=now + timedelta(days=1, hours=19),
                     is_completed=False),
            Schedule(user_id=1, title="项目会议", category="fixed",
                     start_time=now + timedelta(days=2, hours=14), end_time=now + timedelta(days=2, hours=15, minutes=30),
                     is_completed=False),
        ]
        s.add_all(schedules)

        # === 消费 ===
        consumes = [
            ConsumeRecord(user_id=1, amount=25.5, category="food", merchant="食堂",
                          occurred_at=now - timedelta(hours=3)),
            ConsumeRecord(user_id=1, amount=15.0, category="food", merchant="咖啡店",
                          occurred_at=now - timedelta(days=1, hours=2)),
            ConsumeRecord(user_id=1, amount=35.0, category="food", merchant="外卖",
                          occurred_at=now - timedelta(days=2, hours=5)),
            ConsumeRecord(user_id=1, amount=128.0, category="shopping", merchant="淘宝",
                          occurred_at=now - timedelta(days=3), is_impulse=True),
            ConsumeRecord(user_id=1, amount=45.0, category="study", merchant="书店",
                          occurred_at=now - timedelta(days=4)),
            ConsumeRecord(user_id=1, amount=8.0, category="transport", merchant="地铁",
                          occurred_at=now - timedelta(days=1)),
            ConsumeRecord(user_id=1, amount=68.0, category="entertainment", merchant="电影票",
                          occurred_at=now - timedelta(days=5)),
            ConsumeRecord(user_id=1, amount=32.0, category="food", merchant="超市",
                          occurred_at=now - timedelta(days=6)),
            ConsumeRecord(user_id=1, amount=25.0, category="food", merchant="食堂",
                          occurred_at=now - timedelta(days=7)),
            ConsumeRecord(user_id=1, amount=88.0, category="shopping", merchant="京东",
                          occurred_at=now - timedelta(days=8), is_impulse=True),
        ]
        s.add_all(consumes)

        # === 预算 ===
        budgets = [
            Budget(user_id=1, category="food", monthly_limit=800, effective_month=now.strftime("%Y-%m")),
            Budget(user_id=1, category="shopping", monthly_limit=300, effective_month=now.strftime("%Y-%m")),
            Budget(user_id=1, category="transport", monthly_limit=100, effective_month=now.strftime("%Y-%m")),
            Budget(user_id=1, category="entertainment", monthly_limit=200, effective_month=now.strftime("%Y-%m")),
            Budget(user_id=1, category="study", monthly_limit=200, effective_month=now.strftime("%Y-%m")),
        ]
        s.add_all(budgets)

        # === 物品 ===
        items = [
            Item(user_id=1, name="牛奶", category="food", location_path="MyHome/Kitchen/Fridge", quantity=3,
                 expire_at=now + timedelta(days=5)),
            Item(user_id=1, name="面包", category="food", location_path="MyHome/Kitchen/Counter", quantity=1,
                 expire_at=now + timedelta(days=2)),
            Item(user_id=1, name="洗发水", category="cosmetic", location_path="MyHome/Bathroom", quantity=1,
                 expire_at=now + timedelta(days=180)),
            Item(user_id=1, name="考研英语书", category="other", location_path="MyHome/Bedroom/Shelf", quantity=1),
            Item(user_id=1, name="健身卡", category="card", location_path="Wallet", quantity=1,
                 expire_at=now + timedelta(days=90)),
        ]
        s.add_all(items)

        # === 学习记录 ===
        studies = [
            StudyRecord(user_id=1, subject="高数", duration_minutes=60, efficiency=0.85,
                        start_time=now - timedelta(days=1, hours=2), end_time=now - timedelta(days=1),
                        is_delayed=False, quality=4),
            StudyRecord(user_id=1, subject="英语", duration_minutes=45, efficiency=0.72,
                        start_time=now - timedelta(days=2, hours=3), end_time=now - timedelta(days=2, hours=2, minutes=15),
                        is_delayed=True, quality=3),
            StudyRecord(user_id=1, subject="高数", duration_minutes=90, efficiency=0.90,
                        start_time=now - timedelta(days=3, hours=3), end_time=now - timedelta(days=3, hours=1, minutes=30),
                        is_delayed=False, quality=5),
            StudyRecord(user_id=1, subject="政治", duration_minutes=30, efficiency=0.65,
                        start_time=now - timedelta(days=4, hours=2), end_time=now - timedelta(days=4, hours=1, minutes=30),
                        is_delayed=True, quality=3),
            StudyRecord(user_id=1, subject="英语", duration_minutes=50, efficiency=0.78,
                        start_time=now - timedelta(days=5, hours=2), end_time=now - timedelta(days=5, hours=1, minutes=10),
                        is_delayed=False, quality=4),
        ]
        s.add_all(studies)

        # === 出行 ===
        travels = [
            TravelPlan(user_id=1, title="周末杭州游", travel_type="trip",
                       destination="杭州", depart_time=now + timedelta(days=5, hours=8),
                       arrive_time=now + timedelta(days=5, hours=12)),
            TravelPlan(user_id=1, title="回家过年", travel_type="trip",
                       destination="老家", depart_time=now + timedelta(days=20, hours=10),
                       arrive_time=now + timedelta(days=20, hours=18)),
        ]
        s.add_all(travels)

        # === 行为日志 ===
        for i in range(15):
            day = now - timedelta(days=i)
            s.add(BehaviorLog(
                user_id=1, dimension="time", event_type="schedule_completed",
                value=random.uniform(0.6, 1.0), hour_of_day=random.randint(8, 22),
                day_of_week=day.weekday(), created_at=day,
                schedule_completed=random.random() > 0.3,
                schedule_self_rating=random.randint(3, 5),
                schedule_is_delayed=random.random() < 0.2,
            ))
            if random.random() > 0.4:
                s.add(BehaviorLog(
                    user_id=1, dimension="study", event_type="study_session",
                    value=random.uniform(0.5, 0.95), hour_of_day=random.randint(8, 22),
                    day_of_week=day.weekday(), created_at=day,
                    study_accuracy=random.uniform(0.6, 0.95),
                    study_focus_min=random.randint(30, 90),
                ))
            if random.random() > 0.3:
                s.add(BehaviorLog(
                    user_id=1, dimension="consume", event_type="consume",
                    value=random.uniform(10, 150), hour_of_day=random.randint(10, 21),
                    day_of_week=day.weekday(), created_at=day,
                    consume_is_impulse=random.random() < 0.2,
                    consume_is_necessity=random.random() > 0.3,
                ))

        # === 精力记录 ===
        for i in range(7):
            day = (now - timedelta(days=i)).strftime("%Y-%m-%d")
            energy = random.randint(40, 85)
            s.add(EnergyRecord(
                user_id=1, record_date=day,
                sleep_score=random.uniform(60, 90),
                load_score=random.uniform(30, 80),
                completion_score=random.uniform(0.5, 0.95),
                focus_score=random.uniform(0.5, 0.9),
                total_energy=energy,
                energy_level="high" if energy > 70 else "medium" if energy > 45 else "low",
            ))

        # === 规则 ===
        rules = [
            UserRule(user_id=1, dimension="time", name="早间高效时段",
                     description="8-10点精力最佳，安排高难度任务",
                     rule_expr={"type": "schedule_hard_task", "hours": [8, 9, 10]},
                     confidence=0.85, sample_count=15, priority=2),
            UserRule(user_id=1, dimension="consume", name="餐饮预算控制",
                     description="本月餐饮已超支20%，建议减少外卖",
                     rule_expr={"type": "budget_alert", "category": "food", "threshold": 0.8},
                     confidence=0.72, sample_count=10, priority=2),
            UserRule(user_id=1, dimension="study", name="晚间学习效率下降",
                     description="21点后正确率降低，不适合高难度内容",
                     rule_expr={"type": "avoid_hard_task", "after_hour": 21},
                     confidence=0.68, sample_count=8, priority=1),
        ]
        s.add_all(rules)

        await s.commit()
        print("[OK] 演示数据初始化完成！")


import random

if __name__ == "__main__":
    asyncio.run(seed())
