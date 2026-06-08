from __future__ import annotations

import json
from pathlib import Path

from argus.evals.harness import run_suite
from argus.evals.suites import make_injected_failure_suite, make_main_eval_suite, make_scripts


def pct(value: float) -> float:
    return round(value * 100, 1)


def main() -> None:
    scripts = make_scripts()

    main_tasks = make_main_eval_suite()
    failure_tasks = make_injected_failure_suite()

    main_baseline = run_suite(main_tasks, scripts, use_reliability_layer=False)
    main_reliable = run_suite(main_tasks, scripts, use_reliability_layer=True)

    fail_baseline = run_suite(failure_tasks, scripts, use_reliability_layer=False)
    fail_reliable = run_suite(failure_tasks, scripts, use_reliability_layer=True)

    report = {
        "main_eval": {
            "baseline": {
                "passed": main_baseline.succeeded,
                "total": main_baseline.total,
                "rate": main_baseline.rate,
                "rate_pct": pct(main_baseline.rate),
            },
            "with_reliability": {
                "passed": main_reliable.succeeded,
                "total": main_reliable.total,
                "rate": main_reliable.rate,
                "rate_pct": pct(main_reliable.rate),
            },
        },
        "failure_injection_eval": {
            "baseline": {
                "passed": fail_baseline.succeeded,
                "total": fail_baseline.total,
                "rate": fail_baseline.rate,
                "rate_pct": pct(fail_baseline.rate),
            },
            "with_reliability": {
                "passed": fail_reliable.succeeded,
                "total": fail_reliable.total,
                "rate": fail_reliable.rate,
                "rate_pct": pct(fail_reliable.rate),
            },
        },
    }

    out_path = Path("eval_report.json")
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"\nWrote {out_path.resolve()}")


if __name__ == "__main__":
    main()

