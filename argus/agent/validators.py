from __future__ import annotations

from argus.agent.schemas import StepRequirement, TaskPlan


def validate_task_plan(plan: TaskPlan, available_tools: set[str] | None = None) -> None:
    if not plan.steps:
        raise ValueError(f"Task plan {plan.task_id} has no steps")

    seen_step_ids: set[str] = set()
    for step in plan.steps:
        if step.step_id in seen_step_ids:
            raise ValueError(f"Task plan {plan.task_id} has duplicate step_id: {step.step_id}")
        seen_step_ids.add(step.step_id)

        if not step.tool_name:
            raise ValueError(f"Step {step.step_id} has empty tool_name")

        if not isinstance(step.payload, dict):
            raise ValueError(f"Step {step.step_id} payload must be a dict")

        if "key" not in step.payload:
            raise ValueError(f"Step {step.step_id} payload must include key")

        if step.step_timeout_ms is not None and step.step_timeout_ms <= 0:
            raise ValueError(f"Step {step.step_id} step_timeout_ms must be positive")

        if step.max_step_attempts_override is not None and step.max_step_attempts_override <= 0:
            raise ValueError(f"Step {step.step_id} max_step_attempts_override must be positive")

        if step.requirement not in (StepRequirement.REQUIRED, StepRequirement.OPTIONAL):
            raise ValueError(f"Step {step.step_id} has unknown requirement: {step.requirement}")

        if available_tools is not None:
            if step.tool_name not in available_tools:
                raise ValueError(f"Step {step.step_id} unknown tool_name: {step.tool_name}")
            if step.fallback_tool_name and step.fallback_tool_name not in available_tools:
                raise ValueError(
                    f"Step {step.step_id} unknown fallback_tool_name: {step.fallback_tool_name}"
                )
