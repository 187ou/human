"""消费记账工具集"""
from typing import Any


CATEGORY_KEYWORDS = {
    "food": ["餐", "饭", "外卖", "奶茶", "咖啡", "零食", "水果", "超市"],
    "shopping": ["买", "购", "淘宝", "京东", "拼多多", "衣服", "鞋"],
    "transport": ["打车", "地铁", "公交", "加油", "滴滴", "高铁"],
    "entertainment": ["电影", "游戏", "会员", "KTV", "娱乐", "皮肤"],
    "study": ["书", "课", "培训", "考试", "资料"],
    "rent": ["房租", "水电", "物业", "网费"],
}


class ConsumeTools:
    def __init__(self, user_id: int, user_rules: dict[str, Any]):
        self.user_id = user_id
        self.rules = user_rules.get("consume", {})
        self.budget_limits = self.rules.get("budget_limits", {})

    def classify(self, description: str) -> str:
        """分类消费"""
        for cat, kws in CATEGORY_KEYWORDS.items():
            if any(kw in description for kw in kws):
                return cat
        return "other"

    def detect_impulse(self, amount: float, category: str, history_avg: float) -> bool:
        """识别冲动消费"""
        threshold = self.budget_limits.get(category, {}).get("impulse_threshold", history_avg * 1.5)
        return amount > threshold

    def calculate_waste(self, records: list[dict]) -> dict[str, Any]:
        """统计浪费"""
        waste_items = [r for r in records if r.get("is_waste") or r.get("is_impulse")]
        total_waste = sum(r["amount"] for r in waste_items)
        return {
            "waste_count": len(waste_items),
            "total_waste": total_waste,
            "top_waste_category": max(
                set(r["category"] for r in waste_items),
                key=lambda c: sum(r["amount"] for r in waste_items if r["category"] == c),
                default=None,
            ) if waste_items else None,
        }

    def suggest_savings(self, category: str, overspent: float) -> list[str]:
        """省钱建议"""
        suggestions = {
            "food": ["自带午餐", "减少外卖至每周2次", "用团购券"],
            "shopping": ["加入购物车冷静48小时", "优先使用闲置物品"],
            "entertainment": ["取消不常用会员", "选择免费替代活动"],
        }
        base = suggestions.get(category, ["审视该品类必要性"])
        return [f"本月已超支{overspent:.0f}元，建议："] + base

    def dynamic_budget(self, monthly_income: float, category: str, history_avg: float) -> float:
        """动态预算计算"""
        # 基础比例
        base_ratio = self.budget_limits.get(category, {}).get("ratio", 0.15)
        suggested = monthly_income * base_ratio
        # 结合历史平均微调
        return round((suggested + history_avg) / 2, 2)
