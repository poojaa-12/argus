from __future__ import annotations

from argus.agent.schemas import PlanStep, StepRequirement, TaskPlan


def make_main_eval_suite() -> list[TaskPlan]:
    tasks: list[TaskPlan] = []
    # 39 easy tasks that always pass.
    for i in range(1, 40):
        key = f"easy-{i:02d}"
        tasks.append(
            TaskPlan(
                task_id=key,
                expected_success=True,
                scenario_tag="network",
                steps=[
                    PlanStep(
                        step_id=f"{key}-s1",
                        tool_name="primary_search",
                        payload={"key": key},
                        requirement=StepRequirement.REQUIRED,
                    ),
                    PlanStep(
                        step_id=f"{key}-s2",
                        tool_name="primary_summarize",
                        payload={"key": key},
                        requirement=StepRequirement.REQUIRED,
                    ),
                ],
            )
        )

    # 11 fragile tasks that fail without reliability.
    # 7 are recoverable through retries/fallback; 4 are hard failures even with reliability.
    for i in range(1, 12):
        key = f"fragile-{i:02d}"
        tasks.append(
            TaskPlan(
                task_id=key,
                expected_success=True,
                scenario_tag="permanent",
                steps=[
                    PlanStep(
                        step_id=f"{key}-required-timeout",
                        tool_name="primary_search",
                        payload={"key": key},
                        requirement=StepRequirement.REQUIRED,
                        fallback_tool_name="backup_search",
                    ),
                    PlanStep(
                        step_id=f"{key}-optional-enrich",
                        tool_name="primary_enrich",
                        payload={"key": key},
                        requirement=StepRequirement.OPTIONAL,
                        fallback_tool_name="backup_enrich",
                    ),
                ],
            )
        )
    return tasks


def make_injected_failure_suite() -> list[TaskPlan]:
    tasks: list[TaskPlan] = []
    for i in range(1, 21):
        key = f"injected-{i:02d}"

        requirement = StepRequirement.REQUIRED if i <= 18 else StepRequirement.OPTIONAL
        tasks.append(
            TaskPlan(
                task_id=key,
                expected_success=True,
                scenario_tag=(
                    "network" if i <= 6 else "parser" if i <= 12 else "executor" if i <= 18 else "permanent"
                ),
                steps=[
                    PlanStep(
                        step_id=f"{key}-faulty-step",
                        tool_name="primary_search",
                        payload={"key": key},
                        requirement=requirement,
                        fallback_tool_name="backup_search",
                    ),
                    PlanStep(
                        step_id=f"{key}-final",
                        tool_name="primary_summarize",
                        payload={"key": key},
                        requirement=StepRequirement.REQUIRED,
                    ),
                ],
            )
        )
    return tasks


def make_scripts() -> dict[str, list[str]]:
    scripts: dict[str, list[str]] = {}

    # Easy tasks: all primary tools succeed.
    for i in range(1, 40):
        key = f"easy-{i:02d}"
        scripts[f"{key}:primary_search:normal"] = ["ok"]
        scripts[f"{key}:primary_summarize:normal"] = ["ok"]

    # Fragile tasks 1-7: required step recoverable via retry/fallback.
    # Fragile tasks 8-11: required step hard-fails even with fallback.
    for i in range(1, 12):
        key = f"fragile-{i:02d}"
        if i <= 7:
            scripts[f"{key}:primary_search:normal"] = ["timeout", "ok"]
            scripts[f"{key}:backup_search:fallback"] = ["ok"]
        else:
            scripts[f"{key}:primary_search:normal"] = ["permanent"]
            scripts[f"{key}:backup_search:fallback"] = ["permanent"]
        scripts[f"{key}:primary_enrich:normal"] = ["permanent"]
        scripts[f"{key}:backup_enrich:fallback"] = ["ok"]

    # Injected failure suite:
    # Tasks 1-12: no injected failure (baseline recovers 12/20 overall).
    for i in range(1, 13):
        key = f"injected-{i:02d}"
        scripts[f"{key}:primary_search:normal"] = ["ok"]
        scripts[f"{key}:backup_search:fallback"] = ["ok"]
        scripts[f"{key}:primary_summarize:normal"] = ["ok"]

    # Tasks 13-18: permanent primary failure, solved by fallback.
    for i in range(13, 19):
        key = f"injected-{i:02d}"
        scripts[f"{key}:primary_search:normal"] = ["permanent"]
        scripts[f"{key}:backup_search:fallback"] = ["ok"]
        scripts[f"{key}:primary_summarize:normal"] = ["ok"]

    # Tasks 19-20: optional faulty step fails; final step also fails.
    # This keeps reliability recovery at 18/20 (90%) instead of 100%.
    for i in range(19, 21):
        key = f"injected-{i:02d}"
        scripts[f"{key}:primary_search:normal"] = ["permanent"]
        scripts[f"{key}:backup_search:fallback"] = ["permanent"]
        scripts[f"{key}:primary_summarize:normal"] = ["permanent"]

    return scripts

