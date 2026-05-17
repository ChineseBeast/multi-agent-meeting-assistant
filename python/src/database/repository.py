"""
MeetingRepository — 会议数据的高层级 CRUD 操作

每个公开方法自行创建并销毁 session，调用方无需关心 session 生命周期。所有方法均为异步。
"""

from __future__ import annotations

import json
from typing import Any

from loguru import logger
from sqlalchemy import select, delete, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from .engine import get_session
from .models import (
    ActionItemRecord,
    FollowUpRecord,
    InsightRecord,
    MeetingRecord,
    SpeakerStatRecord,
    TopicRecord,
    TranscriptSegmentRecord,
)


class MeetingRepository:
    """无状态仓库——每个方法自行打开 session。"""

    # ── 会议 ────────────────────────────────────────────

    async def create_meeting(
        self,
        meeting_id: str,
        platform: str = "",
        meeting_url: str = "",
        account: str = "",
        bot_mode: str = "simulation",
    ) -> MeetingRecord:
        """插入一条新的会议记录。"""
        record = MeetingRecord(
            meeting_id=meeting_id,
            platform=platform,
            meeting_url=meeting_url,
            account=account,
            bot_mode=bot_mode,
            status="created",
        )
        session = await get_session()
        try:
            session.add(record)
            await session.commit()
            await session.refresh(record)
        finally:
            await session.close()
        logger.debug("DB: created meeting {}", meeting_id)
        return record

    async def update_meeting(self, meeting_id: str, **kwargs) -> MeetingRecord | None:
        """更新会议记录的任意字段（status, bot_status 等）。"""
        session = await get_session()
        try:
            result = await session.execute(
                select(MeetingRecord).where(MeetingRecord.meeting_id == meeting_id)
            )
            record = result.scalar_one_or_none()
            if record is None:
                logger.warning("DB: meeting {} not found for update", meeting_id)
                return None
            for key, value in kwargs.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            await session.commit()
            await session.refresh(record)
        finally:
            await session.close()
        return record

    # ── 转写 ─────────────────────────────────────────

    async def save_transcript(
        self,
        meeting_id: str,
        segments: list[dict],
        language: str = "zh",
        duration: float = 0.0,
        full_text: str = "",
    ) -> int:
        """存储会议的转写片段。返回片段数量。

        先删除已有片段（幂等重保存）。
        """
        session = await get_session()
        try:
            # 删除旧片段
            await session.execute(
                delete(TranscriptSegmentRecord).where(
                    TranscriptSegmentRecord.meeting_id == meeting_id
                )
            )

            for idx, seg in enumerate(segments):
                session.add(
                    TranscriptSegmentRecord(
                        meeting_id=meeting_id,
                        speaker=seg.get("speaker", "Unknown"),
                        text=seg.get("text", ""),
                        start_time=seg.get("start", 0.0),
                        end_time=seg.get("end", 0.0),
                        confidence=seg.get("confidence", 0.0),
                        segment_index=idx,
                    )
                )

            # 更新会议的降维字段
            result = await session.execute(
                select(MeetingRecord).where(MeetingRecord.meeting_id == meeting_id)
            )
            meeting = result.scalar_one_or_none()
            if meeting:
                meeting.transcript_language = language
                meeting.transcript_duration = duration
                meeting.transcript_full_text = full_text

            await session.commit()
        finally:
            await session.close()

        count = len(segments)
        logger.debug("DB: saved {} transcript segments for {}", count, meeting_id)
        return count

    # ── 摘要 / 议题 ───────────────────────────────────

    async def save_summary(
        self,
        meeting_id: str,
        title: str = "",
        date: str = "",
        participants: list[str] | None = None,
        topics: list[dict] | None = None,
        decisions: list[str] | None = None,
        next_steps: list[str] | None = None,
    ) -> int:
        """存储结构化的会议摘要。返回议题数量。"""
        topics = topics or []
        participants = participants or []
        decisions = decisions or []
        next_steps = next_steps or []

        session = await get_session()
        try:
            # 删除旧议题
            await session.execute(
                delete(TopicRecord).where(
                    TopicRecord.meeting_id == meeting_id
                )
            )

            for t in topics:
                session.add(
                    TopicRecord(
                        meeting_id=meeting_id,
                        title=t.get("title", ""),
                        discussion_points=json.dumps(
                            t.get("discussion_points", []), ensure_ascii=False
                        ),
                        participants=json.dumps(
                            t.get("participants", []), ensure_ascii=False
                        ),
                        conclusion=t.get("conclusion", ""),
                    )
                )

            # 会议上的降维字段
            result = await session.execute(
                select(MeetingRecord).where(MeetingRecord.meeting_id == meeting_id)
            )
            meeting = result.scalar_one_or_none()
            if meeting:
                meeting.summary_title = title
                meeting.summary_date = date
                meeting.summary_participants = json.dumps(
                    participants, ensure_ascii=False
                )
                meeting.summary_decisions = json.dumps(
                    decisions, ensure_ascii=False
                )
                meeting.summary_next_steps = json.dumps(
                    next_steps, ensure_ascii=False
                )

            await session.commit()
        finally:
            await session.close()

        logger.debug("DB: saved {} topics for {}", len(topics), meeting_id)
        return len(topics)

    # ── 待办事项 ───────────────────────────────────────

    async def save_action_items(
        self, meeting_id: str, items: list[dict]
    ) -> int:
        """存储待办事项。返回事项数量。"""
        session = await get_session()
        try:
            await session.execute(
                delete(ActionItemRecord).where(
                    ActionItemRecord.meeting_id == meeting_id
                )
            )

            for item in items:
                session.add(
                    ActionItemRecord(
                        meeting_id=meeting_id,
                        assignee=item.get("assignee", ""),
                        task=item.get("task", ""),
                        deadline=item.get("deadline", ""),
                        priority=item.get("priority", "medium"),
                        context=item.get("context", ""),
                        jira_issue_key=item.get("jira_issue_key", ""),
                        feishu_task_id=item.get("feishu_task_id", ""),
                    )
                )

            await session.commit()
        finally:
            await session.close()

        logger.debug("DB: saved {} action items for {}", len(items), meeting_id)
        return len(items)

    # ── 洞察 + 说话人统计 ───────────────────────────

    async def save_insights(
        self,
        meeting_id: str,
        overall_sentiment: str = "neutral",
        sentiment_score: float = 0.5,
        efficiency_score: float = 5.0,
        keywords: list[str] | None = None,
        highlights: list[str] | None = None,
        suggestions: list[str] | None = None,
        speaker_stats: list[dict] | None = None,
    ) -> InsightRecord:
        """存储洞察记录 + 说话人统计。返回 InsightRecord。"""
        keywords = keywords or []
        highlights = highlights or []
        suggestions = suggestions or []
        speaker_stats = speaker_stats or []

        session = await get_session()
        try:
            # 删除旧洞察 + 统计
            old_result = await session.execute(
                select(InsightRecord).where(
                    InsightRecord.meeting_id == meeting_id
                )
            )
            old = old_result.scalar_one_or_none()
            if old:
                await session.delete(old)

            await session.execute(
                delete(SpeakerStatRecord).where(
                    SpeakerStatRecord.meeting_id == meeting_id
                )
            )

            insight = InsightRecord(
                meeting_id=meeting_id,
                overall_sentiment=overall_sentiment,
                sentiment_score=sentiment_score,
                efficiency_score=efficiency_score,
                keywords=json.dumps(keywords, ensure_ascii=False),
                highlights=json.dumps(highlights, ensure_ascii=False),
                suggestions=json.dumps(suggestions, ensure_ascii=False),
            )
            session.add(insight)

            for stat in speaker_stats:
                session.add(
                    SpeakerStatRecord(
                        meeting_id=meeting_id,
                        speaker=stat.get("speaker", ""),
                        speaking_duration=stat.get("speaking_duration", 0.0),
                        speaking_ratio=stat.get("speaking_ratio", 0.0),
                        word_count=stat.get("word_count", 0),
                        segment_count=stat.get("segment_count", 0),
                    )
                )

            await session.commit()
            await session.refresh(insight)
        finally:
            await session.close()

        logger.debug(
            "DB: saved insight + {} speaker stats for {}",
            len(speaker_stats),
            meeting_id,
        )
        return insight

    # ── 跟进 ──────────────────────────────────────────

    async def save_followup(
        self,
        meeting_id: str,
        summary_sent: bool = False,
        recipients: list[str] | None = None,
        jira_issues_created: list[str] | None = None,
        feishu_tasks_created: list[str] | None = None,
        reminders_scheduled: int = 0,
        report_url: str = "",
    ) -> FollowUpRecord:
        """存储跟进记录。返回 FollowUpRecord。"""
        recipients = recipients or []
        jira_issues_created = jira_issues_created or []
        feishu_tasks_created = feishu_tasks_created or []

        session = await get_session()
        try:
            old_result = await session.execute(
                select(FollowUpRecord).where(
                    FollowUpRecord.meeting_id == meeting_id
                )
            )
            old = old_result.scalar_one_or_none()
            if old:
                await session.delete(old)
                await session.flush()

            record = FollowUpRecord(
                meeting_id=meeting_id,
                summary_sent=summary_sent,
                recipients=json.dumps(recipients, ensure_ascii=False),
                jira_issues_created=json.dumps(
                    jira_issues_created, ensure_ascii=False
                ),
                feishu_tasks_created=json.dumps(
                    feishu_tasks_created, ensure_ascii=False
                ),
                reminders_scheduled=reminders_scheduled,
                report_url=report_url,
            )
            session.add(record)
            await session.commit()
            await session.refresh(record)
        finally:
            await session.close()

        logger.debug("DB: saved followup for {}", meeting_id)
        return record

    # ── 查询 ────────────────────────────────────────────

    async def get_meeting(self, meeting_id: str) -> dict | None:
        """获取单个会议及其所有关联数据，返回嵌套字典。"""
        session = await get_session()
        try:
            result = await session.execute(
                select(MeetingRecord).where(
                    MeetingRecord.meeting_id == meeting_id
                )
            )
            meeting = result.scalar_one_or_none()
            if meeting is None:
                return None

            return self._meeting_to_full_dict(meeting)
        finally:
            await session.close()

    async def list_meetings(
        self, limit: int = 50, offset: int = 0
    ) -> list[dict]:
        """返回会议摘要的分页列表（不含详情）。"""
        session = await get_session()
        try:
            result = await session.execute(
                select(MeetingRecord)
                .order_by(MeetingRecord.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            meetings = result.scalars().all()
            return [m.to_dict() for m in meetings]
        finally:
            await session.close()

    async def search_meetings(
        self, query: str, limit: int = 20
    ) -> list[dict]:
        """跨会议标题、参与人和转写全文进行全文搜索。"""
        pattern = f"%{query}%"
        session = await get_session()
        try:
            result = await session.execute(
                select(MeetingRecord)
                .where(
                    or_(
                        MeetingRecord.summary_title.ilike(pattern),
                        MeetingRecord.summary_participants.ilike(pattern),
                        MeetingRecord.transcript_full_text.ilike(pattern),
                        MeetingRecord.meeting_id.ilike(pattern),
                    )
                )
                .order_by(MeetingRecord.created_at.desc())
                .limit(limit)
            )
            meetings = result.scalars().all()
            return [m.to_dict() for m in meetings]
        finally:
            await session.close()

    async def delete_meeting(self, meeting_id: str) -> bool:
        """删除会议及其所有关联数据（级联删除）。"""
        session = await get_session()
        try:
            result = await session.execute(
                select(MeetingRecord).where(
                    MeetingRecord.meeting_id == meeting_id
                )
            )
            meeting = result.scalar_one_or_none()
            if meeting is None:
                return False
            await session.delete(meeting)
            await session.commit()
        finally:
            await session.close()
        logger.info("DB: deleted meeting {}", meeting_id)
        return True

    # ── 内部辅助方法 ───────────────────────────────────

    @staticmethod
    def _meeting_to_full_dict(meeting: MeetingRecord) -> dict:
        base = meeting.to_dict()
        base["transcript_segments"] = [
            s.to_dict() for s in meeting.transcript_segments
        ]
        base["topics"] = [t.to_dict() for t in meeting.topics]
        base["action_items"] = [a.to_dict() for a in meeting.action_items]
        base["speaker_stats"] = [s.to_dict() for s in meeting.speaker_stats]
        base["insight"] = meeting.insight.to_dict() if meeting.insight else None
        base["followup"] = meeting.followup.to_dict() if meeting.followup else None
        return base
