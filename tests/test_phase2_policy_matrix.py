from __future__ import annotations

from argus.agent.orchestrator import Orchestrator
from argus.agent.schemas import ErrorClassification, PlanStep, RunStatus, StepRequirement, TaskPlan
from argus.tools.reliability import RetryPolicy
from argus.tools.simulated_tools import DeterministicToolEngine


def _orchestrator(scripts: dict[str, list[str]], use_reliability_layer: bool = True) -> Orchestrator:
    return Orchestrator(
        tools=DeterministicToolEngine(scripts=scripts),
        use_reliability_layer=use_reliability_layer,
        retry_policy=RetryPolicy(max_retries=2, base_delay_s=0.0, jitter_s=0.0),
        do_sleep=False,
    )


def test_required_transient_failure_is_policy_exhausted() -> None:
    key = "required-transient"
    scripts = {
        f"{key}:primary_search:normal": ["timeout", "timeout", "timeout"],
    }
    plan = TaskPlan(
        task_id=key,
        expected_success=False,
        steps=[PlanStep(step_id=f"{key}-s1", tool_name="primary_search", payload={"key": key})],
    )
    trace = _orchestrator(scripts).run(plan)
    assert trace.success is False
    assert trace.status == RunStatus.FAILED_POLICY_EXHAUSTED
    assert trace.steps[0].error_classification == ErrorClassification.TRANSIENT


def test_required_permanent_failure_is_required_failure_status() -> None:
    key = "required-permanent"
    scripts = {
        f"{key}:primary_search:normal": ["permanent"],
    }
    plan = TaskPlan(
        task_id=key,
        expected_success=False,
        steps=[PlanStep(step_id=f"{key}-s1", tool_name="primary_search", payload={"key": key})],
    )
    trace = _orchestrator(scripts).run(plan)
    assert trace.success is False
    assert trace.status == RunStatus.FAILED_REQUIRED_STEP
    assert trace.steps[0].error_classification == ErrorClassification.PERMANENT


def test_optional_permanent_failure_degrades_without_failing_run() -> None:
    key = "optional-permanent"
    scripts = {
        f"{key}:primary_search:normal": ["permanent"],
        f"{key}:primary_summarize:normal": ["ok"],
    }
    plan = TaskPlan(
        task_id=key,
        expected_success=True,
        steps=[
            PlanStep(
                step_id=f"{key}-optional",
                tool_name="primary_search",
                payload={"key": key},
                requirement=StepRequirement.OPTIONAL,
            ),
            PlanStep(
                step_id=f"{key}-required",
                tool_name="primary_summarize",
                payload={"key": key},
                requirement=StepRequirement.REQUIRED,
            ),
        ],
    )
    trace = _orchestrator(scripts).run(plan)
    assert trace.success is True
    assert trace.status == RunStatus.PARTIAL_SUCCESS_OPTIONAL_DEGRADED
    assert trace.optional_failures == [f"{key}-optional"]


def test_max_attempts_override_prevents_extra_retries() -> None:
    key = "attempt-override"
    scripts = {
        f"{key}:primary_search:normal": ["timeout", "ok"],
    }
    plan = TaskPlan(
        task_id=key,
        expected_success=False,
        steps=[
            PlanStep(
                step_id=f"{key}-s1",
                tool_name="primary_search",
                payload={"key": key},
                max_step_attempts_override=1,
            )
        ],
    )
    trace = _orchestrator(scripts).run(plan)
    assert trace.success is False
    assert trace.steps[0].attempts == 1


def test_timeout_budget_is_enforced_and_classified_transient() -> None:
    key = "timeout-budget"
    scripts = {
        f"{key}:primary_search:normal": ["ok"],
        f"{key}:backup_search:fallback": ["ok"],
    }
    plan = TaskPlan(
        task_id=key,
        expected_success=True,
        steps=[
            PlanStep(
                step_id=f"{key}-s1",
                tool_name="primary_search",
                payload={"key": key, "simulated_latency_ms": 250.0},
                fallback_tool_name="backup_search",
                step_timeout_ms=200,
            )
        ],
    )
    trace = _orchestrator(scripts).run(plan)
    assert trace.success is False
    assert trace.status == RunStatus.FAILED_POLICY_EXHAUSTED
    assert trace.steps[0].error_classification == ErrorClassification.TRANSIENT
