from __future__ import annotations

from dataclasses import dataclass

from argus.agent.schemas import PlanStep, RunTrace, StepTrace, StepRequirement, TaskPlan, ToolCallResult
from argus.tools.reliability import RetryPolicy, error_type_name, is_retryable, sleep_for_retry
from argus.tools.simulated_tools import DeterministicToolEngine


@dataclass
class Orchestrator:
    tools: DeterministicToolEngine
    use_reliability_layer: bool
    retry_policy: RetryPolicy
    do_sleep: bool = False

    def _call_step(self, step: PlanStep) -> ToolCallResult:
        attempts = 0
        last_error: Exception | None = None

        while True:
            attempts += 1
            try:
                output = self.tools.call(step.tool_name, step.payload)
                return ToolCallResult(ok=True, output=output, attempts=attempts)
            except Exception as err:  # noqa: BLE001 - capturing for retry simulation
                last_error = err
                if not self.use_reliability_layer:
                    return ToolCallResult(
                        ok=False,
                        error_type=error_type_name(err),
                        error_message=str(err),
                        attempts=attempts,
                    )

                if is_retryable(err) and attempts <= (self.retry_policy.max_retries + 1):
                    # attempts includes first attempt; retry indices start from 0
                    if attempts <= self.retry_policy.max_retries:
                        sleep_for_retry(self.retry_policy, attempts - 1, self.do_sleep)
                        continue

                break

        if self.use_reliability_layer and step.fallback_tool_name:
            try:
                fallback_payload = dict(step.payload)
                fallback_payload["mode"] = "fallback"
                output = self.tools.call(step.fallback_tool_name, fallback_payload)
                return ToolCallResult(ok=True, output=output, attempts=attempts, used_fallback=True)
            except Exception as fallback_err:  # noqa: BLE001
                return ToolCallResult(
                    ok=False,
                    error_type=error_type_name(fallback_err),
                    error_message=str(fallback_err),
                    attempts=attempts,
                    used_fallback=True,
                )

        return ToolCallResult(
            ok=False,
            error_type=error_type_name(last_error) if last_error else "UnknownError",
            error_message=str(last_error) if last_error else "unknown failure",
            attempts=attempts,
        )

    def run(self, plan: TaskPlan) -> RunTrace:
        trace = RunTrace(task_id=plan.task_id, success=True)

        for step in plan.steps:
            result = self._call_step(step)
            trace.steps.append(
                StepTrace(
                    step_id=step.step_id,
                    tool_name=step.tool_name,
                    requirement=step.requirement,
                    success=result.ok,
                    attempts=result.attempts,
                    used_fallback=result.used_fallback,
                    error_type=result.error_type,
                )
            )

            if result.ok:
                continue

            if self.use_reliability_layer and step.requirement == StepRequirement.OPTIONAL:
                trace.optional_failures.append(step.step_id)
                continue

            trace.success = False
            if step.requirement == StepRequirement.REQUIRED:
                trace.failed_required_step = step.step_id
            break

        return trace

