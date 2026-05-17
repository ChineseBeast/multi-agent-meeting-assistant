"""
Circuit Breaker（熔断器）

标准的熔断状态机: CLOSED -> OPEN -> HALF_OPEN -> CLOSED

- CLOSED: 正常通行，记录失败次数
- OPEN: 熔断开启，直接快速失败，不调用下游
- HALF_OPEN: 冷却期结束，试探性放行一个请求

使用场景:
    包装 LLM API 调用，当连续失败超过阈值时触发熔断，
    防止雪崩效应拖死整个系统。
"""

from __future__ import annotations

import time
from enum import Enum
from functools import wraps

from loguru import logger


class BreakerState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreakerOpenException(Exception):
    """熔断器开启时抛出的异常 —— 调用方应捕获此异常执行降级"""
    pass


class CircuitBreaker:
    """
    熔断器装饰器

    用法:
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60)

        @breaker
        async def my_api_call(...):
            ...

    Args:
        failure_threshold: 连续失败多少次触发熔断（默认 3）
        recovery_timeout: 熔断后等待多少秒进入半开状态（默认 30）
    """

    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout

        self.state = BreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0

    def __call__(self, func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 1. 检查状态 —— 如果熔断已开启
            if self.state == BreakerState.OPEN:
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    logger.info(
                        "Circuit Breaker [{}] transitioning to HALF_OPEN",
                        func.__name__,
                    )
                    self.state = BreakerState.HALF_OPEN
                else:
                    raise CircuitBreakerOpenException(
                        f"Circuit Breaker [{func.__name__}] is OPEN. Fast failing."
                    )

            # 2. 执行目标函数
            try:
                result = await func(*args, **kwargs)

                # 3. 成功时 —— 如果处于半开状态，恢复为关闭
                if self.state == BreakerState.HALF_OPEN:
                    logger.info(
                        "Circuit Breaker [{}] recovered to CLOSED", func.__name__
                    )
                    self.state = BreakerState.CLOSED
                    self.failure_count = 0

                return result

            except Exception as e:
                # 4. 失败时 —— 累计失败次数，达到阈值则熔断
                self.failure_count += 1
                self.last_failure_time = time.time()

                if self.state in (BreakerState.CLOSED, BreakerState.HALF_OPEN):
                    if self.failure_count >= self.failure_threshold:
                        logger.error(
                            "Circuit Breaker [{}] tripped to OPEN "
                            "after {} failures!",
                            func.__name__,
                            self.failure_count,
                        )
                        self.state = BreakerState.OPEN

                raise e

        return wrapper

    def reset(self):
        """手动重置熔断器（管理员接口）"""
        logger.info("Circuit Breaker manually reset to CLOSED")
        self.state = BreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0

    @property
    def is_open(self) -> bool:
        return self.state == BreakerState.OPEN

    def get_state_info(self) -> dict:
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "last_failure_time": self.last_failure_time,
        }
