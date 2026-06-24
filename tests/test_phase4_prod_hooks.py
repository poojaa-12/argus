from __future__ import annotations

import json
from pathlib import Path

from argus.agent.orchestrator import Orchestrator
from argus.agent.schemas import PlanStep, RunStatus, StepRequirement, TaskPlan
from argus.evals.report import load_runtime_config
from argus.observability import InMemoryMetricsExporter, InMemoryStructuredLogger
from argus.tools.reliability import RetryPolicy
from argus.tools.simulated_tools import DeterministicToolEngine


def test_structured_logs_and_metrics_emit_terminal_states() -> None:
    key = "prod-hooks"
    scripts = {
        f"{key}:primary_search:normal": ["permanent"],
    }
    logger = InMemoryStructuredLogger()
    metrics = InMemoryMetricsExporter()
    orchestrator = Orchestrator(
        tools=DeterministicToolEngine(scripts=scripts),
        use_reliability_layer=True,
        retry_policy=RetryPolicy(max_retries=2, base_delay_s=0.0, jitter_s=0.0),
        logger=logger,
        metrics=metrics,
    )
    plan = TaskPlan(
        task_id=key,
        expected_success=False,
        correlation_id="corr-prod-hooks",
        steps=[
            PlanStep(
                step_id=f"{key}-s1",
                tool_name="primary_search",
                payload={"key": key},
                requirement=StepRequirement.REQUIRED,
            )
        ],
    )
    trace = orchestrator.run(plan)
    assert trace.status == RunStatus.FAILED_REQUIRED_STEP
    assert trace.failed_required_step == f"{key}-s1"
    assert trace.termination_reason == "required_step_failed"

    event_names = [event["event"] for event in logger.events]
    assert "run_started" in event_names
    assert "step_completed" in event_names
    assert "run_failed" in event_names

    run_failed_counter = (
        "argus_runs_failed_total",
        (("status", RunStatus.FAILED_REQUIRED_STEP.value),),
    )
    assert metrics.counters[run_failed_counter] == 1


def test_runtime_config_file_parsing_and_failure_message(tmp_path: Path, monkeypatch) -> None:
    good = tmp_path / "runtime-config.json"
    good.write_text(
        json.dumps(
            {
                "max_retries": 3,
                "base_delay_s": 0.01,
                "jitter_s": 0.0,
                "default_step_timeout_ms": 200,
                "eval_seed": 2026,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("ARGUS_RUNTIME_CONFIG", str(good))
    loaded = load_runtime_config()
    assert loaded.max_retries == 3
    assert loaded.default_step_timeout_ms == 200
    assert loaded.eval_seed == 2026

    bad = tmp_path / "bad-runtime-config.json"
    bad.write_text("{not-json", encoding="utf-8")
    monkeypatch.setenv("ARGUS_RUNTIME_CONFIG", str(bad))
    try:
        load_runtime_config()
        assert False, "expected load_runtime_config to fail for malformed JSON"
    except ValueError as err:
        assert "Failed to load ARGUS_RUNTIME_CONFIG" in str(err)
