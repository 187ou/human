"""出行规划服务：开销预估、行李清单、日程联动、天气提醒"""
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.travel import TravelPlan
from app.models.item import Item
from app.models.schedule import Schedule, ScheduleItem


class TravelPlanner:
    """出行规划引擎"""

    # 天气对应的行李建议
    WEATHER_GEAR = {
        "rainy": ["雨伞", "雨衣", "防水鞋套", "塑料袋(保护电子设备)"],
        "snowy": ["防滑手套", "围巾", "保暖帽", "防滑鞋", "暖宝宝"],
        "sunny": ["防晒霜", "太阳镜", "遮阳帽", "补水喷雾"],
        "cold": ["厚外套", "围巾", "手套", "保暖内衣"],
        "hot": ["短袖", "防晒霜", "遮阳帽", "清凉喷雾", "便携风扇"],
    }

    # 基础行李模板
    BASE_PACKING = {
        "document": ["身份证", "银行卡", "钥匙", "手机充电器"],
        "toiletries": ["牙刷", "牙膏", "毛巾", "洗面奶"],
        "clothing": ["换洗衣物", "袜子", "内衣"],
        "electronics": ["手机", "充电宝", "耳机"],
        "misc": ["纸巾", "水杯", "常用药品"],
    }

    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id

    # ==================== 开销预估 ====================

    async def estimate_costs(self, travel_type: str, destination: str | None,
                              duration_days: int = 1) -> dict[str, Any]:
        """预估出行开销"""
        transport_cost = 0
        meal_cost = 0
        duration_min = 0

        if travel_type == "commute":
            transport_cost = 10  # 通勤默认10元
            meal_cost = 30 * duration_days
            duration_min = 60
        elif travel_type == "trip":
            transport_cost = 200  # 短途旅行默认200元
            meal_cost = 80 * duration_days
            duration_min = 240
        elif travel_type == "flight":
            transport_cost = 800  # 航班默认800元
            meal_cost = 100 * duration_days
            duration_min = 360
        elif travel_type == "hotel":
            transport_cost = 300
            meal_cost = 150 * duration_days
            duration_min = 120

        # 根据目的地距离微调
        if destination:
            if any(city in (destination or "") for city in ["北京", "上海", "广州", "深圳"]):
                transport_cost *= 1.5
                duration_min = int(duration_min * 1.3)

        return {
            "transport_cost": round(transport_cost, 2),
            "meal_cost": round(meal_cost, 2),
            "total_cost": round(transport_cost + meal_cost, 2),
            "duration_min": duration_min,
        }

    # ==================== 行李清单生成 ====================

    async def generate_packing_list(self, duration_days: int, weather_condition: str | None = None,
                                      temp: float | None = None, category: str | None = None) -> list[dict[str, Any]]:
        """生成行李打包清单"""
        packing = []

        # 基础物品
        for cat, items in self.BASE_PACKING.items():
            for item_name in items:
                packing.append({
                    "item": item_name,
                    "category": cat,
                    "quantity": 1,
                    "is_checked": False,
                })

        # 根据天数增加衣物
        if duration_days > 1:
            packing.append({"item": "换洗衣物", "category": "clothing", "quantity": duration_days, "is_checked": False})
            packing.append({"item": "袜子", "category": "clothing", "quantity": duration_days + 1, "is_checked": False})

        # 根据天气添加物品
        if weather_condition:
            weather_items = self.WEATHER_GEAR.get(weather_condition, [])
            for item_name in weather_items:
                packing.append({
                    "item": item_name,
                    "category": "weather",
                    "quantity": 1,
                    "is_checked": False,
                })

        # 根据温度调整
        if temp is not None:
            if temp < 5:
                for item in self.WEATHER_GEAR.get("cold", []):
                    if not any(p["item"] == item for p in packing):
                        packing.append({"item": item, "category": "weather", "quantity": 1, "is_checked": False})
            elif temp > 30:
                for item in self.WEATHER_GEAR.get("hot", []):
                    if not any(p["item"] == item for p in packing):
                        packing.append({"item": item, "category": "weather", "quantity": 1, "is_checked": False})

        # 检查库存中已有物品
        existing_items = await self.session.execute(
            select(Item.name).where(Item.user_id == self.user_id)
        )
        owned = {row[0].lower() for row in existing_items.all()}

        for p in packing:
            if p["item"].lower() in owned:
                p["in_storage"] = True

        return packing

    # ==================== 日程联动 ====================

    async def clear_conflicting_schedules(self, depart_time: datetime, arrive_time: datetime) -> list[int]:
        """清空出行时段的居家日程"""
        result = await self.session.execute(
            select(Schedule).where(
                and_(
                    Schedule.user_id == self.user_id,
                    Schedule.is_completed == False,
                    Schedule.is_paused == False,
                    Schedule.start_time >= depart_time,
                    Schedule.start_time <= arrive_time,
                    Schedule.category.in_(["fixed", "flexible", "study"]),
                )
            )
        )
        cleared_ids = []
        for s in result.scalars().all():
            s.is_paused = True
            s.original_start = s.start_time
            cleared_ids.append(s.id)

        await self.session.flush()
        return cleared_ids

    async def postpone_tasks(self, depart_time: datetime, arrive_time: datetime,
                              delay_hours: int = 24) -> list[int]:
        """顺延出行时段的碎片任务"""
        result = await self.session.execute(
            select(ScheduleItem).where(
                and_(
                    ScheduleItem.user_id == self.user_id,
                    ScheduleItem.is_done == False,
                    ScheduleItem.created_at >= depart_time,
                    ScheduleItem.created_at <= arrive_time,
                )
            )
        )
        postponed_ids = []
        for item in result.scalars().all():
            postponed_ids.append(item.id)

        await self.session.flush()
        return postponed_ids

    # ==================== 天气联动 ====================

    async def check_weather_risk(self, destination: str | None) -> dict[str, Any]:
        """检查天气风险（模拟）"""
        # 模拟天气数据（实际项目中接入天气API）
        import random
        conditions = ["sunny", "rainy", "snowy", "cloudy"]
        condition = random.choice(conditions)
        temp = random.randint(-5, 35)

        risk = "low"
        alert_message = ""
        suggestions = []

        if condition == "rainy":
            risk = "medium"
            alert_message = f"目的地{destination or ''}预报有雨"
            suggestions = ["准备雨具", "选择室内活动", "驾车出行注意安全"]
        elif condition == "snowy":
            risk = "high"
            alert_message = f"目的地{destination or ''}预报有雪"
            suggestions = ["更换防滑轮胎", "准备防滑链", "备好保暖衣物", "考虑改期"]
        elif temp < 0:
            risk = "medium"
            alert_message = f"目的地{destination or ''}气温较低({temp}°C)"
            suggestions = ["准备厚衣物", "注意防滑"]
        elif temp > 35:
            risk = "medium"
            alert_message = f"目的地{destination or ''}高温({temp}°C)"
            suggestions = ["准备防晒用品", "多带水", "避免正午外出"]

        return {
            "condition": condition,
            "temperature": temp,
            "risk_level": risk,
            "alert_message": alert_message,
            "suggestions": suggestions,
        }

    # ==================== 综合规划 ====================

    async def create_travel_plan(self, title: str, travel_type: str, destination: str | None,
                                  depart_time: datetime, arrive_time: datetime | None = None,
                                  **kwargs) -> dict[str, Any]:
        """创建完整出行计划（含所有联动）"""
        # 计算天数
        if arrive_time:
            duration_days = max(1, (arrive_time - depart_time).days + 1)
        else:
            duration_days = 1

        # 天气检查
        weather = await self.check_weather_risk(destination)

        # 开销预估
        costs = await self.estimate_costs(travel_type, destination, duration_days)

        # 行李清单
        packing = await self.generate_packing_list(
            duration_days, weather["condition"], weather["temperature"]
        )

        # 日程联动
        cleared = []
        postponed = []
        if arrive_time:
            cleared = await self.clear_conflicting_schedules(depart_time, arrive_time)
            postponed = await self.postpone_tasks(depart_time, arrive_time)

        # 创建计划
        plan = TravelPlan(
            user_id=self.user_id,
            title=title,
            travel_type=travel_type,
            origin=kwargs.get("origin"),
            destination=destination,
            depart_time=depart_time,
            arrive_time=arrive_time,
            weather_risk=weather["risk_level"],
            weather_condition=weather["condition"],
            weather_temp=weather["temperature"],
            estimated_transport_cost=costs["transport_cost"],
            estimated_meal_cost=costs["meal_cost"],
            estimated_total_cost=costs["total_cost"],
            estimated_duration_min=costs["duration_min"],
            suggested_leave_time=depart_time - timedelta(minutes=30),
            packing_list=packing,
            cleared_schedule_ids=cleared,
            postponed_task_ids=postponed,
            notes=kwargs.get("notes"),
        )
        self.session.add(plan)
        await self.session.flush()

        return {
            "plan_id": plan.id,
            "estimated_costs": costs,
            "weather": weather,
            "packing_list": packing,
            "cleared_schedules": cleared,
            "postponed_tasks": postponed,
            "suggested_leave_time": plan.suggested_leave_time.isoformat() if plan.suggested_leave_time else None,
        }
