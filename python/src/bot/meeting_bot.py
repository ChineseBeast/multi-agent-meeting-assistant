"""
Meeting Bot - 隐形参会人（核心实现）

使用 Playwright 模拟浏览器加入在线会议，通过 JavaScript 注入
捕获系统音频流并推送至后端 WebSocket 进行实时转写。

支持的会议平台:
    - 腾讯会议 (Tencent Meeting)
    - 飞书会议 (Feishu / Lark Meeting)

运行模式:
    - headless: 浏览器在后台运行（适合服务器部署）
    - visible: 浏览器可见（适合调试）
    - simulation: 纯模拟模式，不启动浏览器（适合开发/演示）

用法:
    manager = BotManager()
    await manager.start_bot("meeting-001", {
        "platform": "tencent",
        "meeting_url": "https://meeting.tencent.com/p/123456",
        "account": "user@example.com",
        "password": "password123"
    })
"""

from __future__ import annotations

import asyncio
import json
import struct
import time
import uuid
from enum import Enum
from typing import Any

from loguru import logger


class BotStatus(str, Enum):
    """Bot 运行状态"""
    IDLE = "idle"
    STARTING = "starting"
    JOINING = "joining"
    CONNECTED = "connected"
    STREAMING = "streaming"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class AudioCaptureMode(str, Enum):
    """音频采集模式"""
    WEBRTC = "webrtc"          # 通过浏览器 WebRTC API 捕获
    SIMULATION = "simulation"  # 模拟模式，生成测试数据


