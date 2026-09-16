from __future__ import annotations

from argus.evals.judge.dataset import build_corpus, build_suite
from argus.graph.graph import compile_langgraph
from argus.graph.nodes import make_node_context, make_nodes
from argus.graph.policy import ScriptedPolicy
from argus.graph.state import initial_state
from argus.tools.research_tools import GraphToolEngine


def test_langgraph_compiles_and_runs_memory_saver() -> None:
    suite = build_suite()
    item = suite[0]
    ctx = make_node_context(
        policy=ScriptedPolicy(catalog={item["id"]: item}),
        tools=GraphToolEngine(corpus=build_corpus(suite)),
    )
    app = compile_langgraph(make_nodes(ctx))
    state = initial_state(item["query"], "lg-1", query_id=item["id"])
    result = app.invoke(state, {"configurable": {"thread_id": "lg-1"}})
    assert result["status"] in {"completed", "interrupted"}
    assert result.get("subqueries") or result.get("final_answer") is not None
