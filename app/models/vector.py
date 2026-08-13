"""向量数据模型：仅存储用户偏好和历史对话向量"""
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class UserPreferenceVector(Base):
    """用户偏好向量（用于个性化召回）"""
    __tablename__ = "user_preference_vectors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # 偏好维度
    dimension: Mapped[str] = mapped_column(String(30))  # schedule / consume / study / travel / item
    # 偏好描述文本
    description: Mapped[str] = mapped_column(Text)
    # 向量嵌入（JSON格式，兼容SQLite）
    embedding: Mapped[list] = mapped_column(JSON, default=list)

    # 元数据
    source: Mapped[str] = mapped_column(String(20), default="auto")  # auto / manual
    relevance_score: Mapped[float] = mapped_column(Float, default=1.0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ConversationVector(Base):
    """历史对话向量（用于上下文召回）"""
    __tablename__ = "conversation_vectors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # 对话摘要
    summary: Mapped[str] = mapped_column(Text)
    # 向量嵌入
    embedding: Mapped[list] = mapped_column(JSON, default=list)

    # 关联信息
    intent_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
