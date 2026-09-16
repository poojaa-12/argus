from __future__ import annotations

import json
from pathlib import Path

from argus.evals.judge.dataset import dump_suite, load_suite
from argus.evals.judge.harness import run_compression_benchmark, run_judge_suite
from argus.evals.report import write_json_atomic


def build_judge_report(seed: int = 1337) -> dict:
    dump_suite()
    suite = load_suite()
    report = run_judge_suite(suite, seed=seed)
    token_reduction = run_compression_benchmark(suite, seed=seed)
    payload = report.model_dump()
    payload["token_reduction"] = token_reduction
    payload["token_reduction_pct"] = round(token_reduction * 100, 1)
    payload["tool_selection_accuracy_pct"] = round(report.tool_selection_accuracy * 100, 1)
    payload["hallucination_rate_pct"] = round(report.hallucination_rate * 100, 1)
    payload["verdicts"] = [verdict.model_dump() for verdict in report.verdicts]
    return payload


def main() -> None:
    payload = build_judge_report()
    out_path = Path("eval_report_judge.json")
    write_json_atomic(out_path, payload)
    summary = {
        "total": payload["total"],
        "tool_selection_accuracy_pct": payload["tool_selection_accuracy_pct"],
        "hallucination_rate_pct": payload["hallucination_rate_pct"],
        "mean_llm_calls": payload["mean_llm_calls"],
        "token_reduction_pct": payload["token_reduction_pct"],
    }
    print(json.dumps(summary, indent=2))
    print(f"\nWrote {out_path.resolve()}")


if __name__ == "__main__":
    main()
