from __future__ import annotations

from typing import Any

from argus.evals.judge.schemas import ClaimCheck, JudgeSuiteReport, JudgeVerdict, ToolSelectionScore, TrajectoryStats
from argus.graph.policy import ScriptedPolicy
from argus.graph.runtime import GraphRuntime
from argus.observability.otel import TokenBudgetRecorder
from argus.runtime_config import RuntimeConfig
from argus.tools.research_tools import GraphToolEngine


def _equivalent(name: str, allowed: dict[str, list[str]]) -> set[str]:
    names = {name}
    names.update(allowed.get(name) or [])
    return names


def score_tool_selection(item: dict[str, Any], tool_events: list[dict[str, Any]]) -> ToolSelectionScore:
    expected = [str(tool["name"]) for tool in item.get("golden_tools") or []]
    actual = [str(event.get("tool_name")) for event in tool_events]
    allowed = item.get("allowed_equivalents") or {}
    remaining = list(actual)
    correct = 0
    for name in expected:
        options = _equivalent(name, allowed)
        hit_index = next((i for i, got in enumerate(remaining) if got in options), None)
        if hit_index is None:
            continue
        correct += 1
        remaining.pop(hit_index)
    total = max(len(expected), 1)
    return ToolSelectionScore(
        expected=expected,
        actual=actual,
        correct=correct,
        total=total,
        accuracy=correct / total,
    )


def _tool_context(state: dict[str, Any], item: dict[str, Any]) -> str:
    chunks = list(item.get("source_claims") or [])
    for finding in state.get("research_findings") or []:
        chunks.append(str(finding.get("content") or ""))
    for event in state.get("tool_events") or []:
        output = event.get("output") or {}
        chunks.append(str(output.get("content") or ""))
    feedback = state.get("human_feedback")
    if feedback:
        chunks.append(str(feedback))
    return " ".join(chunks).lower()


def score_hallucinations(state: dict[str, Any], item: dict[str, Any]) -> tuple[float, list[ClaimCheck]]:
    answer = str(state.get("final_answer") or "")
    context = _tool_context(state, item)
    raw_claims = [part.strip() for part in answer.replace("!", ".").split(".") if part.strip()]
    if not raw_claims:
        return 0.0, []
    checks: list[ClaimCheck] = []
    missed = 0
    for claim in raw_claims:
        needle = claim.lower()
        entailed = needle in context or all(token in context for token in needle.split()[:6])
        # human_feedback echoes are entailed
        if "human_feedback=" in needle:
            entailed = True
        if not entailed:
            missed += 1
        checks.append(ClaimCheck(claim=claim, entailed=entailed, source="tool_context" if entailed else None))
    return missed / len(checks), checks


def _catalog(suite: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in suite}


def run_judge_item(
    item: dict[str, Any],
    *,
    runtime: GraphRuntime | None = None,
    resume_feedback: str = "use operator_records",
) -> JudgeVerdict:
    graph = runtime or GraphRuntime.create()
    state = graph.start(item["query"], run_id=item["id"], query_id=item["id"])
    if state.get("status") == "interrupted":
        state = graph.resume(item["id"], resume_feedback)
    selection = score_tool_selection(item, list(state.get("tool_events") or []))
    hallucination_rate, claims = score_hallucinations(state, item)
    recorder = graph.ctx.recorder
    reduction = recorder.reduction_rate if recorder.compressions else None
    return JudgeVerdict(
        query_id=item["id"],
        tool_selection=selection,
        hallucination_rate=hallucination_rate,
        claims=claims,
        trajectory=TrajectoryStats(
            llm_calls=int(state.get("llm_calls") or 0),
            tool_calls=len(state.get("tool_events") or []),
            operator_iterations=int(state.get("operator_iterations") or 0),
        ),
        token_reduction=reduction,
        status=str(state.get("status") or "completed"),
    )


def run_judge_suite(
    suite: list[dict[str, Any]],
    *,
    seed: int = 1337,
    bloat_chars: int = 0,
    context_window: int | None = None,
) -> JudgeSuiteReport:
    config = RuntimeConfig(eval_seed=seed, context_window=context_window or 8192)
    recorder = TokenBudgetRecorder()
    tools = GraphToolEngine(corpus=_corpus_from_suite(suite), bloat_chars=bloat_chars)
    runtime = GraphRuntime.create(
        config=config,
        policy=ScriptedPolicy(catalog=_catalog(suite)),
        tools=tools,
        recorder=recorder,
    )
    verdicts = [run_judge_item(item, runtime=runtime) for item in suite]
    total = len(verdicts) or 1
    accuracy = sum(v.tool_selection.accuracy for v in verdicts) / total
    hallucination = sum(v.hallucination_rate for v in verdicts) / total
    mean_llm = sum(v.trajectory.llm_calls for v in verdicts) / total
    return JudgeSuiteReport(
        seed=seed,
        total=len(verdicts),
        tool_selection_accuracy=accuracy,
        hallucination_rate=hallucination,
        mean_llm_calls=mean_llm,
        token_reduction=recorder.reduction_rate if recorder.compressions else None,
        verdicts=verdicts,
    )


def _corpus_from_suite(suite: list[dict[str, Any]]) -> dict[str, str]:
    from argus.evals.judge.dataset import build_corpus

    return build_corpus(suite)


def run_compression_benchmark(suite: list[dict[str, Any]], *, seed: int = 1337) -> float:
    sample = suite[:8]
    report = run_judge_suite(sample, seed=seed, bloat_chars=8000, context_window=128)
    return float(report.token_reduction or 0.0)
