"""计算工具"""
from langchain_core.tools import tool


@tool
def calc_tool(expression: str) -> str:
    """执行数学计算。输入数学表达式（如：100*0.85+50、(5000-3000)/30）。"""
    try:
        # 安全计算（仅限数学运算）
        allowed_chars = set("0123456789+-*/().^ %")
        if not all(c in allowed_chars for c in expression.replace(" ", "")):
            return "错误：表达式包含非法字符"
        result = eval(expression.replace("^", "**"))
        return f"计算结果: {expression} = {result}"
    except Exception as e:
        return f"计算错误: {e}"
