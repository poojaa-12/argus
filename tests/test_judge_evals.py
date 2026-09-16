from __future__ import annotations

import json
from pathlib import Path

from argus.evals.judge.dataset import build_suite, dump_suite, load_suite
from argus.evals.judge.harness import run_compression_benchmark, run_judge_suite
from argus.evals.judge.report import build_judge_report


def test_suite_has_fifty_queries() -> None:
    dump_suite()
    suite = load_suite()
    assert len(suite) == 50
    assert suite[0]["id"] == "dr-001"
    assert suite[-1]["id"] == "dr-050"


def test_judge_metrics_on_full_suite() -> None:
    suite = build_suite()
    report = run_judge_suite(suite)
    assert report.total == 50
    assert report.tool_selection_accuracy >= 0.9
    assert report.hallucination_rate <= 0.15
    assert report.mean_llm_calls >= 3
    completed = [verdict for verdict in report.verdicts if verdict.status in {"completed", "rejected"}]
    assert len(completed) == 50


def test_compression_benchmark_reduces_tokens() -> None:
    reduction = run_compression_benchmark(build_suite()[:8])
    assert reduction >= 0.35


def test_judge_report_snapshot_shape() -> None:
    payload = build_judge_report()
    assert payload["total"] == 50
    assert "tool_selection_accuracy_pct" in payload
    snapshot_path = Path(__file__).parent / "fixtures" / "judge_report_summary.json"
    summary = {
        "total": payload["total"],
        "tool_selection_accuracy_pct": payload["tool_selection_accuracy_pct"],
        "hallucination_rate_pct": payload["hallucination_rate_pct"],
        "mean_llm_calls": round(payload["mean_llm_calls"], 2),
        "token_reduction_pct": payload["token_reduction_pct"],
    }
    if snapshot_path.exists():
        expected = json.loads(snapshot_path.read_text(encoding="utf-8"))
        assert summary == expected
    else:
        snapshot_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
