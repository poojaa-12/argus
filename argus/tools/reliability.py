from __future__ import annotations

import random
import time
from dataclasses import dataclass

from argus.agent.schemas import ErrorClassification, PlanStep
from argus.tools.errors import ExecutorError, MalformedResponseError, ToolError, ToolTimeoutError


@dataclass
class RetryPolicy:
    max_retries: int = 2
    base_delay_s: float = 0.01
    jitter_s: float = 0.005

    def backoff_delay(self, retry_index: int) -> float:
        # Exponential backoff: base, 2*base, 4*base...
        return self.base_delay_s * (2**retry_index) + random.uniform(0.0, self.jitter_s)


def max_attempts_for_step(step: PlanStep, retry_policy: RetryPolicy) -> int:
    if step.max_step_attempts_override is not None:
        return step.max_step_attempts_override
    return retry_policy.max_retries + 1


def is_retryable(error: Exception) -> bool:
    return isinstance(error, (ToolTimeoutError, MalformedResponseError, ExecutorError))


def sleep_for_retry(policy: RetryPolicy, retry_index: int, do_sleep: bool) -> None:
    if not do_sleep:
        return
    time.sleep(policy.backoff_delay(retry_index))


def error_type_name(error: Exception) -> str:
    if isinstance(error, ToolError):
        return error.__class__.__name__
    return "UnknownError"


def classify_error(error: Exception | None) -> ErrorClassification:
    if error is None:
        return ErrorClassification.UNKNOWN
    if is_retryable(error):
        return ErrorClassification.TRANSIENT
    if isinstance(error, ToolError):
        return ErrorClassification.PERMANENT
    return ErrorClassification.UNKNOWN

