from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StepRequirement(str, Enum):
    REQUIRED = "required"
    OPTIONAL = "optional"


class RunStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL_SUCCESS_OPTIONAL_DEGRADED = "partial_success_optional_degraded"
    FAILED_REQUIRED_STEP = "failed_required_step"
    FAILED_POLICY_EXHAUSTED = "failed_policy_exhausted"
    FAILED_VALIDATION = "failed_validation"


class ErrorClassification(str, Enum):
    TRANSIENT = "transient"
    PERMANENT = "permanent"
    UNKNOWN = "unknown"


@dataclass
class PlanStep:
    step_id: str
    tool_name: str
    payload: dict[str, Any]
    requirement: StepRequirement = StepRequirement.REQUIRED
    fallback_tool_name: str | None = None
    step_timeout_ms: int | None = None
    max_step_attempts_override: int | None = None


@dataclass
class TaskPlan:
    task_id: str
    expected_success: bool
    steps: list[PlanStep]
    plan_version: str = "1.0"
    scenario_tag: str = "default"
    correlation_id: str | None = None


@dataclass
class ToolCallResult:
    ok: bool
    output: dict[str, Any] | None = None
    error_type: str | None = None
    error_message: str | None = None
    attempts: int = 1
    used_fallback: bool = False
    error_classification: ErrorClassification | None = None


@dataclass
class StepTrace:
    step_id: str
    tool_name: str
    requirement: StepRequirement
    success: bool
    attempts: int
    used_fallback: bool
    error_type: str | None = None
    error_classification: ErrorClassification | None = None
    latency_ms: float | None = None


@dataclass
class RunTrace:
    task_id: str
    success: bool
    steps: list[StepTrace] = field(default_factory=list)
    failed_required_step: str | None = None
    optional_failures: list[str] = field(default_factory=list)
    status: RunStatus = RunStatus.SUCCESS
    termination_reason: str | None = None
    correlation_id: str | None = None

