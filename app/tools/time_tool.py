"""时间查询工具"""
from datetime import datetime, timedelta

from langchain_core.tools import tool


@tool
def time_tool(query: str) -> str:
    """查询时间相关信息。支持：现在、今天、明天、昨天、本周、本月、X天后、X天前。"""
    now = datetime.now()

    query = query.strip().lower()
    if query in ["现在", "当前时间", "几点"]:
        return f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')} 星期{['一','二','三','四','五','六','日'][now.weekday()]}"
    elif query in ["今天", "今日"]:
        return f"今天: {now.strftime('%Y-%m-%d')} 星期{['一','二','三','四','五','六','日'][now.weekday()]}"
    elif query in ["明天", "明日"]:
        t = now + timedelta(days=1)
        return f"明天: {t.strftime('%Y-%m-%d')} 星期{['一','二','三','四','五','六','日'][t.weekday()]}"
    elif query in ["昨天", "昨日"]:
        t = now - timedelta(days=1)
        return f"昨天: {t.strftime('%Y-%m-%d')} 星期{['一','二','三','四','五','六','日'][t.weekday()]}"
    elif query in ["本周"]:
        start = now - timedelta(days=now.weekday())
        end = start + timedelta(days=6)
        return f"本周: {start.strftime('%m/%d')} - {end.strftime('%m/%d')}"
    elif query in ["本月"]:
        return f"本月: {now.strftime('%Y年%m月')} 共{now.day}天已过"
    elif "天后" in query:
        try:
            days = int(''.join(filter(str.isdigit, query)))
            t = now + timedelta(days=days)
            return f"{days}天后: {t.strftime('%Y-%m-%d')} 星期{['一','二','三','四','五','六','日'][t.weekday()]}"
        except ValueError:
            return "无法解析天数"
    elif "天前" in query:
        try:
            days = int(''.join(filter(str.isdigit, query)))
            t = now - timedelta(days=days)
            return f"{days}天前: {t.strftime('%Y-%m-%d')} 星期{['一','二','三','四','五','六','日'][t.weekday()]}"
        except ValueError:
            return "无法解析天数"
    else:
        return f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}"
