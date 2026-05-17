"""
Meeting Bot - 隐形参会人

使用 Playwright 模拟真实用户加入腾讯会议 / 飞书会议，
通过注入 JavaScript 捕获 WebRTC 音频流并推送到后端 WebSocket。

架构:
    1. BotManager: 管理多个会议 Bot 实例（启动/停止/状态查询）
    2. MeetingBot: 单个会议 Bot，负责加入会议 + 音频采集 + WebSocket 推送
    3. BotStatus: Bot 运行状态枚举
"""

from .meeting_bot import MeetingBot, BotManager, BotStatus, AudioCaptureMode

__all__ = ["MeetingBot", "BotManager", "BotStatus", "AudioCaptureMode"]
