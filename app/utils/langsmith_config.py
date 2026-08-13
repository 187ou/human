"""LangSmith 链路追踪配置"""
import os
from loguru import logger

LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY", "")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "human-agent")
LANGSMITH_TRACING = os.getenv("LANGSMITH_TRACING", "false").lower() == "true"

if LANGSMITH_TRACING and LANGSMITH_API_KEY:
    os.environ["LANGSMITH_API_KEY"] = LANGSMITH_API_KEY
    os.environ["LANGSMITH_PROJECT"] = LANGSMITH_PROJECT
    os.environ["LANGSMITH_TRACING_V2"] = "true"
    logger.info(f"[LangSmith] 已启用追踪，项目: {LANGSMITH_PROJECT}")
else:
    logger.info("[LangSmith] 追踪未启用（设置 LANGSMITH_API_KEY 和 LANGSMITH_TRACING=true 启用）")


def get_trace_config(run_name: str, metadata: dict | None = None) -> dict:
    """获取追踪配置"""
    if not LANGSMITH_TRACING:
        return {}
    return {
        "run_name": run_name,
        "metadata": {
            "project": LANGSMITH_PROJECT,
            **(metadata or {}),
        },
        "tags": ["human-agent", run_name],
    }


def trace_run(run_name: str):
    """追踪装饰器（条件启用）"""
    def decorator(func):
        if not LANGSMITH_TRACING:
            return func

        from langsmith.run_helpers import traceable
        return traceable(name=run_name, tags=["human-agent"])(func)
    return decorator
