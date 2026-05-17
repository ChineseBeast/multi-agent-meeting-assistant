"""
数据库引擎和会话管理。

使用 SQLAlchemy 2.0 异步 API。默认后端为 SQLite（通过 aiosqlite），
零外部依赖，适合办公笔记本。
设置 DATABASE_URL=postgresql://user:pass@host/db 即可使用 PostgreSQL。

默认数据库文件创建在项目根目录下的 'meetings.db'。
"""

from __future__ import annotations

import os
from pathlib import Path

from loguru import logger
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .models import Base

# ---- 模块级状态（懒初始化） ----
_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _resolve_db_url() -> str:
    """返回异步数据库连接 URL。

    优先级：
    1. DATABASE_URL 环境变量（必须是 postgresql:// 格式的 URL）
    2. 默认 SQLite 文件，位于项目根目录 / 'meetings.db'
    """
    raw = os.getenv("DATABASE_URL", "").strip()
    if raw:
        # 将标准 postgresql:// 转换为异步格式 postgresql+asyncpg://
        if raw.startswith("postgresql://") and "+" not in raw:
            raw = raw.replace("postgresql://", "postgresql+asyncpg://")
        logger.info("Using configured database: {}", raw)
        return raw

    # 默认：python/ 目录下的 SQLite 文件
    db_dir = Path(__file__).resolve().parent.parent.parent
    db_path = db_dir / "meetings.db"
    url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    logger.info("Using default SQLite database: {}", db_path)
    return url


async def init_database():
    """创建引擎、会话工厂和所有表。

    在服务器启动时调用一次（幂等）。
    """
    global _engine, _session_factory

    url = _resolve_db_url()
    _engine = create_async_engine(url, echo=False, future=True)

    # 创建所有表
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    _session_factory = async_sessionmaker(
        _engine, class_=AsyncSession, expire_on_commit=False
    )

    logger.info("Database tables created / verified successfully")


async def get_session() -> AsyncSession:
    """获取一个新的异步会话（兼容上下文管理器）。

    用法：
        session = await get_session()
        try:
            ...
        finally:
            await session.close()
    """
    if _session_factory is None:
        await init_database()
    return _session_factory()


def get_session_factory():
    """返回底层的 async_sessionmaker，供仓库层使用。"""
    return _session_factory


def get_repository_sync():
    """同步获取器——实际的异步 session 在每个 repo 方法内部创建。

    返回一个 MeetingRepository 实例，该实例在内部创建 session。
    这样避免了 FastAPI 与我们的 session 生命周期耦合。
    """
    from .repository import MeetingRepository

    return MeetingRepository()


async def close_database():
    """释放数据库引擎（在关闭时调用）。"""
    global _engine, _session_factory
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("Database engine disposed")
