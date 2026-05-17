"""MiniMax LLM 客户端 - 支持 M2.7 模型调用"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from .circuit_breaker import CircuitBreaker, CircuitBreakerOpenException

# 全局熔断器：连续失败 3 次后熔断 60 秒
llm_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60)


class MiniMaxClient:
    """
    MiniMax API 客户端

    支持 MiniMax M2.7 模型，兼容 OpenAI 接口格式。
    文档: https://platform.minimaxi.com/document/guides/chat-model/chat/api
    """

    BASE_URL = "https://api.minimax.chat/v1"

    def __init__(
        self,
        api_key: str | None = None,
        group_id: str | None = None,
        model: str = "abab6.5s-chat",
    ):
        self.api_key = api_key or os.getenv("MINIMAX_API_KEY", "")
        self.group_id = group_id or os.getenv("MINIMAX_GROUP_ID", "")
        self.model = model
        self._client = httpx.AsyncClient(
            timeout=60.0,
            headers={"Authorization": f"Bearer {self.api_key}"},
        )

    @llm_breaker
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: dict | None = None,
    ) -> str:
        """
        调用 MiniMax 聊天接口

        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            temperature: 温度参数
            max_tokens: 最大生成token数
            response_format: 输出格式约束 (如 {"type": "json_object"})

        Returns:
            模型生成的文本
        """
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format

        url = f"{self.BASE_URL}/text/chatcompletion_v2"
        if self.group_id:
            url = f"{url}?GroupId={self.group_id}"

        response = await self._client.post(url, json=payload)
        response.raise_for_status()

        data = response.json()

        # 检查 MiniMax 业务状态码
        base_resp = data.get("base_resp", {})
        if base_resp.get("status_code", 0) != 0:
            err_msg = base_resp.get("status_msg", "unknown")
            logger.error(f"MiniMax API error: {err_msg} (code={base_resp.get('status_code')})")
            raise ValueError(f"MiniMax API error: {err_msg}")

        if "choices" in data and len(data["choices"]) > 0:
            # MiniMax v2 响应: choices[0].message.content
            message = data["choices"][0].get("message", {})
            content = message.get("content", "")
            if content:
                return content

        logger.error(f"MiniMax API unexpected response: {data}")
        raise ValueError(f"Unexpected API response: {data}")

    async def chat_json(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> dict:
        """调用聊天接口并解析 JSON 输出（MiniMax 不支持 response_format，改由提示词约束）"""
        # MiniMax 不支持 response_format=json_object，追加提示词要求 JSON 输出
        json_messages = list(messages)
        if json_messages and json_messages[-1].get("role") == "user":
            json_messages[-1]["content"] += (
                "\n\n请严格按照 JSON 格式输出，不要包含 markdown 代码块标记。"
            )
        text = await self.chat(
            messages=json_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            # 不传 response_format，MiniMax 不支持
        )
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # MiniMax 有时会在 JSON 外包 markdown 代码块
            stripped = text.strip()
            if stripped.startswith("```"):
                # 移除 ```json ... ``` 包装
                import re
                match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", stripped, re.DOTALL)
                if match:
                    try:
                        return json.loads(match.group(1))
                    except json.JSONDecodeError:
                        pass
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
            raise

    async def close(self):
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
