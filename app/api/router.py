"""API路由汇总"""
from fastapi import APIRouter

from app.api import auth, schedules, consumes, items, studies, travels, agent, evolution, stats, schedule_nlp, scenarios, notifications, nlp, vectors

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["用户认证"])
api_router.include_router(schedules.router, prefix="/schedules", tags=["时间规划"])
api_router.include_router(consumes.router, prefix="/consumes", tags=["消费记账"])
api_router.include_router(items.router, prefix="/items", tags=["物品收纳"])
api_router.include_router(studies.router, prefix="/studies", tags=["学习督导"])
api_router.include_router(travels.router, prefix="/travels", tags=["出行处理"])
api_router.include_router(agent.router, prefix="/agent", tags=["Agent对话"])
api_router.include_router(evolution.router, prefix="/evolution", tags=["自适应演化"])
api_router.include_router(stats.router, prefix="/stats", tags=["数据统计"])
api_router.include_router(schedule_nlp.router, prefix="/schedule-nlp", tags=["自然语言日程"])
api_router.include_router(scenarios.router, prefix="/scenarios", tags=["跨Agent场景联动"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["消息推送"])
api_router.include_router(nlp.router, prefix="/nlp", tags=["自然语言解析"])
api_router.include_router(vectors.router, prefix="/vectors", tags=["向量存储"])
