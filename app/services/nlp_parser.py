"""增强版NLP解析器：支持复杂周期性计划语句拆解"""
import json
import re
from datetime import datetime, timedelta
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.utils.llm import get_llm


SYSTEM_PROMPT = """你是一个智能生活助手解析器。将用户的自然语言输入解析为结构化指令。

支持的指令类型：
1. create_schedule - 创建日程
2. create_recurring_schedule - 创建周期性日程
3. record_consume - 记账
4. create_item - 添加物品
5. record_study - 记录学习
6. review_consume - 消费复盘
7. query - 查询信息
8. scenario - 触发场景联动

输出格式（纯JSON）：
{
  "type": "指令类型",
  "params": {参数键值对},
  "confidence": 0.95,
  "original_text": "原始输入"
}

示例：
输入："每天早上8点跑步30分钟，除了周日"
输出：{"type": "create_recurring_schedule", "params": {"title": "跑步", "category": "sport", "start_time": "08:00", "duration_minutes": 30, "days_of_week": [0,1,2,3,4,5], "skip_days": [6]}, "confidence": 0.95, "original_text": "每天早上8点跑步30分钟，除了周日"}

输入："记一笔35块的外卖"
输出：{"type": "record_consume", "params": {"amount": 35, "category": "food", "merchant": "外卖"}, "confidence": 0.95, "original_text": "记一笔35块的外卖"}

输入："下个月1号去杭州玩3天，预算2000"
输出：{"type": "scenario", "params": {"scenario": "trip", "destination": "杭州", "depart_time": "2026-09-01", "arrive_time": "2026-09-03", "budget": 2000}, "confidence": 0.9, "original_text": "下个月1号去杭州玩3天，预算2000"}

输入："每周一三五晚上7点到9点学习高数"
输出：{"type": "create_recurring_schedule", "params": {"title": "学习高数", "category": "study", "start_time": "19:00", "end_time": "21:00", "days_of_week": [0,2,4]}, "confidence": 0.95, "original_text": "每周一三五晚上7点到9点学习高数"}

输入："这个月花了多少钱"
输出：{"type": "query", "params": {"query_type": "consume_summary"}, "confidence": 0.9, "original_text": "这个月花了多少钱"}

输入："感冒了，休息3天"
输出：{"type": "scenario", "params": {"scenario": "sick_rest", "rest_days": 3, "symptoms": "感冒"}, "confidence": 0.9, "original_text": "感冒了，休息3天"}

输入："9月1号前要考完数学，每天学6小时"
输出：{"type": "scenario", "params": {"scenario": "exam_prep", "subject": "数学", "exam_date": "2026-09-01", "daily_hours": 6}, "confidence": 0.9, "original_text": "9月1号前要考完数学，每天学6小时"}

只输出JSON，不要其他内容。
"""


class NLPParser:
    """增强版NLP解析器"""

    def __init__(self):
        self.llm = get_llm()

    async def parse(self, text: str) -> dict[str, Any]:
        """解析自然语言输入（优先规则，LLM增强）"""
        # 先尝试规则解析（快速、不依赖LLM）
        rule_result = self._rule_based_parse(text)
        if rule_result.get("confidence", 0) >= 0.6:
            return rule_result

        # 规则不确定时，尝试LLM解析
        try:
            messages = [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=text),
            ]
            result = self.llm.invoke(messages)
            response_text = result.content.strip()

            if "```" in response_text:
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            parsed = json.loads(response_text)
            return parsed
        except Exception:
            return rule_result

    def _rule_based_parse(self, text: str) -> dict[str, Any]:
        """基于规则的快速解析（LLM失败时的降级方案）"""
        text = text.strip()

        # 记账模式
        consume_patterns = [
            r'记[一笔]*(.*?)(\d+\.?\d*)\s*块',
            r'花了(\d+\.?\d*)',
            r'消费(\d+\.?\d*)',
            r'(\d+\.?\d*)\s*元[的]*(.+)',
        ]
        for pattern in consume_patterns:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                if len(groups) >= 2:
                    if groups[0].replace('.', '').isdigit():
                        amount = float(groups[0])
                        desc = groups[1] if len(groups) > 1 else ''
                    else:
                        amount = float(groups[1])
                        desc = groups[0]
                    return {
                        "type": "record_consume",
                        "params": {"amount": amount, "category": self._guess_category(desc), "description": desc},
                        "confidence": 0.7,
                        "original_text": text,
                    }

        # 日程模式
        schedule_patterns = [
            r'(.+?)(\d{1,2})[点:](\d{0,2})[到至-](\d{1,2})[点:](\d{0,2})',
            r'(.+?)(\d{1,2})[点:](\d{0,2})开始',
        ]
        for pattern in schedule_patterns:
            match = re.search(pattern, text)
            if match:
                return {
                    "type": "create_schedule",
                    "params": {"title": match.group(1).strip(), "time": match.group(2)},
                    "confidence": 0.6,
                    "original_text": text,
                }

        # 默认返回查询
        return {
            "type": "query",
            "params": {"query_type": "general", "text": text},
            "confidence": 0.3,
            "original_text": text,
        }

    @staticmethod
    def _guess_category(desc: str) -> str:
        """猜测消费品类"""
        desc = desc.lower()
        if any(w in desc for w in ['饭', '餐', '食', '吃', '外卖', '奶茶', '咖啡']):
            return 'food'
        elif any(w in desc for w in ['买', '购', '淘宝', '京东', '拼多多']):
            return 'shopping'
        elif any(w in desc for w in ['车', '地铁', '打车', '油', '交通']):
            return 'transport'
        elif any(w in desc for w in ['电影', '游戏', '玩', '娱乐']):
            return 'entertainment'
        return 'other'


# 快捷指令模板
QUICK_COMMANDS = [
    {
        "id": "record_consume",
        "icon": "💰",
        "label": "记一笔",
        "template": "记一笔{amount}块的{category}",
        "example": "记一笔35块的外卖",
        "type": "record_consume",
    },
    {
        "id": "create_schedule",
        "icon": "📅",
        "label": "新建日程",
        "template": "{time}做{title}",
        "example": "明天下午2点开组会",
        "type": "create_schedule",
    },
    {
        "id": "review_consume",
        "icon": "📊",
        "label": "消费复盘",
        "template": "这个月花了多少钱",
        "example": "这个月花了多少钱",
        "type": "review_consume",
    },
    {
        "id": "add_item",
        "icon": "📦",
        "label": "添加物品",
        "template": "添加{item}到{location}",
        "example": "添加牛奶到冰箱",
        "type": "create_item",
    },
    {
        "id": "record_study",
        "icon": "📚",
        "label": "学习记录",
        "template": "学了{subject}{duration}分钟",
        "example": "学了数学60分钟",
        "type": "record_study",
    },
    {
        "id": "trip_plan",
        "icon": "🏖️",
        "label": "出游计划",
        "template": "去{destination}{days}天",
        "example": "去杭州玩3天",
        "type": "scenario",
    },
    {
        "id": "exam_prep",
        "icon": "📝",
        "label": "备考冲刺",
        "template": "{subject}考试{exam_date}",
        "example": "数学考试9月1号",
        "type": "scenario",
    },
    {
        "id": "sick_rest",
        "icon": "🤒",
        "label": "生病休息",
        "template": "生病了休息{days}天",
        "example": "感冒了休息3天",
        "type": "scenario",
    },
]
