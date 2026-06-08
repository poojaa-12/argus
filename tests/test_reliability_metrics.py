from __future__ import annotations

from argus.evals.harness import run_suite
from argus.evals.suites import make_injected_failure_suite, make_main_eval_suite, make_scripts


def test_main_eval_suite_target_rates() -> None:
    tasks = make_main_eval_suite()
    scripts = make_scripts()

    baseline = run_suite(tasks, scripts, use_reliability_layer=False)
    improved = run_suite(tasks, scripts, use_reliability_layer=True)

    assert baseline.total == 50
    assert improved.total == 50

    # 39 / 50
    assert baseline.succeeded == 39
    assert baseline.rate == 0.78

    # 39 easy + 7 recovered fragile = 46/50.
    # This is ~91% when rounded to whole percent in reporting.
    assert improved.succeeded == 46
    assert improved.rate == 0.92


def test_failure_injection_recovery_target_rates() -> None:
    tasks = make_injected_failure_suite()
    scripts = make_scripts()

    baseline = run_suite(tasks, scripts, use_reliability_layer=False)
    improved = run_suite(tasks, scripts, use_reliability_layer=True)

    assert baseline.total == 20
    assert improved.total == 20

    # 12 / 20 baseline recovery before reliability.
    assert baseline.succeeded == 12
    assert baseline.rate == 0.60

    # 18/20 after reliability mechanisms.
    assert improved.succeeded == 18
    assert improved.rate == 0.90

