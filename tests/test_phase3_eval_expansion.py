from __future__ import annotations

import json
from pathlib import Path

from argus.evals.report import build_report


def test_build_report_is_reproducible_for_same_seed() -> None:
    report_a = build_report(seed=1337)
    report_b = build_report(seed=1337)
    assert report_a == report_b


def test_report_has_scenario_breakdown_keys() -> None:
    report = build_report(seed=1337)
    assert "by_scenario" in report["main_eval"]
    assert "by_scenario" in report["failure_injection_eval"]
    assert "network" in report["main_eval"]["by_scenario"]
    assert "permanent" in report["failure_injection_eval"]["by_scenario"]


def test_report_matches_seeded_snapshot() -> None:
    report = build_report(seed=1337)
    snapshot_path = Path(__file__).parent / "fixtures" / "report_snapshot_seed_1337.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert report == snapshot
