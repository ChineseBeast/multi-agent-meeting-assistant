"""
多Agent智能会议助手系统 - Python 版入口

启动方式:
    python -m src.main
    # 或
    uvicorn src.websocket.server:app --host 0.0.0.0 --port 8000 --reload
"""

import asyncio
import os
import sys
import uvicorn
from dotenv import load_dotenv
from loguru import logger

# Windows 下 Playwright 需要 SelectorEventLoop 来创建子进程
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

load_dotenv()

from .websocket.server import app


def main():
    host = os.getenv("SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("SERVER_PORT", "8000"))
    log_level = os.getenv("LOG_LEVEL", "info").lower()

    logger.info(f"Starting Meeting Assistant Server on {host}:{port}")
    logger.info("API docs: http://localhost:{}/docs".format(port))
    logger.info("UI Console: http://localhost:{}/ui".format(port))
    logger.info("WebSocket: ws://localhost:{}/ws/meeting/{{meeting_id}}".format(port))

    # Windows + Anaconda 下 Playwright 需要 SelectorEventLoop
    # uvicorn reload 模式不继承此策略，这里强制禁用 reload
    use_reload = os.getenv("UVICORN_RELOAD", "").lower() == "true"
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    uvicorn.run(
        "src.websocket.server:app",
        host=host,
        port=port,
        log_level=log_level,
        reload=use_reload,
    )


if __name__ == "__main__":
    main()
