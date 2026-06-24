from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile

from argus.evals.harness import EvalResult, run_suite_with_scenario_breakdown
from argus.evals.suites import make_injected_failure_suite, make_main_eval_suite, make_scripts
from argus.runtime_config import RuntimeConfig
from argus.tools.reliability import RetryPolicy

DEFAULT_SEED = 1337


def pct(value: float) -> float:
    return round(value * 100, 1)


def serialize_eval_result(result: EvalResult) -> dict[str, float | int]:
    return {
        "passed": result.succeeded,
        "total": result.total,
        "rate": result.rate,
        "rate_pct": pct(result.rate),
        "degraded": result.degraded,
        "degraded_rate": result.degraded_rate,
        "degraded_rate_pct": pct(result.degraded_rate),
    }


def build_scenario_breakdown(
    baseline_by_scenario: dict[str, EvalResult],
    reliable_by_scenario: dict[str, EvalResult],
) -> dict[str, dict[str, float | int | dict[str, float | int]]]:
    scenario_names = sorted(set(baseline_by_scenario) | set(reliable_by_scenario))
    breakdown: dict[str, dict[str, float | int | dict[str, float | int]]] = {}
    for scenario_name in scenario_names:
        baseline = baseline_by_scenario.get(scenario_name, EvalResult(total=0, succeeded=0, degraded=0))
        reliable = reliable_by_scenario.get(scenario_name, EvalResult(total=0, succeeded=0, degraded=0))
        breakdown[scenario_name] = {
            "baseline": serialize_eval_result(baseline),
            "with_reliability": serialize_eval_result(reliable),
            "uplift_rate_points": pct(reliable.rate - baseline.rate),
            "degradation_delta_points": pct(reliable.degraded_rate - baseline.degraded_rate),
        }
    return breakdown


def write_json_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as tmp:
        json.dump(payload, tmp, indent=2)
        tmp.write("\n")
        tmp_path = tmp.name
    os.replace(tmp_path, path)


def load_runtime_config() -> RuntimeConfig:
    config_path = os.getenv("ARGUS_RUNTIME_CONFIG")
    if config_path:
        try:
            return RuntimeConfig.from_file(config_path)
        except Exception as err:  # noqa: BLE001
            raise ValueError(f"Failed to load ARGUS_RUNTIME_CONFIG={config_path}: {err}") from err
    try:
        return RuntimeConfig.from_env()
    except Exception as err:  # noqa: BLE001
        raise ValueError(f"Failed to parse runtime config from environment: {err}") from err


def build_report(seed: int = DEFAULT_SEED, config: RuntimeConfig | None = None) -> dict:
    runtime_config = config or RuntimeConfig()
    retry_policy = RetryPolicy(
        max_retries=runtime_config.max_retries,
        base_delay_s=runtime_config.base_delay_s,
        jitter_s=runtime_config.jitter_s,
    )
    scripts = make_scripts()

    main_tasks = make_main_eval_suite()
    failure_tasks = make_injected_failure_suite()

    main_baseline, main_baseline_by_scenario = run_suite_with_scenario_breakdown(
        main_tasks,
        scripts,
        use_reliability_layer=False,
        seed=seed,
        retry_policy=retry_policy,
        default_step_timeout_ms=runtime_config.default_step_timeout_ms,
    )
    main_reliable, main_reliable_by_scenario = run_suite_with_scenario_breakdown(
        main_tasks,
        scripts,
        use_reliability_layer=True,
        seed=seed,
        retry_policy=retry_policy,
        default_step_timeout_ms=runtime_config.default_step_timeout_ms,
    )

    fail_baseline, fail_baseline_by_scenario = run_suite_with_scenario_breakdown(
        failure_tasks,
        scripts,
        use_reliability_layer=False,
        seed=seed,
        retry_policy=retry_policy,
        default_step_timeout_ms=runtime_config.default_step_timeout_ms,
    )
    fail_reliable, fail_reliable_by_scenario = run_suite_with_scenario_breakdown(
        failure_tasks,
        scripts,
        use_reliability_layer=True,
        seed=seed,
        retry_policy=retry_policy,
        default_step_timeout_ms=runtime_config.default_step_timeout_ms,
    )

    return {
        "seed": seed,
        "runtime_config": {
            "max_retries": runtime_config.max_retries,
            "base_delay_s": runtime_config.base_delay_s,
            "jitter_s": runtime_config.jitter_s,
            "default_step_timeout_ms": runtime_config.default_step_timeout_ms,
        },
        "main_eval": {
            "baseline": serialize_eval_result(main_baseline),
            "with_reliability": serialize_eval_result(main_reliable),
            "by_scenario": build_scenario_breakdown(main_baseline_by_scenario, main_reliable_by_scenario),
        },
        "failure_injection_eval": {
            "baseline": serialize_eval_result(fail_baseline),
            "with_reliability": serialize_eval_result(fail_reliable),
            "by_scenario": build_scenario_breakdown(fail_baseline_by_scenario, fail_reliable_by_scenario),
        },
    }


def main() -> None:
    try:
        runtime_config = load_runtime_config()
    except ValueError as err:
        print(f"Error: {err}")
        raise SystemExit(2) from err
    seed = runtime_config.eval_seed
    report = build_report(seed=seed, config=runtime_config)
    out_path = Path("eval_report.json")
    write_json_atomic(out_path, report)
    print(json.dumps(report, indent=2))
    print(f"\nWrote {out_path.resolve()}")


if __name__ == "__main__":
    main()

