from __future__ import annotations

from dataclasses import dataclass, field
import time

from argus.agent.schemas import ErrorClassification, PlanStep, RunStatus, RunTrace, StepTrace, StepRequirement, TaskPlan, ToolCallResult
from argus.agent.validators import validate_task_plan
from argus.observability import MetricsExporter, NoopMetricsExporter, NoopStructuredLogger, StructuredLogger
from argus.tools.reliability import RetryPolicy, classify_error, error_type_name, is_retryable, max_attempts_for_step, sleep_for_retry
from argus.tools.errors import ToolTimeoutError
from argus.tools.simulated_tools import DeterministicToolEngine


@dataclass
class Orchestrator:
    tools: DeterministicToolEngine
    use_reliability_layer: bool
    retry_policy: RetryPolicy
    do_sleep: bool = False
    default_step_timeout_ms: int | None = None
    logger: StructuredLogger = field(default_factory=NoopStructuredLogger)
    metrics: MetricsExporter = field(default_factory=NoopMetricsExporter)

    def _call_step(self, step: PlanStep) -> ToolCallResult:
        attempts = 0
        last_error: Exception | None = None
        max_attempts = max_attempts_for_step(step, self.retry_policy)
        timeout_budget_ms = (
            step.step_timeout_ms if step.step_timeout_ms is not None else self.default_step_timeout_ms
        )

        while attempts < max_attempts:
            attempts += 1
            try:
                output = self.tools.call(step.tool_name, step.payload)
                if timeout_budget_ms is not None:
                    simulated_latency_ms = float(output.get("simulated_latency_ms", 0.0))
                    if simulated_latency_ms > timeout_budget_ms:
                        raise ToolTimeoutError(
                            f"{step.tool_name} exceeded timeout budget: "
                            f"{simulated_latency_ms:.2f}ms > {timeout_budget_ms}ms"
                        )
                return ToolCallResult(ok=True, output=output, attempts=attempts)
            except Exception as err:  # noqa: BLE001 - capturing for retry simulation
                last_error = err
                if not self.use_reliability_layer:
                    return ToolCallResult(
                        ok=False,
                        error_type=error_type_name(err),
                        error_message=str(err),
                        attempts=attempts,
                        error_classification=classify_error(err),
                    )

                if is_retryable(err) and attempts < max_attempts:
                    # retry indices start at 0 for backoff calculation
                    sleep_for_retry(self.retry_policy, attempts - 1, self.do_sleep)
                    continue

                break

        if self.use_reliability_layer and step.fallback_tool_name:
            try:
                fallback_payload = dict(step.payload)
                fallback_payload["mode"] = "fallback"
                output = self.tools.call(step.fallback_tool_name, fallback_payload)
                if timeout_budget_ms is not None:
                    simulated_latency_ms = float(output.get("simulated_latency_ms", 0.0))
                    if simulated_latency_ms > timeout_budget_ms:
                        raise ToolTimeoutError(
                            f"{step.fallback_tool_name} exceeded timeout budget: "
                            f"{simulated_latency_ms:.2f}ms > {timeout_budget_ms}ms"
                        )
                return ToolCallResult(ok=True, output=output, attempts=attempts, used_fallback=True)
            except Exception as fallback_err:  # noqa: BLE001
                return ToolCallResult(
                    ok=False,
                    error_type=error_type_name(fallback_err),
                    error_message=str(fallback_err),
                    attempts=attempts,
                    used_fallback=True,
                    error_classification=classify_error(fallback_err),
                )

        return ToolCallResult(
            ok=False,
            error_type=error_type_name(last_error) if last_error else "UnknownError",
            error_message=str(last_error) if last_error else "unknown failure",
            attempts=attempts,
            error_classification=classify_error(last_error),
        )

    def run(self, plan: TaskPlan) -> RunTrace:
        trace = RunTrace(task_id=plan.task_id, success=True, correlation_id=plan.correlation_id)
        self.logger.log_event(
            "run_started",
            task_id=plan.task_id,
            correlation_id=plan.correlation_id,
            step_count=len(plan.steps),
        )
        self.metrics.increment("argus_runs_started_total")
        try:
            available_tools = self.tools.available_tools()
            validate_task_plan(plan, available_tools=available_tools)
        except ValueError as err:
            trace.success = False
            trace.status = RunStatus.FAILED_VALIDATION
            trace.termination_reason = str(err)
            self.logger.log_event(
                "run_failed_validation",
                task_id=plan.task_id,
                correlation_id=plan.correlation_id,
                reason=str(err),
            )
            self.metrics.increment("argus_runs_failed_total", status=RunStatus.FAILED_VALIDATION.value)
            return trace

        for step in plan.steps:
            started = time.perf_counter()
            result = self._call_step(step)
            latency_ms = (time.perf_counter() - started) * 1000.0
            trace.steps.append(
                StepTrace(
                    step_id=step.step_id,
                    tool_name=step.tool_name,
                    requirement=step.requirement,
                    success=result.ok,
                    attempts=result.attempts,
                    used_fallback=result.used_fallback,
                    error_type=result.error_type,
                    error_classification=result.error_classification,
                    latency_ms=latency_ms,
                )
            )
            self.logger.log_event(
                "step_completed",
                task_id=plan.task_id,
                correlation_id=plan.correlation_id,
                step_id=step.step_id,
                success=result.ok,
                attempts=result.attempts,
                error_type=result.error_type,
                error_classification=(
                    result.error_classification.value if result.error_classification else None
                ),
                used_fallback=result.used_fallback,
                latency_ms=latency_ms,
            )
            self.metrics.increment(
                "argus_steps_total",
                status="success" if result.ok else "failure",
                requirement=step.requirement.value,
            )

            if result.ok:
                continue

            if self.use_reliability_layer and step.requirement == StepRequirement.OPTIONAL:
                trace.optional_failures.append(step.step_id)
                continue

            trace.success = False
            if step.requirement == StepRequirement.REQUIRED:
                trace.failed_required_step = step.step_id
                if (
                    self.use_reliability_layer
                    and result.error_classification == ErrorClassification.TRANSIENT
                ):
                    trace.status = RunStatus.FAILED_POLICY_EXHAUSTED
                    trace.termination_reason = "policy_exhausted_on_required_step"
                else:
                    trace.status = RunStatus.FAILED_REQUIRED_STEP
                    trace.termination_reason = "required_step_failed"
            break

        if trace.success:
            if trace.optional_failures:
                trace.status = RunStatus.PARTIAL_SUCCESS_OPTIONAL_DEGRADED
                trace.termination_reason = "completed_with_optional_failures"
            else:
                trace.status = RunStatus.SUCCESS
                trace.termination_reason = "completed"

        if trace.success:
            self.metrics.increment("argus_runs_succeeded_total", status=trace.status.value)
            self.logger.log_event(
                "run_completed",
                task_id=plan.task_id,
                correlation_id=plan.correlation_id,
                status=trace.status.value,
                optional_failure_count=len(trace.optional_failures),
            )
        else:
            self.metrics.increment("argus_runs_failed_total", status=trace.status.value)
            self.logger.log_event(
                "run_failed",
                task_id=plan.task_id,
                correlation_id=plan.correlation_id,
                status=trace.status.value,
                failed_required_step=trace.failed_required_step,
                termination_reason=trace.termination_reason,
            )

        return trace

