from __future__ import annotations

from dataclasses import dataclass
import random

from argus.agent.orchestrator import Orchestrator
from argus.agent.schemas import TaskPlan
from argus.tools.reliability import RetryPolicy
from argus.tools.simulated_tools import DeterministicToolEngine


@dataclass
class EvalResult:
    total: int
    succeeded: int
    degraded: int = 0

    @property
    def rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.succeeded / self.total

    @property
    def degraded_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.degraded / self.total


def run_tasks(
    tasks: list[TaskPlan],
    scripts: dict[str, list[str]],
    use_reliability_layer: bool,
    seed: int | None = None,
    retry_policy: RetryPolicy | None = None,
    default_step_timeout_ms: int | None = None,
) -> list[tuple[TaskPlan, bool, bool]]:
    if seed is not None:
        random.seed(seed)
    effective_retry_policy = retry_policy or RetryPolicy(max_retries=2, base_delay_s=0.0, jitter_s=0.0)
    outcomes: list[tuple[TaskPlan, bool, bool]] = []
    for task in tasks:
        tools = DeterministicToolEngine(scripts=scripts)
        orchestrator = Orchestrator(
            tools=tools,
            use_reliability_layer=use_reliability_layer,
            retry_policy=effective_retry_policy,
            do_sleep=False,
            default_step_timeout_ms=default_step_timeout_ms,
        )
        trace = orchestrator.run(task)
        outcomes.append((task, trace.success, bool(trace.optional_failures)))
    return outcomes


def _summarize_outcomes(
    outcomes: list[tuple[TaskPlan, bool, bool]],
) -> tuple[EvalResult, dict[str, EvalResult]]:
    total = len(outcomes)
    passed = 0
    degraded = 0
    grouped: dict[str, EvalResult] = {}
    for task, success, is_degraded in outcomes:
        if success:
            passed += 1
        if is_degraded:
            degraded += 1

        scenario_entry = grouped.setdefault(
            task.scenario_tag, EvalResult(total=0, succeeded=0, degraded=0)
        )
        scenario_entry.total += 1
        if success:
            scenario_entry.succeeded += 1
        if is_degraded:
            scenario_entry.degraded += 1

    return EvalResult(total=total, succeeded=passed, degraded=degraded), grouped


def run_suite(
    tasks: list[TaskPlan],
    scripts: dict[str, list[str]],
    use_reliability_layer: bool,
    seed: int | None = None,
    retry_policy: RetryPolicy | None = None,
    default_step_timeout_ms: int | None = None,
) -> EvalResult:
    outcomes = run_tasks(
        tasks,
        scripts,
        use_reliability_layer=use_reliability_layer,
        seed=seed,
        retry_policy=retry_policy,
        default_step_timeout_ms=default_step_timeout_ms,
    )
    result, _by_scenario = _summarize_outcomes(outcomes)
    return result


def run_suite_by_scenario(
    tasks: list[TaskPlan],
    scripts: dict[str, list[str]],
    use_reliability_layer: bool,
    seed: int | None = None,
    retry_policy: RetryPolicy | None = None,
    default_step_timeout_ms: int | None = None,
) -> dict[str, EvalResult]:
    outcomes = run_tasks(
        tasks,
        scripts,
        use_reliability_layer=use_reliability_layer,
        seed=seed,
        retry_policy=retry_policy,
        default_step_timeout_ms=default_step_timeout_ms,
    )
    _result, grouped = _summarize_outcomes(outcomes)
    return grouped


def run_suite_with_scenario_breakdown(
    tasks: list[TaskPlan],
    scripts: dict[str, list[str]],
    use_reliability_layer: bool,
    seed: int | None = None,
    retry_policy: RetryPolicy | None = None,
    default_step_timeout_ms: int | None = None,
) -> tuple[EvalResult, dict[str, EvalResult]]:
    outcomes = run_tasks(
        tasks,
        scripts,
        use_reliability_layer=use_reliability_layer,
        seed=seed,
        retry_policy=retry_policy,
        default_step_timeout_ms=default_step_timeout_ms,
    )
    return _summarize_outcomes(outcomes)

