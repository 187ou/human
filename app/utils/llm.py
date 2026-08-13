"""LLM客户端封装（OpenAI兼容）"""
from functools import lru_cache

from langchain_openai import ChatOpenAI

from app.config import settings


@lru_cache(maxsize=1)
def get_llm() -> ChatOpenAI:
    """获取默认LLM实例"""
    return ChatOpenAI(
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        model=settings.LLM_MODEL,
        temperature=settings.LLM_TEMPERATURE,
    )


def get_llm_with_temp(temperature: float) -> ChatOpenAI:
    """指定温度的LLM（演化层需要更高创造性）"""
    return ChatOpenAI(
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        model=settings.LLM_MODEL,
        temperature=temperature,
    )
