"""
所有会议数据实体的 SQLAlchemy 2.0 ORM 模型。

每个模型与 models/schemas.py 中的 Pydantic schema 一一对应。
使用传统的 ``declarative_base`` 以保持简单性和兼容性。

所有列表/字典字段以 JSON TEXT 列存储，因为 SQLite
没有原生的 ARRAY/JSONB 支持。PostgreSQL 用户可以在后续添加 JSONB 迁移。
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


# ── 辅助函数 ───────────────────────────────────────────────


def _json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── MeetingRecord（表 1）─────────────────────────────────


class MeetingRecord(Base):
    """核心会议会话记录——每次会议一行。"""

    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    meeting_id = Column(String(64), unique=True, nullable=False, index=True)

    # Bot 配置
    platform = Column(String(32), default="")
    meeting_url = Column(Text, default="")
    account = Column(String(128), default="")

    # 状态追踪
    status = Column(String(32), default="created")  # MeetingStatus 枚举值
    bot_status = Column(String(32), default="")
    bot_mode = Column(String(32), default="simulation")
    error_message = Column(Text, default="")

    # 转写摘要（为加速读取而反范式化）
    transcript_language = Column(String(8), default="")
    transcript_duration = Column(Float, default=0.0)
    transcript_full_text = Column(Text, default="")

    # 纪要摘要（反范式化）
    summary_title = Column(String(256), default="")
    summary_date = Column(String(32), default="")
    summary_participants = Column(Text, default="[]")  # JSON 列表
    summary_decisions = Column(Text, default="[]")
    summary_next_steps = Column(Text, default="[]")

    # 时间戳
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    # 关联关系（通过关联查询加载）
    transcript_segments = relationship(
        "TranscriptSegmentRecord", back_populates="meeting",
        cascade="all, delete-orphan", lazy="selectin",
    )
    topics = relationship(
        "TopicRecord", back_populates="meeting",
        cascade="all, delete-orphan", lazy="selectin",
    )
    action_items = relationship(
        "ActionItemRecord", back_populates="meeting",
        cascade="all, delete-orphan", lazy="selectin",
    )
    speaker_stats = relationship(
        "SpeakerStatRecord", back_populates="meeting",
        cascade="all, delete-orphan", lazy="selectin",
    )
    insight = relationship(
        "InsightRecord", back_populates="meeting",
        uselist=False, lazy="selectin",
    )
    followup = relationship(
        "FollowUpRecord", back_populates="meeting",
        uselist=False, lazy="selectin",
    )

    def to_dict(self) -> dict:
        return {
            "meeting_id": self.meeting_id,
            "platform": self.platform,
            "meeting_url": self.meeting_url,
            "status": self.status,
            "bot_status": self.bot_status,
            "bot_mode": self.bot_mode,
            "error_message": self.error_message,
            "transcript_language": self.transcript_language,
            "transcript_duration": self.transcript_duration,
            "transcript_full_text": self.transcript_full_text,
            "summary_title": self.summary_title,
            "summary_date": self.summary_date,
            "summary_participants": json.loads(self.summary_participants or "[]"),
            "summary_decisions": json.loads(self.summary_decisions or "[]"),
            "summary_next_steps": json.loads(self.summary_next_steps or "[]"),
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "updated_at": self.updated_at.isoformat() if self.updated_at else "",
        }


# ── TranscriptSegmentRecord（表 2）───────────────────────


class TranscriptSegmentRecord(Base):
    """单个转写的句子/话语。"""

    __tablename__ = "transcript_segments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    meeting_id = Column(
        String(64),
        ForeignKey("meetings.meeting_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    speaker = Column(String(128), default="Unknown")
    text = Column(Text, default="")
    start_time = Column(Float, default=0.0)
    end_time = Column(Float, default=0.0)
    confidence = Column(Float, default=0.0)
    segment_index = Column(Integer, default=0)

    meeting = relationship("MeetingRecord", back_populates="transcript_segments")

    def to_dict(self) -> dict:
        return {
            "speaker": self.speaker,
            "text": self.text,
            "start": self.start_time,
            "end": self.end_time,
            "confidence": self.confidence,
        }


# ── TopicRecord（表 3）───────────────────────────────────


class TopicRecord(Base):
    """会议纪要中的一个议题/议程项。"""

    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    meeting_id = Column(
        String(64),
        ForeignKey("meetings.meeting_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(256), default="")
    discussion_points = Column(Text, default="[]")  # JSON 列表
    participants = Column(Text, default="[]")  # JSON 列表
    conclusion = Column(Text, default="")

    meeting = relationship("MeetingRecord", back_populates="topics")

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "discussion_points": json.loads(self.discussion_points or "[]"),
            "participants": json.loads(self.participants or "[]"),
            "conclusion": self.conclusion,
        }


# ── ActionItemRecord（表 4）──────────────────────────────


class ActionItemRecord(Base):
    """一条提取的待办事项。"""

    __tablename__ = "action_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    meeting_id = Column(
        String(64),
        ForeignKey("meetings.meeting_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assignee = Column(String(128), default="")
    task = Column(Text, default="")
    deadline = Column(String(32), default="")
    priority = Column(String(16), default="medium")
    context = Column(Text, default="")
    jira_issue_key = Column(String(32), default="")
    feishu_task_id = Column(String(64), default="")

    meeting = relationship("MeetingRecord", back_populates="action_items")

    def to_dict(self) -> dict:
        return {
            "assignee": self.assignee,
            "task": self.task,
            "deadline": self.deadline,
            "priority": self.priority,
            "context": self.context,
            "jira_issue_key": self.jira_issue_key,
            "feishu_task_id": self.feishu_task_id,
        }


# ── SpeakerStatRecord（表 5）─────────────────────────────


class SpeakerStatRecord(Base):
    """会议中每个说话人的统计数据。"""

    __tablename__ = "speaker_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    meeting_id = Column(
        String(64),
        ForeignKey("meetings.meeting_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    speaker = Column(String(128), default="")
    speaking_duration = Column(Float, default=0.0)
    speaking_ratio = Column(Float, default=0.0)
    word_count = Column(Integer, default=0)
    segment_count = Column(Integer, default=0)

    meeting = relationship("MeetingRecord", back_populates="speaker_stats")

    def to_dict(self) -> dict:
        return {
            "speaker": self.speaker,
            "speaking_duration": self.speaking_duration,
            "speaking_ratio": self.speaking_ratio,
            "word_count": self.word_count,
            "segment_count": self.segment_count,
        }


# ── InsightRecord（表 6）─────────────────────────────────


class InsightRecord(Base):
    """会议分析/洞察行（每次会议一条）。"""

    __tablename__ = "insights"

    id = Column(Integer, primary_key=True, autoincrement=True)
    meeting_id = Column(
        String(64),
        ForeignKey("meetings.meeting_id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    overall_sentiment = Column(String(16), default="neutral")
    sentiment_score = Column(Float, default=0.5)
    efficiency_score = Column(Float, default=5.0)
    keywords = Column(Text, default="[]")  # JSON 列表
    highlights = Column(Text, default="[]")  # JSON 列表
    suggestions = Column(Text, default="[]")  # JSON 列表

    meeting = relationship("MeetingRecord", back_populates="insight")

    def to_dict(self) -> dict:
        return {
            "overall_sentiment": self.overall_sentiment,
            "sentiment_score": self.sentiment_score,
            "efficiency_score": self.efficiency_score,
            "keywords": json.loads(self.keywords or "[]"),
            "highlights": json.loads(self.highlights or "[]"),
            "suggestions": json.loads(self.suggestions or "[]"),
        }


# ── FollowUpRecord（表 7）────────────────────────────────


class FollowUpRecord(Base):
    """跟进执行结果（每次会议一条）。"""

    __tablename__ = "followups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    meeting_id = Column(
        String(64),
        ForeignKey("meetings.meeting_id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    summary_sent = Column(Boolean, default=False)
    recipients = Column(Text, default="[]")  # JSON 列表
    jira_issues_created = Column(Text, default="[]")  # JSON 列表
    feishu_tasks_created = Column(Text, default="[]")  # JSON 列表
    reminders_scheduled = Column(Integer, default=0)
    report_url = Column(Text, default="")

    meeting = relationship("MeetingRecord", back_populates="followup")

    def to_dict(self) -> dict:
        return {
            "summary_sent": self.summary_sent,
            "recipients": json.loads(self.recipients or "[]"),
            "jira_issues_created": json.loads(self.jira_issues_created or "[]"),
            "feishu_tasks_created": json.loads(self.feishu_tasks_created or "[]"),
            "reminders_scheduled": self.reminders_scheduled,
            "report_url": self.report_url,
        }
