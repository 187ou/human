"""天气查询工具"""
from langchain_core.tools import tool


@tool
def weather_tool(city: str) -> str:
    """查询指定城市的实时天气和预报。输入城市名称（如：北京、上海、杭州）。"""
    import random
    conditions = ["晴", "多云", "阴", "小雨", "中雨", "大雨", "雪"]
    condition = random.choice(conditions)
    temp = random.randint(-5, 35)
    humidity = random.randint(30, 90)
    wind = random.choice(["北风", "南风", "东风", "西风"]) + f"{random.randint(1, 5)}级"

    return (
        f"城市: {city}\n"
        f"天气: {condition}\n"
        f"温度: {temp}°C\n"
        f"湿度: {humidity}%\n"
        f"风力: {wind}\n"
        f"（注：当前为模拟数据，生产环境请接入真实天气API）"
    )
