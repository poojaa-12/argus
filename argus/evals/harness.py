from __future__ import annotations

from dataclasses import dataclass

from argus.agent.orchestrator import Orchestrator
from argus.agent.schemas import TaskPlan
from argus.tools.reliability import RetryPolicy
from argus.tools.simulated_tools import DeterministicToolEngine


@dataclass
class EvalResult:
    total: int
    succeeded: int

    @property
    def rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.succeeded / self.total


def run_suite(
    tasks: list[TaskPlan],
    scripts: dict[str, list[str]],
    use_reliability_layer: bool,
) -> EvalResult:
    passed = 0
    for task in tasks:
        tools = DeterministicToolEngine(scripts=scripts)
        orchestrator = Orchestrator(
            tools=tools,
            use_reliability_layer=use_reliability_layer,
            retry_policy=RetryPolicy(max_retries=2, base_delay_s=0.0, jitter_s=0.0),
            do_sleep=False,
        )
        trace = orchestrator.run(task)
        if trace.success:
            passed += 1
    return EvalResult(total=len(tasks), succeeded=passed)