class MeetingBot:
    """
    单个会议 Bot —— 负责加入指定会议并采集音频

    每个 Bot 实例对应一个会议连接，独立的浏览器上下文和 WebSocket 连接。
    """

    def __init__(
        self,
        meeting_id: str,
        config: dict,
        backend_ws_url: str = "ws://localhost:8000/ws/meeting/",
        capture_mode: AudioCaptureMode = AudioCaptureMode.SIMULATION,
    ):
        self.meeting_id = meeting_id
        self.config = config
        self.backend_ws_url = f"{backend_ws_url}{meeting_id}"
        self.capture_mode = capture_mode

        self.status = BotStatus.IDLE
        self.error_message: str | None = None
        self.stats: dict = {
            "audio_chunks_sent": 0,
            "bytes_sent": 0,
            "started_at": 0,
            "duration_seconds": 0,
        }

        # 内部状态
        self._browser = None
        self._page = None
        self._context = None
        self._ws = None
        self._running = False
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()

    async def start(self):
        """启动 Bot —— 加入会议并开始采集音频"""
        self._running = True
        self._stop_event.clear()
        self.status = BotStatus.STARTING
        self.stats["started_at"] = time.time()
        logger.info(f"[Bot {self.meeting_id}] Starting...")

        # 根据模式选择执行路径
        if self.capture_mode == AudioCaptureMode.SIMULATION:
            self._task = asyncio.create_task(self._run_simulation())
        else:
            self._task = asyncio.create_task(self._run_browser())

        return {"meeting_id": self.meeting_id, "status": self.status.value}

    async def stop(self):
        """停止 Bot"""
        self.status = BotStatus.STOPPING
        self._stop_event.set()
        logger.info(f"[Bot {self.meeting_id}] Stopping...")

        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass

        self.status = BotStatus.STOPPED
        self._running = False
        self.stats["duration_seconds"] = time.time() - self.stats["started_at"]
        logger.info(
            f"[Bot {self.meeting_id}] Stopped. "
            f"Sent {self.stats['audio_chunks_sent']} chunks, "
            f"{self.stats['bytes_sent']} bytes"
        )

    def get_status(self) -> dict:
        if self._running and self.stats["started_at"] > 0:
            self.stats["duration_seconds"] = time.time() - self.stats["started_at"]
        return {
            "meeting_id": self.meeting_id,
            "status": self.status.value,
            "error": self.error_message,
            "stats": self.stats,
            "config": {
                "platform": self.config.get("platform"),
                "meeting_url": self.config.get("meeting_url"),
                "mode": self.capture_mode.value,
            },
        }

    # ---- 模拟模式 ----
    async def _run_simulation(self):
        """
        模拟模式：不启动浏览器，生成模拟音频数据
        适合在办公本上开发和演示
        """
        import websockets

        self.status = BotStatus.JOINING
        await asyncio.sleep(1)
        logger.info(f"[Bot {self.meeting_id}] Simulation mode, joining meeting...")

        platform = self.config.get("platform", "tencent")
        meeting_url = self.config.get("meeting_url", "demo")

        try:
            # 连接后端 WebSocket
            self.status = BotStatus.CONNECTED
            async with websockets.connect(self.backend_ws_url) as ws:
                self._ws = ws
                self.status = BotStatus.STREAMING
                logger.info(
                    f"[Bot {self.meeting_id}] Connected to backend, "
                    f"streaming simulated audio..."
                )

                # 发送开始消息
                await ws.send(json.dumps({
                    "type": "bot_status",
                    "meeting_id": self.meeting_id,
                    "platform": platform,
                    "meeting_url": meeting_url,
                    "message": f"Bot joined {platform} meeting via simulation mode",
                }))

                # 模拟音频数据：生成简单的正弦波 PCM 数据
                sample_rate = 16000
                chunk_duration = 0.5  # 每次发送 500ms 音频
                chunk_samples = int(sample_rate * chunk_duration)
                frequency = 440  # A4 note

                while not self._stop_event.is_set():
                    # 生成模拟音频数据 (Int16 PCM)
                    import math
                    samples = []
                    for i in range(chunk_samples):
                        t = (self.stats["audio_chunks_sent"] * chunk_samples + i) / sample_rate
                        sample = int(math.sin(2 * math.pi * frequency * t) * 5000)
                        samples.append(max(-32768, min(32767, sample)))

                    audio_bytes = struct.pack(f"<{len(samples)}h", *samples)

                    # 通过 WebSocket 发送模拟音频
                    await ws.send(audio_bytes)
                    self.stats["audio_chunks_sent"] += 1
                    self.stats["bytes_sent"] += len(audio_bytes)

                    await asyncio.sleep(chunk_duration)

        except asyncio.CancelledError:
            logger.info(f"[Bot {self.meeting_id}] Simulation cancelled")
        except Exception as e:
            self.status = BotStatus.ERROR
            self.error_message = str(e)
            logger.error(f"[Bot {self.meeting_id}] Simulation error: {e}")
        finally:
            if not self._stop_event.is_set():
                self._stop_event.set()

    # ---- 浏览器模式 ----
    async def _run_browser(self):
        """
        浏览器模式：使用 Playwright 打开真实浏览器加入会议

        注意：此模式需要安装 Playwright 浏览器:
            playwright install chromium

        由于会议平台 (腾讯/飞书) 使用加密的 WebRTC 协议，
        实际加入会议需要处理登录、密码验证、页面交互等逻辑。
        此处提供框架实现，具体页面交互需根据平台 DOM 结构定制。
        """
        import websockets

        self.status = BotStatus.JOINING
        logger.info(f"[Bot {self.meeting_id}] Launching browser...")

        try:
            from playwright.async_api import async_playwright

            platform = self.config.get("platform", "tencent")
            meeting_url = self.config.get("meeting_url", "")
            account = self.config.get("account", "")
            password = self.config.get("password", "")

            async with async_playwright() as p:
                # 启动浏览器
                self._browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--use-fake-ui-for-media-stream",
                        "--autoplay-policy=no-user-gesture-required",
                        "--disable-web-security",
                        "--allow-file-access-from-files",
                    ],
                )
                self._context = await self._browser.new_context(
                    viewport={"width": 1280, "height": 720},
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                )
                self._page = await self._context.new_page()

                # 根据平台处理登录
                if platform == "tencent":
                    await self._handle_tencent_login(meeting_url, account, password)
                elif platform == "feishu":
                    await self._handle_feishu_login(meeting_url, account, password)
                else:
                    raise ValueError(f"Unsupported platform: {platform}")

                self.status = BotStatus.CONNECTED

                # 注入音频采集脚本
                async with websockets.connect(self.backend_ws_url) as ws:
                    self._ws = ws
                    self.status = BotStatus.STREAMING
                    logger.info(
                        f"[Bot {self.meeting_id}] Connected, "
                        f"injecting audio capture..."
                    )

                    # 发送平台信息
                    await ws.send(json.dumps({
                        "type": "bot_status",
                        "meeting_id": self.meeting_id,
                        "platform": platform,
                        "meeting_url": meeting_url,
                        "message": f"Bot joined {platform} meeting",
                    }))

                    # 注入 WebRTC 音频捕获 JavaScript
                    await self._page.evaluate("""
                        async (wsUrl) => {
                            const ws = new WebSocket(wsUrl);
                            ws.onopen = () => console.log('Bot WS connected');

                            try {
                                // 获取系统音频输出 (混音后的系统声音)
                                const stream = await navigator.mediaDevices.getUserMedia({
                                    audio: {
                                        echoCancellation: false,
                                        noiseSuppression: false,
                                        autoGainControl: false
                                    },
                                    video: false
                                });

                                const audioContext = new AudioContext({sampleRate: 16000});
                                const source = audioContext.createMediaStreamSource(stream);
                                const processor = audioContext.createScriptProcessor(4096, 1, 1);

                                source.connect(processor);
                                processor.connect(audioContext.destination);

                                processor.onaudioprocess = (e) => {
                                    const float32Data = e.inputBuffer.getChannelData(0);
                                    // 转换为 Int16 PCM
                                    const int16Data = new Int16Array(float32Data.length);
                                    for (let i = 0; i < float32Data.length; i++) {
                                        const s = Math.max(-1, Math.min(1, float32Data[i]));
                                        int16Data[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
                                    }
                                    if (ws.readyState === WebSocket.OPEN) {
                                        ws.send(int16Data.buffer);
                                    }
                                };
                            } catch (err) {
                                console.error('Audio capture error:', err);
                                ws.send(JSON.stringify({
                                    type: 'bot_error',
                                    message: 'Audio capture failed: ' + err.message
                                }));
                            }
                        }
                    """, self.backend_ws_url)

                    # 保持 Bot 在线，直到被停止
                    while not self._stop_event.is_set():
                        await asyncio.sleep(1)

                await self._browser.close()

        except asyncio.CancelledError:
            logger.info(f"[Bot {self.meeting_id}] Browser task cancelled")
        except ImportError:
            logger.error(
                f"[Bot {self.meeting_id}] playwright not installed. "
                f"Run: pip install playwright && playwright install chromium"
            )
            self.status = BotStatus.ERROR
            self.error_message = "playwright not installed"
        except Exception as e:
            self.status = BotStatus.ERROR
            self.error_message = str(e)
            logger.error(f"[Bot {self.meeting_id}] Browser error: {e}")
        finally:
            if self._browser:
                try:
                    await self._browser.close()
                except Exception:
                    pass
            if not self._stop_event.is_set():
                self._stop_event.set()

    # ---- 平台登录处理器 ----

    async def _handle_tencent_login(
        self, meeting_url: str, account: str, password: str
    ):
        """处理腾讯会议登录（框架实现，需根据实际 DOM 调整）"""
        logger.info(f"[Bot {self.meeting_id}] Handling Tencent login...")
        page = self._page

        await page.goto(meeting_url, wait_until="domcontentloaded")
        await asyncio.sleep(3)

        # 尝试点击"加入会议"按钮
        try:
            join_btn = await page.query_selector("text=加入会议")
            if join_btn:
                await join_btn.click()
                await asyncio.sleep(2)
        except Exception:
            pass

        # 输入密码（如果需要）
        if password:
            try:
                pwd_input = await page.query_selector("input[type='password']")
                if pwd_input:
                    await pwd_input.fill(password)
                    await asyncio.sleep(1)
            except Exception:
                pass

        logger.info(f"[Bot {self.meeting_id}] Tencent login flow completed")

    async def _handle_feishu_login(
        self, meeting_url: str, account: str, password: str
    ):
        """处理飞书会议登录（框架实现，需根据实际 DOM 调整）"""
        logger.info(f"[Bot {self.meeting_id}] Handling Feishu login...")
        page = self._page

        await page.goto(meeting_url, wait_until="domcontentloaded")
        await asyncio.sleep(3)

        # 飞书会议可能需要扫码登录，此处为框架占位
        if account and password:
            try:
                account_input = await page.query_selector("input[type='text']")
                if account_input:
                    await account_input.fill(account)
                    await asyncio.sleep(1)

                pwd_input = await page.query_selector("input[type='password']")
                if pwd_input:
                    await pwd_input.fill(password)
                    await asyncio.sleep(1)

                login_btn = await page.query_selector("button:has-text('登录')")
                if login_btn:
                    await login_btn.click()
                    await asyncio.sleep(3)
            except Exception:
                pass

        logger.info(f"[Bot {self.meeting_id}] Feishu login flow completed")


