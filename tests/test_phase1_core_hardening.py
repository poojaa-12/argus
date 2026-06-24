from __future__ import annotations

import json
from pathlib import Path

from argus.agent.orchestrator import Orchestrator
from argus.agent.schemas import PlanStep, RunStatus, StepRequirement, TaskPlan
from argus.agent.validators import validate_task_plan
from argus.evals.report import write_json_atomic
from argus.tools.reliability import RetryPolicy
from argus.tools.simulated_tools import DeterministicToolEngine


def test_validate_task_plan_rejects_duplicate_step_ids() -> None:
    plan = TaskPlan(
        task_id="dup-step",
        expected_success=False,
        steps=[
            PlanStep(step_id="s1", tool_name="primary_search", payload={"key": "x"}),
            PlanStep(step_id="s1", tool_name="primary_summarize", payload={"key": "x"}),
        ],
    )
    try:
        validate_task_plan(plan, available_tools={"primary_search", "primary_summarize"})
        assert False, "expected validation error"
    except ValueError as err:
        assert "duplicate step_id" in str(err)


def test_orchestrator_records_status_and_latency() -> None:
    scripts = {
        "latency:primary_search:normal": ["ok"],
        "latency:primary_summarize:normal": ["ok"],
    }
    tools = DeterministicToolEngine(scripts=scripts)
    orchestrator = Orchestrator(
        tools=tools,
        use_reliability_layer=True,
        retry_policy=RetryPolicy(max_retries=2, base_delay_s=0.0, jitter_s=0.0),
        do_sleep=False,
    )
    plan = TaskPlan(
        task_id="latency",
        expected_success=True,
        steps=[
            PlanStep(
                step_id="latency-s1",
                tool_name="primary_search",
                payload={"key": "latency"},
                requirement=StepRequirement.REQUIRED,
            ),
            PlanStep(
                step_id="latency-s2",
                tool_name="primary_summarize",
                payload={"key": "latency"},
                requirement=StepRequirement.REQUIRED,
            ),
        ],
    )
    trace = orchestrator.run(plan)
    assert trace.success is True
    assert trace.status == RunStatus.SUCCESS
    assert trace.termination_reason == "completed"
    assert len(trace.steps) == 2
    assert trace.steps[0].latency_ms is not None
    assert trace.steps[0].latency_ms >= 0


def test_write_json_atomic_round_trips(tmp_path: Path) -> None:
    payload = {"a": 1, "nested": {"ok": True}}
    out = tmp_path / "report.json"
    write_json_atomic(out, payload)
    read_back = json.loads(out.read_text(encoding="utf-8"))
    assert read_back == payload
