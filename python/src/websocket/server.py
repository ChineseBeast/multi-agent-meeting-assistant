"""
WebSocket 服务器 - 实时音频流接入和结果推送

支持两种模式:
1. 实时模式: 客户端通过 WebSocket 发送音频流，服务端实时返回转写结果
2. 文件模式: 通过 REST API 上传音频文件，异步处理后推送结果
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from loguru import logger

from ..graph.meeting_graph import run_meeting_pipeline
from ..models.schemas import MeetingStatus
from ..bot import BotManager, AudioCaptureMode
from ..database import init_database, close_database, get_repository_sync


app = FastAPI(
    title="多Agent智能会议助手",
    description="企业级5-Agent会议全流程自动化系统",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 存储活跃的 WebSocket 连接和会议状态
active_connections: dict[str, WebSocket] = {}
meeting_results: dict[str, dict] = {}
bot_manager = BotManager()
repo = get_repository_sync()

# 实时录音相关状态
SILENCE_TIMEOUT_SECONDS = 5  # 静音超过此秒数自动停止并触发Pipeline
_recording_sessions: dict[str, dict] = {}  # meeting_id -> {buffer, last_audio_at, paused}


# ============================================================
# 应用生命周期
# ============================================================


@app.on_event("startup")
async def on_startup():
    """在服务器启动时初始化数据库。"""
    logger.info("正在初始化数据库...")
    await init_database()


@app.on_event("shutdown")
async def on_shutdown():
    """在服务器关闭时清理资源。"""
    logger.info("正在关闭数据库引擎...")
    await close_database()
    await bot_manager.cleanup()


# ============================================================
# 静态文件服务 - 前端页面
# ============================================================

FRONTEND_PATH = os.path.join(
    os.path.dirname(__file__), "..", "static", "index.html"
)


@app.get("/ui", response_class=HTMLResponse)
async def get_ui():
    """返回会议室配置前端页面"""
    if os.path.exists(FRONTEND_PATH):
        with open(FRONTEND_PATH, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Frontend not found</h1>")


# ============================================================
# WebSocket 端点
# ============================================================

@app.websocket("/ws/meeting/{meeting_id}")
async def websocket_meeting(websocket: WebSocket, meeting_id: str):
    """
    WebSocket 会议端点 — 支持实时录音

    协议:
    - 客户端发送: 音频二进制帧 / JSON控制消息
    - 服务端返回: JSON格式的处理结果

    控制消息:
    - {"type": "start"}: 开始录制会话（清空旧缓冲区）
    - {"type": "pause"}: 暂停录制（保留缓冲区，不触发处理）
    - {"type": "resume"}: 继续录制
    - {"type": "stop"}: 停止录制，触发 Pipeline 处理
    - {"type": "ping"}: 心跳

    静音自动结束:
      服务端检测到连续 {SILENCE_TIMEOUT_SECONDS} 秒未收到音频帧时，
      自动停止录制并触发 Pipeline。
    """
    await websocket.accept()
    active_connections[meeting_id] = websocket

    # 初始化录音会话
    _recording_sessions[meeting_id] = {
        "buffer": bytearray(),
        "last_audio_at": 0.0,
        "paused": False,
    }
    session = _recording_sessions[meeting_id]

    logger.info(f"WebSocket connected: {meeting_id}")

    async def _trigger_pipeline(silence_triggered: bool = False):
        """内部函数：将缓冲区音频送入 Pipeline 处理"""
        reason = "静音超时自动触发" if silence_triggered else "手动停止"
        logger.info(f"[{meeting_id}] 触发 Pipeline, 原因: {reason}")

        await websocket.send_json({
            "type": "processing",
            "message": f"正在处理音频 ({reason})，请稍候...",
        })

        result = await run_meeting_pipeline(
            meeting_id=meeting_id,
            audio_data=bytes(session["buffer"]),
        )
        meeting_results[meeting_id] = result
        await _send_results(websocket, result)
        session["buffer"].clear()

    try:
        await websocket.send_json({
            "type": "connected",
            "meeting_id": meeting_id,
            "message": "会议助手已连接，发送 start 消息开始录制",
        })

        while True:
            data = await websocket.receive()

            # ---- 音频数据帧 ----
            if "bytes" in data and data["bytes"]:
                if not session["paused"]:
                    session["buffer"].extend(data["bytes"])
                    session["last_audio_at"] = time.time()
                await websocket.send_json({
                    "type": "recording",
                    "buffer_size": len(session["buffer"]),
                    "paused": session["paused"],
                })

            # ---- JSON 控制消息 ----
            elif "text" in data and data["text"]:
                message = json.loads(data["text"])
                msg_type = message.get("type", "")

                if msg_type == "start":
                    # 开始新录音会话，清空旧缓冲区
                    session["buffer"].clear()
                    session["last_audio_at"] = time.time()
                    session["paused"] = False
                    await websocket.send_json({
                        "type": "started",
                        "meeting_id": meeting_id,
                        "message": "录音已开始，发送音频二进制帧即可",
                    })

                elif msg_type == "pause":
                    session["paused"] = True
                    await websocket.send_json({
                        "type": "paused",
                        "buffer_size": len(session["buffer"]),
                        "message": "录音已暂停",
                    })

                elif msg_type == "resume":
                    session["paused"] = False
                    session["last_audio_at"] = time.time()
                    await websocket.send_json({
                        "type": "resumed",
                        "message": "录音已继续",
                    })

                elif msg_type == "stop":
                    session["paused"] = True  # 防止停止过程中写入新数据
                    await _trigger_pipeline(silence_triggered=False)

                elif msg_type == "demo":
                    await websocket.send_json({
                        "type": "processing",
                        "message": "运行演示模式...",
                    })
                    result = await run_meeting_pipeline(
                        meeting_id=meeting_id,
                        audio_data=b"",
                    )
                    meeting_results[meeting_id] = result
                    await _send_results(websocket, result)

                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong"})

            # ---- 静音超时检测（每收到一条消息都检查）----
            if (
                session["last_audio_at"] > 0
                and not session["paused"]
                and len(session["buffer"]) > 0
            ):
                elapsed = time.time() - session["last_audio_at"]
                if elapsed >= SILENCE_TIMEOUT_SECONDS:
                    logger.info(
                        f"[{meeting_id}] 静音超时 {elapsed:.1f}s, 自动触发 Pipeline"
                    )
                    session["paused"] = True
                    await _trigger_pipeline(silence_triggered=True)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {meeting_id}")
        # 如果断开时有未处理的音频，自动触发
        if meeting_id in _recording_sessions:
            s = _recording_sessions[meeting_id]
            if not s["paused"] and len(s["buffer"]) > 0:
                logger.info(f"[{meeting_id}] 断开时有未处理音频，自动触发 Pipeline")
                try:
                    await _trigger_pipeline(silence_triggered=True)
                except Exception:
                    pass
    except Exception as e:
        logger.error(f"WebSocket error: {meeting_id} - {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e),
            })
        except Exception:
            pass
    finally:
        active_connections.pop(meeting_id, None)
        _recording_sessions.pop(meeting_id, None)


async def _send_results(websocket: WebSocket, state: dict):
    """将 Pipeline 处理结果分步推送给客户端"""
    # 转写结果
    transcript = state.get("transcript")
    if transcript:
        await websocket.send_json({
            "type": "transcript",
            "data": transcript.model_dump() if hasattr(transcript, "model_dump") else {},
        })

    # 摘要结果
    summary = state.get("summary")
    if summary:
        await websocket.send_json({
            "type": "summary",
            "data": summary.model_dump() if hasattr(summary, "model_dump") else {},
        })

    # 待办结果
    actions = state.get("actions")
    if actions:
        await websocket.send_json({
            "type": "actions",
            "data": actions.model_dump() if hasattr(actions, "model_dump") else {},
        })

    # 洞察结果
    insights = state.get("insights")
    if insights:
        await websocket.send_json({
            "type": "insights",
            "data": insights.model_dump() if hasattr(insights, "model_dump") else {},
        })

    # 跟进结果
    followup = state.get("followup")
    if followup:
        await websocket.send_json({
            "type": "followup",
            "data": followup.model_dump() if hasattr(followup, "model_dump") else {},
        })

    # 完成通知
    errors = state.get("errors", [])
    await websocket.send_json({
        "type": "completed",
        "meeting_id": state.get("meeting_id"),
        "status": state.get("status", MeetingStatus.COMPLETED),
        "errors": errors,
    })

    # 结果发送后也持久化到数据库
    try:
        await _persist_results(state)
    except Exception as e:
        logger.error(f"数据库持久化失败: {e}")


async def _persist_results(state: dict):
    """将 Pipeline 所有结果持久化到数据库。"""
    meeting_id = state.get("meeting_id", "")
    if not meeting_id:
        return

    errors = state.get("errors", [])

    # 更新会议状态
    await repo.update_meeting(
        meeting_id,
        status=state.get("status", MeetingStatus.COMPLETED).value if hasattr(state.get("status"), "value") else state.get("status", "completed"),
        error_message="; ".join(errors) if errors else "",
    )

    # 保存转写
    transcript = state.get("transcript")
    if transcript and hasattr(transcript, "model_dump"):
        td = transcript.model_dump()
        segments = td.get("segments", [])
        if segments:
            await repo.save_transcript(
                meeting_id=meeting_id,
                segments=segments,
                language=td.get("language", "zh"),
                duration=td.get("duration_seconds", 0.0),
                full_text=td.get("full_text", ""),
            )

    # 保存摘要
    summary = state.get("summary")
    if summary and hasattr(summary, "model_dump"):
        sd = summary.model_dump()
        topics_data = [t for t in sd.get("topics", [])]
        await repo.save_summary(
            meeting_id=meeting_id,
            title=sd.get("title", ""),
            date=sd.get("date", ""),
            participants=sd.get("participants", []),
            topics=topics_data,
            decisions=sd.get("decisions", []),
            next_steps=sd.get("next_steps", []),
        )

    # 保存待办事项
    actions = state.get("actions")
    if actions and hasattr(actions, "model_dump"):
        ad = actions.model_dump()
        items = ad.get("action_items", [])
        if items:
            await repo.save_action_items(meeting_id=meeting_id, items=items)

    # 保存洞察
    insights = state.get("insights")
    if insights and hasattr(insights, "model_dump"):
        ind = insights.model_dump()
        stats = ind.get("speaker_stats", [])
        await repo.save_insights(
            meeting_id=meeting_id,
            overall_sentiment=ind.get("overall_sentiment", "neutral"),
            sentiment_score=ind.get("sentiment_score", 0.5),
            efficiency_score=ind.get("efficiency_score", 5.0),
            keywords=ind.get("keywords", []),
            highlights=ind.get("highlights", []),
            suggestions=ind.get("suggestions", []),
            speaker_stats=stats,
        )

    # 保存跟进
    followup = state.get("followup")
    if followup and hasattr(followup, "model_dump"):
        fd = followup.model_dump()
        await repo.save_followup(
            meeting_id=meeting_id,
            summary_sent=fd.get("summary_sent", False),
            recipients=fd.get("recipients", []),
            jira_issues_created=fd.get("jira_issues_created", []),
            feishu_tasks_created=fd.get("feishu_tasks_created", []),
            reminders_scheduled=fd.get("reminders_scheduled", 0),
            report_url=fd.get("report_url", ""),
        )

    logger.info(f"会议 {meeting_id} 的结果已持久化到数据库")


# ============================================================
# Meeting Bot 管理 API
# ============================================================


@app.post("/api/v1/bot/start")
async def start_bot(body: dict):
    """
    启动 Meeting Bot 加入会议

    请求体:
    {
        "meeting_id": "可选，自动生成",
        "platform": "tencent 或 feishu",
        "meeting_url": "会议链接",
        "account": "登录账号",
        "password": "登录密码",
        "mode": "simulation 或 webrtc (默认 simulation，适合办公本)"
    }
    """
    meeting_id = body.get("meeting_id", str(uuid.uuid4())[:12])
    platform = body.get("platform", "tencent")
    meeting_url = body.get("meeting_url", "")
    account = body.get("account", "")
    password = body.get("password", "")
    mode_str = body.get("mode", "simulation")

    try:
        mode = AudioCaptureMode(mode_str)
    except ValueError:
        mode = AudioCaptureMode.SIMULATION

    config = {
        "platform": platform,
        "meeting_url": meeting_url,
        "account": account,
        "password": password,
    }

    result = await bot_manager.start_bot(
        meeting_id=meeting_id,
        config=config,
        capture_mode=mode,
    )

    # 创建会议结果记录
    if meeting_id not in meeting_results:
        meeting_results[meeting_id] = {}

    # 持久化到数据库
    try:
        await repo.create_meeting(
            meeting_id=meeting_id,
            platform=platform,
            meeting_url=meeting_url,
            account=account,
            bot_mode=mode.value,
        )
        await repo.update_meeting(
            meeting_id, bot_status=result.get("status", "starting")
        )
    except Exception as e:
        logger.warning(f"Failed to persist meeting to DB: {e}")

    logger.info(
        f"Bot started: {meeting_id}, platform={platform}, "
        f"mode={mode.value}"
    )
    return {
        "success": True,
        "meeting_id": meeting_id,
        "status": result.get("status"),
        "websocket_url": f"ws://localhost:8000/ws/meeting/{meeting_id}",
    }


@app.post("/api/v1/bot/stop/{meeting_id}")
async def stop_bot(meeting_id: str):
    """停止指定会议的 Bot"""
    result = await bot_manager.stop_bot(meeting_id)
    logger.info(f"Bot stopped: {meeting_id}")
    return {"success": True, "meeting_id": meeting_id, **result}


@app.get("/api/v1/bot/status/{meeting_id}")
async def get_bot_status(meeting_id: str):
    """获取 Bot 运行状态"""
    status = bot_manager.get_bot_status(meeting_id)
    if not status:
        return {"meeting_id": meeting_id, "status": "not_found"}
    return status


@app.get("/api/v1/bot/status")
async def get_all_bot_status():
    """获取所有 Bot 状态"""
    return {"bots": bot_manager.get_all_status()}


@app.get("/api/v1/meeting/{meeting_id}/full")
async def get_full_results(meeting_id: str):
    """获取会议完整结果（含 Bot 状态）"""
    result = meeting_results.get(meeting_id, {})
    bot_status = bot_manager.get_bot_status(meeting_id)

    response = {"meeting_id": meeting_id}
    for key in ("transcript", "summary", "actions", "insights", "followup"):
        val = result.get(key)
        if val and hasattr(val, "model_dump"):
            response[key] = val.model_dump()

    response["errors"] = result.get("errors", [])
    response["bot_status"] = bot_status
    return response


# ============================================================
# REST API 端点
# ============================================================

@app.get("/")
async def root():
    return {
        "name": "多Agent智能会议助手",
        "version": "1.0.0",
        "docs": "/docs",
        "websocket": "ws://localhost:8000/ws/meeting/{meeting_id}",
    }


# ============================================================
# 基于数据库的 API 端点
# ============================================================


@app.get("/api/v1/meetings")
async def list_meetings(limit: int = 50, offset: int = 0):
    """列出历史会议记录（从数据库读取）"""
    try:
        meetings = await repo.list_meetings(limit=limit, offset=offset)
        return {"meetings": meetings, "total": len(meetings)}
    except Exception as e:
        logger.error(f"列出会议失败: {e}")
        # 降级：返回内存中的会议
        fallback = [
            {"meeting_id": mid, "status": "unknown"}
            for mid in meeting_results
        ]
        return {"meetings": fallback, "total": len(fallback), "error": str(e)}


@app.get("/api/v1/meetings/search")
async def search_meetings(q: str = "", limit: int = 20):
    """搜索历史会议（按标题/参与人/转写文本模糊匹配）"""
    if not q:
        return {"meetings": []}
    try:
        meetings = await repo.search_meetings(query=q, limit=limit)
        return {"meetings": meetings, "query": q}
    except Exception as e:
        logger.error(f"搜索会议失败: {e}")
        return {"meetings": [], "query": q, "error": str(e)}


@app.get("/api/v1/meetings/detail/{meeting_id}")
async def get_meeting_detail(meeting_id: str):
    """获取会议完整详情（从数据库读取，含所有子表数据）"""
    try:
        meeting = await repo.get_meeting(meeting_id)
        if meeting:
            return meeting
    except Exception as e:
        logger.error(f"数据库获取详情失败 {meeting_id}: {e}")

    # 降级：从内存返回
    result = meeting_results.get(meeting_id, {})
    response = {"meeting_id": meeting_id}
    for key in ("transcript", "summary", "actions", "insights", "followup"):
        val = result.get(key)
        if val and hasattr(val, "model_dump"):
            response[key] = val.model_dump()
    response["errors"] = result.get("errors", [])
    return response


@app.delete("/api/v1/meetings/{meeting_id}")
async def delete_meeting(meeting_id: str):
    """删除会议记录"""
    try:
        deleted = await repo.delete_meeting(meeting_id)
        if deleted:
            meeting_results.pop(meeting_id, None)
            return {"success": True, "meeting_id": meeting_id}
        return {"success": False, "meeting_id": meeting_id, "error": "Not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/v1/meeting/start")
async def start_meeting():
    """创建新会议"""
    meeting_id = str(uuid.uuid4())[:12]
    return {
        "meeting_id": meeting_id,
        "websocket_url": f"ws://localhost:8000/ws/meeting/{meeting_id}",
        "status": "created",
    }


@app.post("/api/v1/meeting/{meeting_id}/upload")
async def upload_audio(meeting_id: str, file: UploadFile = File(...)):
    """上传音频文件并处理"""
    audio_data = await file.read()
    logger.info(
        f"Received audio upload: {meeting_id}, size={len(audio_data)} bytes"
    )

    result = await run_meeting_pipeline(
        meeting_id=meeting_id,
        audio_data=audio_data,
    )
    meeting_results[meeting_id] = result

    # 持久化到数据库
    try:
        await _persist_results(result)
    except Exception as e:
        logger.error(f"上传结果持久化失败: {e}")

    return {
        "meeting_id": meeting_id,
        "status": result.get("status", "completed"),
        "errors": result.get("errors", []),
    }


@app.post("/api/v1/meeting/{meeting_id}/demo")
async def run_demo(meeting_id: str = "demo"):
    """运行演示模式（无需音频）"""
    result = await run_meeting_pipeline(
        meeting_id=meeting_id,
        audio_data=b"",
    )
    meeting_results[meeting_id] = result

    # 持久化到数据库
    try:
        await _persist_results(result)
    except Exception as e:
        logger.error(f"演示结果持久化失败: {e}")

    response: dict[str, Any] = {
        "meeting_id": meeting_id,
        "status": result.get("status"),
    }

    for key in ("transcript", "summary", "actions", "insights", "followup"):
        val = result.get(key)
        if val and hasattr(val, "model_dump"):
            response[key] = val.model_dump()

    response["errors"] = result.get("errors", [])
    return response


@app.get("/api/v1/meeting/{meeting_id}/transcript")
async def get_transcript(meeting_id: str):
    """获取转写结果"""
    result = meeting_results.get(meeting_id)
    if not result:
        return {"error": "Meeting not found"}
    transcript = result.get("transcript")
    if transcript and hasattr(transcript, "model_dump"):
        return transcript.model_dump()
    return {"error": "Transcript not available"}


@app.get("/api/v1/meeting/{meeting_id}/summary")
async def get_summary(meeting_id: str):
    """获取会议纪要"""
    result = meeting_results.get(meeting_id)
    if not result:
        return {"error": "Meeting not found"}
    summary = result.get("summary")
    if summary and hasattr(summary, "model_dump"):
        return summary.model_dump()
    return {"error": "Summary not available"}


@app.get("/api/v1/meeting/{meeting_id}/actions")
async def get_actions(meeting_id: str):
    """获取待办事项"""
    result = meeting_results.get(meeting_id)
    if not result:
        return {"error": "Meeting not found"}
    actions = result.get("actions")
    if actions and hasattr(actions, "model_dump"):
        return actions.model_dump()
    return {"error": "Actions not available"}


@app.get("/api/v1/meeting/{meeting_id}/insights")
async def get_insights(meeting_id: str):
    """获取会议洞察"""
    result = meeting_results.get(meeting_id)
    if not result:
        return {"error": "Meeting not found"}
    insights = result.get("insights")
    if insights and hasattr(insights, "model_dump"):
        return insights.model_dump()
    return {"error": "Insights not available"}


@app.get("/api/v1/meeting/{meeting_id}/report")
async def get_full_report(meeting_id: str):
    """获取完整报告"""
    result = meeting_results.get(meeting_id)
    if not result:
        return {"error": "Meeting not found"}

    response = {"meeting_id": meeting_id}
    for key in ("transcript", "summary", "actions", "insights", "followup"):
        val = result.get(key)
        if val and hasattr(val, "model_dump"):
            response[key] = val.model_dump()

    response["errors"] = result.get("errors", [])
    return response
