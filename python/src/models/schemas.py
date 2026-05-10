"""
数据模型定义（Pydantic Schemas）

对照 Go 版 internal/model/types.go 和 Java 版 model 包，
为 Python 版提供一致的数据结构。

面试考点:
- 为什么用 Pydantic 而不是 dataclass？（序列化/验证/文档生成）
- BaseModel 和 TypedDict 在 LangGraph 中的使用场景？
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ============================================================
# 枚举类型
# ============================================================


class MeetingStatus(str, Enum):
    """会议处理状态"""
    CREATED = "created"
    TRANSCRIBING = "transcribing"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Priority(str, Enum):
    """待办优先级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class SentimentType(str, Enum):
    """情感分析类型"""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


# ============================================================
# 转写相关 (Transcription)
# ============================================================


class TranscriptSegment(BaseModel):
    """单条转写片段

    对应: Go TranscriptSegment / Java TranscriptSegment
    """
    speaker: str = "Unknown"
    text: str = ""
    start: float = 0.0
    end: float = 0.0
    confidence: float = 0.0


class TranscriptResult(BaseModel):
    """转写结果

    对应: Go []TranscriptSegment / Java TranscriptResult
    """
    meeting_id: str = ""
    segments: list[TranscriptSegment] = Field(default_factory=list)
    language: str = "zh"
    duration_seconds: float = 0.0
    full_text: str = ""


# ============================================================
# 摘要相关 (Summary)
# ============================================================


class TopicSummary(BaseModel):
    """单个议题摘要

    对应: Go TopicSummary / Java TopicSummary
    """
    title: str = ""
    discussion_points: list[str] = Field(default_factory=list)
    participants: list[str] = Field(default_factory=list)
    conclusion: str = ""


class MeetingSummary(BaseModel):
    """结构化会议纪要

    对应: Go MeetingSummary / Java MeetingSummary
    """
    title: str = ""
    date: str = ""
    participants: list[str] = Field(default_factory=list)
    topics: list[TopicSummary] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)


# ============================================================
# 待办相关 (Action)
# ============================================================


class ActionItem(BaseModel):
    """单条行动项

    对应: Go ActionItem / Java ActionItem
    """
    assignee: str = ""
    task: str = ""
    deadline: str = ""
    priority: Priority = Priority.MEDIUM
    context: str = ""
    jira_issue_key: str = ""
    feishu_task_id: str = ""


class ActionResult(BaseModel):
    """行动项处理结果"""
    meeting_id: str = ""
    action_items: list[ActionItem] = Field(default_factory=list)
    sync_status: dict[str, str] = Field(default_factory=dict)


# ============================================================
# 洞察相关 (Insight)
# ============================================================


class SpeakerStats(BaseModel):
    """说话人统计数据

    对应: Go SpeakerStats / Java SpeakerStats
    """
    speaker: str = ""
    speaking_duration: float = 0.0
    speaking_ratio: float = 0.0
    word_count: int = 0
    segment_count: int = 0


class MeetingInsight(BaseModel):
    """会议洞察

    对应: Go MeetingInsight / Java MeetingInsight
    """
    meeting_id: str = ""
    overall_sentiment: SentimentType = SentimentType.NEUTRAL
    sentiment_score: float = 0.5
    speaker_stats: list[SpeakerStats] = Field(default_factory=list)
    efficiency_score: float = 5.0
    keywords: list[str] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


# ============================================================
# 跟进相关 (Follow-up)
# ============================================================


class FollowUpResult(BaseModel):
    """跟进处理结果

    对应: Go FollowUpResult / Java FollowUpResult
    """
    meeting_id: str = ""
    summary_sent: bool = False
    recipients: list[str] = Field(default_factory=list)
    jira_issues_created: list[str] = Field(default_factory=list)
    feishu_tasks_created: list[str] = Field(default_factory=list)
    reminders_scheduled: int = 0
    report_url: str = ""


# ============================================================
# 全局状态 (Meeting State)
# ============================================================

# LangGraph 使用 TypedDict 定义状态结构，与 Pydantic 模型配合使用
MeetingState = dict
"""
会议处理状态的类型别名（LangGraph TypedDict）

在 meeting_graph.py 中使用具体的 GraphState(TypedDict)，
此类型别名用于 IDE 提示和类型检查。

字段说明:
    meeting_id: str             - 会议唯一ID
    status: str                 - 当前处理状态
    audio_data: bytes           - 音频数据
    transcript: Any             - TranscriptResult 或 None
    transcript_text: str        - 转写纯文本
    summary: Any                - MeetingSummary 或 None
    actions: Any                - ActionResult 或 None
    insights: Any               - MeetingInsight 或 None
    followup: Any               - FollowUpResult 或 None
    errors: list[str]           - 错误列表
"""


def create_initial_state(
    meeting_id: str,
    audio_data: bytes = b"",
) -> dict:
    """
    创建初始会议处理状态

    对照: Go MeetingPipeline.Execute() 中的初始 state 创建

    Args:
        meeting_id: 会议ID
        audio_data: 音频字节数据（为空将使用演示数据）

    Returns:
        初始化的 MeetingState 字典
    """
    return {
        "meeting_id": meeting_id,
        "status": MeetingStatus.CREATED,
        "audio_data": audio_data,
        "transcript": None,
        "transcript_text": "",
        "summary": None,
        "actions": None,
        "insights": None,
        "followup": None,
        "errors": [],
    }
