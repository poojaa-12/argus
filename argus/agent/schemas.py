from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StepRequirement(str, Enum):
    REQUIRED = "required"
    OPTIONAL = "optional"


@dataclass
class PlanStep:
    step_id: str
    tool_name: str
    payload: dict[str, Any]
    requirement: StepRequirement = StepRequirement.REQUIRED
    fallback_tool_name: str | None = None


@dataclass
class TaskPlan:
    task_id: str
    expected_success: bool
    steps: list[PlanStep]


@dataclass
class ToolCallResult:
    ok: bool
    output: dict[str, Any] | None = None
    error_type: str | None = None
    error_message: str | None = None
    attempts: int = 1
    used_fallback: bool = False


@dataclass
class StepTrace:
    step_id: str
    tool_name: str
    requirement: StepRequirement
    success: bool
    attempts: int
    used_fallback: bool
    error_type: str | None = None


@dataclass
class RunTrace:
    task_id: str
    success: bool
    steps: list[StepTrace] = field(default_factory=list)
    failed_required_step: str | None = None
    optional_failures: list[str] = field(default_factory=list)

