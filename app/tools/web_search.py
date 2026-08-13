"""网络搜索工具"""
from langchain_core.tools import tool


@tool
def search_tool(query: str) -> str:
    """搜索互联网信息。输入搜索关键词，返回搜索结果摘要。"""
    return (
        f"搜索查询: {query}\n"
        f"（注：当前为占位实现，生产环境请接入真实搜索API如 Tavily/SerpAPI）\n"
        f"建议接入方式：\n"
        f"1. Tavily API - 专为AI Agent优化的搜索\n"
        f"2. SerpAPI - Google搜索代理\n"
        f"3. Bing Search API - 微软搜索"
    )
