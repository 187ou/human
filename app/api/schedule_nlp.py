"""自然语言录入周期性例外日程"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, get_current_user
from app.models.user import User
from app.utils.llm import get_llm

router = APIRouter()


class NLParseRequest(BaseModel):
    text: str


SYSTEM_PROMPT = """你是一个日程解析助手。将用户的自然语言描述转换为周期性例外日程的JSON规则。

输出格式（纯JSON，不要其他内容）：
{"days_of_week": [1,2,3,4,5], "start_time": "19:00", "end_time": "21:00", "action": "add"}

说明：
- days_of_week: 星期几，0=周一，1=周二，...，6=周日
- start_time / end_time: HH:MM 格式
- action: "add"（添加日程）/ "pause"（暂停当天日程）/ "skip"（跳过当天某类日程）

示例：
输入："周一至周五晚间学习"
输出：{"days_of_week": [0,1,2,3,4], "start_time": "19:00", "end_time": "21:00", "action": "add"}

输入："周三晚上聚餐，暂停学习计划"
输出：{"days_of_week": [2], "start_time": "18:00", "end_time": "21:00", "action": "pause"}

输入："周末不安排学习"
输出：{"days_of_week": [5,6], "start_time": "00:00", "end_time": "23:59", "action": "skip"}
"""


@router.post("/parse")
async def parse_natural_language(
    data: NLParseRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """自然语言解析为例期规则JSON"""
    from langchain_core.messages import HumanMessage, SystemMessage

    llm = get_llm()
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=data.text),
    ]
    result = llm.invoke(messages)
    response_text = result.content.strip()

    # 尝试解析JSON
    import json
    try:
        # 提取JSON部分
        if "```" in response_text:
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        rule = json.loads(response_text)
        return {"code": 0, "data": rule}
    except json.JSONDecodeError:
        return {"code": 1, "message": "解析失败", "raw": response_text}