class BotManager:
    """
    Bot 管理器 —— 管理所有活跃的会议 Bot 实例

    单例模式，全局只有一个管理器。
    """

    _instance: BotManager | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._bots: dict[str, MeetingBot] = {}
            cls._instance._initialized = True
        return cls._instance

    async def start_bot(
        self,
        meeting_id: str | None = None,
        config: dict | None = None,
        capture_mode: AudioCaptureMode = AudioCaptureMode.SIMULATION,
    ) -> dict:
        """
        启动一个会议 Bot

        Args:
            meeting_id: 会议ID（不提供则自动生成）
            config: 配置字典
                - platform: "tencent" 或 "feishu"
                - meeting_url: 会议链接
                - account: 登录账号
                - password: 登录密码
            capture_mode: 音频采集模式

        Returns:
            Bot 状态信息
        """
        meeting_id = meeting_id or str(uuid.uuid4())[:12]
        config = config or {}

        # 如果已有同 ID 的 Bot 在运行，先停止
        if meeting_id in self._bots:
            existing = self._bots[meeting_id]
            if existing._running:
                await existing.stop()

        bot = MeetingBot(
            meeting_id=meeting_id,
            config=config,
            capture_mode=capture_mode,
        )
        self._bots[meeting_id] = bot
        result = await bot.start()
        return result

    async def stop_bot(self, meeting_id: str) -> dict:
        """停止指定 Bot"""
        bot = self._bots.get(meeting_id)
        if not bot:
            return {"meeting_id": meeting_id, "error": "Bot not found"}
        await bot.stop()
        return bot.get_status()

    async def stop_all(self):
        """停止所有 Bot"""
        for meeting_id in list(self._bots.keys()):
            await self.stop_bot(meeting_id)

    def get_bot_status(self, meeting_id: str) -> dict | None:
        """获取指定 Bot 的状态"""
        bot = self._bots.get(meeting_id)
        if bot:
            return bot.get_status()
        return None

    def get_all_status(self) -> dict[str, dict]:
        """获取所有 Bot 的状态"""
        return {
            mid: bot.get_status()
            for mid, bot in self._bots.items()
        }

    def remove_bot(self, meeting_id: str):
        """从管理器移除 Bot（不停止，仅清理记录）"""
        self._bots.pop(meeting_id, None)

    async def cleanup(self):
        """清理所有 Bot 资源"""
        await self.stop_all()
        self._bots.clear()
