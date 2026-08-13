"""物品收纳管理服务：层级位置、双阶段预警、闲置识别、智能推荐"""
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.item import Item, StorageLocation, ItemIdleAlert
from app.models.user import User


class ItemManager:
    """物品收纳管理引擎"""

    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id

    # ==================== 层级位置 ====================

    async def create_location(self, house: str = "默认房屋", room: str = "默认房间",
                               cabinet: str = "默认柜体", grid: str | None = None) -> StorageLocation:
        """创建存储位置"""
        parts = [house, room, cabinet]
        if grid:
            parts.append(grid)
        full_path = " / ".join(parts)

        loc = StorageLocation(
            user_id=self.user_id,
            house=house, room=room, cabinet=cabinet, grid=grid,
            full_path=full_path,
        )
        self.session.add(loc)
        await self.session.flush()
        return loc

    async def get_locations(self) -> list[StorageLocation]:
        """获取所有存储位置"""
        result = await self.session.execute(
            select(StorageLocation).where(
                and_(StorageLocation.user_id == self.user_id, StorageLocation.is_active == True)
            ).order_by(StorageLocation.house, StorageLocation.room, StorageLocation.cabinet)
        )
        return list(result.scalars().all())

    async def search_by_location(self, keyword: str) -> list[Item]:
        """按位置关键词搜索物品"""
        result = await self.session.execute(
            select(Item).where(
                and_(
                    Item.user_id == self.user_id,
                    Item.location_path.contains(keyword),
                )
            )
        )
        return list(result.scalars().all())

    # ==================== 双阶段临期预警 ====================

    async def check_expiration_alerts(self) -> list[dict[str, Any]]:
        """检查临期预警（双阶段）"""
        now = datetime.utcnow()
        items = await self.session.execute(
            select(Item).where(
                and_(
                    Item.user_id == self.user_id,
                    Item.expire_at != None,
                )
            )
        )

        alerts = []
        for item in items.scalars().all():
            days_left = (item.expire_at - now).days

            if days_left < 0:
                alerts.append({
                    "item_id": item.id,
                    "name": item.name,
                    "status": "expired",
                    "days_left": days_left,
                    "message": f"「{item.name}」已过期{abs(days_left)}天，建议丢弃",
                })
            elif days_left <= item.second_remind_days and not item.second_alert_sent:
                item.second_alert_sent = True
                alerts.append({
                    "item_id": item.id,
                    "name": item.name,
                    "status": "critical",
                    "days_left": days_left,
                    "message": f"「{item.name}」{days_left}天后过期，请尽快使用",
                    "recommendation": await self._generate_recommendation(item),
                })
            elif days_left <= item.expire_remind_days and not item.first_alert_sent:
                item.first_alert_sent = True
                alerts.append({
                    "item_id": item.id,
                    "name": item.name,
                    "status": "warning",
                    "days_left": days_left,
                    "message": f"「{item.name}」{days_left}天后过期",
                })

        await self.session.flush()
        return alerts

    # ==================== 智能推荐 ====================

    async def _generate_recommendation(self, item: Item) -> str:
        """生成消耗建议"""
        if item.category == 'food':
            return self._food_recipe(item)
        elif item.category in ('cosmetic', 'skincare'):
            return self._cosmetic_plan(item)
        elif item.category == 'medicine':
            return f"「{item.name}」即将过期，请检查是否需要补充"
        else:
            return f"「{item.name}」即将过期，建议尽快使用或处理"

    @staticmethod
    def _food_recipe(item: Item) -> str:
        """生成简易消耗食谱"""
        name = item.name.lower()
        recipes = {
            'egg': '简易食谱：番茄炒蛋、蒸蛋羹、鸡蛋三明治',
            'milk': '简易食谱：牛奶燕麦粥、奶昔、蒸蛋糕',
            'bread': '简易食谱：吐司披萨、面包布丁、法式吐司',
            'tomato': '简易食谱：番茄炒蛋、番茄汤、凉拌番茄',
            'potato': '简易食谱：土豆丝、烤土豆、土豆泥',
            'chicken': '简易食谱：白切鸡、鸡胸肉沙拉、鸡汤',
            'rice': '简易食谱：蛋炒饭、粥、饭团',
            'noodle': '简易食谱：拌面、汤面、炒面',
            'beef': '简易食谱：牛肉炒饭、红烧牛肉、牛肉汤',
            'pork': '简易食谱：红烧肉、炒肉丝、饺子馅',
        }
        for key, recipe in recipes.items():
            if key in name:
                return recipe
        return f"「{item.name}」建议尽快烹饪食用，避免浪费"

    @staticmethod
    def _cosmetic_plan(item: Item) -> str:
        """生成美妆使用规划"""
        name = item.name.lower()
        if '面膜' in name or 'mask' in name:
            return "面膜临期：建议每周敷2-3次加速使用，或用于颈膜/手膜"
        elif '精华' in name or 'serum' in name:
            return "精华临期：建议早晚使用，或混合面霜增强效果"
        elif '乳液' in name or 'lotion' in name:
            return "乳液临期：建议早晚使用，或作为身体乳使用"
        elif '防晒' in name or 'sunscreen' in name:
            return "防晒临期：建议每天出门前使用，全身涂抹不浪费"
        elif '口红' in name or 'lipstick' in name:
            return "口红临期：建议日常使用，或作为腮红点缀"
        elif '面霜' in name or 'cream' in name:
            return "面霜临期：建议早晚使用，或作为颈霜使用"
        return f"「{item.name}」临期，请尽快使用"

    # ==================== 闲置识别 ====================

    async def detect_idle_items(self) -> list[dict[str, Any]]:
        """检测闲置物品"""
        now = datetime.utcnow()
        threshold_date = now - timedelta(days=90)

        # 查找超过90天未使用的物品
        result = await self.session.execute(
            select(Item).where(
                and_(
                    Item.user_id == self.user_id,
                    Item.is_idle == False,
                    Item.category.in_(['food', 'cosmetic', 'medicine', 'other']),
                    Item.last_used_at < threshold_date,
                )
            )
        )

        alerts = []
        for item in result.scalars().all():
            item.is_idle = True
            idle_days = (now - (item.last_used_at or item.created_at)).days

            # 检查是否重复囤货
            duplicate_check = await self.session.execute(
                select(func.count(Item.id)).where(
                    and_(
                        Item.user_id == self.user_id,
                        Item.name == item.name,
                        Item.id != item.id,
                        Item.created_at < item.created_at,
                    )
                )
            )
            is_duplicate = duplicate_check.scalar() > 0

            if is_duplicate:
                alert_type = "duplicate_hoarding"
                message = f"「{item.name}」已闲置{idle_days}天，检测到重复囤货"
                suggestion = f"建议转手出售或赠送，当前库存{item.quantity}件"
            else:
                alert_type = "idle"
                message = f"「{item.name}」已闲置{idle_days}天"
                suggestion = f"建议清理或捐赠"

            # 创建提醒
            alert = ItemIdleAlert(
                user_id=self.user_id,
                item_id=item.id,
                alert_type=alert_type,
                message=message,
                suggestion=suggestion,
            )
            self.session.add(alert)
            alerts.append({
                "item_id": item.id,
                "name": item.name,
                "idle_days": idle_days,
                "alert_type": alert_type,
                "message": message,
                "suggestion": suggestion,
            })

        await self.session.flush()
        return alerts

    async def get_idle_alerts(self) -> list[ItemIdleAlert]:
        """获取闲置提醒"""
        result = await self.session.execute(
            select(ItemIdleAlert).where(
                and_(ItemIdleAlert.user_id == self.user_id, ItemIdleAlert.is_read == False)
            ).order_by(ItemIdleAlert.created_at.desc())
        )
        return list(result.scalars().all())

    # ==================== 综合报告 ====================

    async def get_item_summary(self) -> dict[str, Any]:
        """获取物品总览"""
        now = datetime.utcnow()

        # 总物品数
        total = await self.session.scalar(
            select(func.count(Item.id)).where(Item.user_id == self.user_id)
        )

        # 即将过期（15天内）
        expiring_15d = await self.session.scalar(
            select(func.count(Item.id)).where(
                and_(
                    Item.user_id == self.user_id,
                    Item.expire_at != None,
                    Item.expire_at >= now,
                    Item.expire_at <= now + timedelta(days=15),
                )
            )
        )

        # 即将过期（7天内）
        expiring_7d = await self.session.scalar(
            select(func.count(Item.id)).where(
                and_(
                    Item.user_id == self.user_id,
                    Item.expire_at != None,
                    Item.expire_at >= now,
                    Item.expire_at <= now + timedelta(days=7),
                )
            )
        )

        # 已过期
        expired = await self.session.scalar(
            select(func.count(Item.id)).where(
                and_(
                    Item.user_id == self.user_id,
                    Item.expire_at != None,
                    Item.expire_at < now,
                )
            )
        )

        # 闲置物品
        idle = await self.session.scalar(
            select(func.count(Item.id)).where(
                and_(Item.user_id == self.user_id, Item.is_idle == True)
            )
        )

        # 分类统计
        cat_result = await self.session.execute(
            select(Item.category, func.count(Item.id)).where(
                Item.user_id == self.user_id
            ).group_by(Item.category)
        )
        categories = {row[0]: row[1] for row in cat_result.all()}

        return {
            "total": total,
            "expiring_15d": expiring_15d,
            "expiring_7d": expiring_7d,
            "expired": expired,
            "idle": idle,
            "categories": categories,
        }
