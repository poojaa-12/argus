from __future__ import annotations

from argus.evals.judge.dataset import build_corpus, build_suite
from argus.graph.policy import ScriptedPolicy
from argus.graph.runtime import GraphRuntime
from argus.runtime_config import RuntimeConfig
from argus.tools.research_tools import GraphToolEngine


def _runtime(**kwargs) -> GraphRuntime:
    suite = build_suite()
    catalog = {item["id"]: item for item in suite}
    tools = kwargs.pop("tools", None) or GraphToolEngine(corpus=build_corpus(suite))
    config = kwargs.pop("config", RuntimeConfig())
    return GraphRuntime.create(
        config=config,
        policy=ScriptedPolicy(catalog=catalog),
        tools=tools,
        **kwargs,
    )


def test_graph_completes_research_task_with_parallel_subqueries() -> None:
    runtime = _runtime()
    item = build_suite()[0]
    state = runtime.start(item["query"], run_id="graph-basic", query_id=item["id"])
    assert state["status"] == "completed"
    assert len(state["subqueries"]) == 2
    assert len(state["research_findings"]) == 2
    assert state["final_answer"]
    assert state["llm_calls"] >= 4
    search_events = [event for event in state["tool_events"] if event["tool_name"] == "web_search"]
    assert len(search_events) == 2


def test_operator_cycles_through_tool_then_synthesize() -> None:
    runtime = _runtime()
    item = next(row for row in build_suite() if row["id"] == "dr-049")
    state = runtime.start(item["query"], run_id="graph-write", query_id=item["id"])
    assert state["status"] == "interrupted"
    assert (state.get("pending_action") or {}).get("tool_name") == "db_write"
    resumed = runtime.resume("graph-write", "approve")
    assert resumed["status"] == "completed"
    names = [event["tool_name"] for event in resumed["tool_events"]]
    assert "web_search" in names
    assert "db_write" in names
    assert resumed["operator_iterations"] >= 2


def test_recursive_merge_keeps_both_researcher_findings() -> None:
    runtime = _runtime()
    item = build_suite()[1]
    state = runtime.start(item["query"], run_id="graph-merge", query_id=item["id"])
    joined = " ".join(finding["content"] for finding in state["research_findings"])
    for claim in item["source_claims"]:
        assert claim in joined or claim.split()[0] in joined
