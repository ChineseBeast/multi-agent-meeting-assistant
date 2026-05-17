"""
会议助手系统的数据库持久化层。

提供异步 SQLAlchemy ORM 模型、引擎管理和所有 CRUD 操作的仓库层。
默认使用 SQLite（文件存储，无外部依赖），
可通过 DATABASE_URL 环境变量切换为 PostgreSQL。

用法：
    from ..database import init_database, get_repository

    # 启动时
    await init_database()

    # 在请求处理中
    repo = await get_repository()
    await repo.create_meeting(...)
"""

from .engine import init_database, get_session, close_database, get_repository_sync
from .models import (
    MeetingRecord,
    TranscriptSegmentRecord,
    TopicRecord,
    ActionItemRecord,
    SpeakerStatRecord,
    InsightRecord,
    FollowUpRecord,
)
from .repository import MeetingRepository

__all__ = [
    "init_database",
    "get_session",
    "close_database",
    "get_repository_sync",
    "MeetingRepository",
    "MeetingRecord",
    "TranscriptSegmentRecord",
    "TopicRecord",
    "ActionItemRecord",
    "SpeakerStatRecord",
    "InsightRecord",
    "FollowUpRecord",
]
