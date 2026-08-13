"""应用配置"""
import os
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "HumanAgent"
    APP_ENV: str = "dev"
    DEBUG: bool = True

    # 服务
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # 数据库 (默认SQLite本地开发，生产用PostgreSQL)
    DATABASE_URL: str = f"sqlite+aiosqlite:///{_PROJECT_DIR}/human_agent.db"

    # LLM (OpenAI兼容)
    LLM_API_KEY: str = "sk-placeholder"
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_TEMPERATURE: float = 0.3

    # 演化层配置
    EVOLUTION_INTERVAL_HOURS: int = 24  # 演化周期
    BEHAVIOR_RETENTION_DAYS: int = 90   # 行为数据保留天数
    RULE_MIN_SAMPLES: int = 7           # 规则挖掘最小样本数

    # 向量库
    VECTOR_DIMENSION: int = 1536


settings = Settings()
