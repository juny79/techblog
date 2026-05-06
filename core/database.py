from __future__ import annotations

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Text, Float, Integer, DateTime, JSON, Boolean
from datetime import datetime

from core.config import settings


# ─── Base ──────────────────────────────────────────────────────────────────────


class Base(DeclarativeBase):
    pass


# ─── ORM Models ────────────────────────────────────────────────────────────────


class PostRecord(Base):
    __tablename__ = "posts"

    post_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    topic_title: Mapped[str] = mapped_column(String(512), nullable=False)
    title: Mapped[str] = mapped_column(String(512), default="")
    pipeline_status: Mapped[str] = mapped_column(String(64), default="idle")
    tistory_post_id: Mapped[str] = mapped_column(String(64), default="")
    published_url: Mapped[str] = mapped_column(String(1024), default="")
    retry_counts: Mapped[dict] = mapped_column(JSON, default=dict)
    content_markdown: Mapped[str] = mapped_column(Text, default="")
    seo_tags: Mapped[str] = mapped_column(Text, default="")
    seo_score: Mapped[float] = mapped_column(Float, default=0.0)
    quality_score: Mapped[float] = mapped_column(Float, default=0.0)
    quality_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AnalyticsRecord(Base):
    __tablename__ = "analytics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    post_id: Mapped[str] = mapped_column(String(36), nullable=False)
    tistory_post_id: Mapped[str] = mapped_column(String(64), nullable=False)
    views: Mapped[int] = mapped_column(Integer, default=0)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    comments: Mapped[int] = mapped_column(Integer, default=0)
    search_impressions: Mapped[int] = mapped_column(Integer, default=0)
    search_clicks: Mapped[int] = mapped_column(Integer, default=0)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class HumanReviewRecord(Base):
    __tablename__ = "human_review_queue"

    post_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    topic_title: Mapped[str] = mapped_column(String(512), nullable=False)
    issues: Mapped[str] = mapped_column(Text, default="")
    draft_json: Mapped[dict] = mapped_column(JSON, default=dict)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    queued_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ─── Engine & Session Factory ──────────────────────────────────────────────────


engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_size=5,
    max_overflow=10,
)

AsyncSessionFactory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    """Create all tables if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    async with AsyncSessionFactory() as session:
        yield session
