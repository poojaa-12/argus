from __future__ import annotations

from typing import Any

from argus.graph.nodes import NodeContext, make_nodes
from argus.graph.state import AgentState

END = "__end__"
ADD_KEYS = {"research_findings", "tool_events", "llm_calls"}


def apply_update(state: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    merged = dict(state)
    for key, value in update.items():
        if key in ADD_KEYS:
            if key == "llm_calls":
                merged[key] = int(merged.get(key) or 0) + int(value or 0)
            else:
                merged[key] = list(merged.get(key) or []) + list(value or [])
        else:
            merged[key] = value
    return merged


class LocalCompiledGraph:
    """Cyclic state machine with HITL interrupt_before hitl_gate semantics."""

    def __init__(self, nodes: dict[str, Any]) -> None:
        self.nodes = nodes
        self._states: dict[str, dict[str, Any]] = {}
        self._next: dict[str, str] = {}

    def get_state(self, config: dict[str, Any]) -> dict[str, Any] | None:
        thread_id = config["configurable"]["thread_id"]
        return self._states.get(thread_id)

    def update_state(self, config: dict[str, Any], values: dict[str, Any]) -> dict[str, Any]:
        thread_id = config["configurable"]["thread_id"]
        current = dict(self._states.get(thread_id) or {})
        current.update(values)
        self._states[thread_id] = current
        return current

    def invoke(self, values: dict[str, Any] | None, config: dict[str, Any], *, resume: bool = False) -> dict[str, Any]:
        thread_id = config["configurable"]["thread_id"]
        if resume:
            state = {**self._states.get(thread_id, {}), **(values or {}), "_resuming_hitl": True}
            current = self._next.get(thread_id, "hitl_gate")
        else:
            state = dict(values or self._states.get(thread_id) or {})
            current = "planner"

        safety = 0
        while current != END and safety < 40:
            safety += 1
            if current == "hitl_gate" and not state.get("_resuming_hitl"):
                pending = state.get("pending_action") or {}
                state["status"] = "interrupted"
                state["interrupt_reason"] = pending.get("reason") or "human_approval_required"
                self._states[thread_id] = state
                self._next[thread_id] = "hitl_gate"
                return state
            state["_resuming_hitl"] = False
            update = self.nodes[current](state) or {}
            state = apply_update(state, update)
            current = self._route(current, state)
            self._states[thread_id] = state

        self._next.pop(thread_id, None)
        if state.get("status") not in {"rejected", "completed"}:
            state["status"] = "completed"
        self._states[thread_id] = state
        return state

    def _route(self, current: str, state: dict[str, Any]) -> str:
        if current == "planner":
            return "research_all"
        if current == "research_all":
            return "merge"
        if current == "merge":
            return "compress"
        if current == "compress":
            return "operator"
        if current == "operator":
            return self.nodes["route_operator"](state)
        if current == "hitl_gate":
            return self.nodes["route_after_hitl"](state)
        if current == "tool_node":
            return "compress"
        return END


class LangGraphApp:
    def __init__(self, compiled: Any) -> None:
        self.compiled = compiled

    def get_state(self, config: dict[str, Any]) -> dict[str, Any] | None:
        snapshot = self.compiled.get_state(config)
        if snapshot is None:
            return None
        values = dict(getattr(snapshot, "values", {}) or {})
        nxt = tuple(getattr(snapshot, "next", ()) or ())
        if nxt:
            values["status"] = values.get("status") or "interrupted"
            pending = values.get("pending_action") or {}
            values["interrupt_reason"] = values.get("interrupt_reason") or pending.get("reason") or "human_approval_required"
        return values

    def update_state(self, config: dict[str, Any], values: dict[str, Any]) -> dict[str, Any]:
        self.compiled.update_state(config, values)
        return self.get_state(config) or {}

    def invoke(self, values: dict[str, Any] | None, config: dict[str, Any], *, resume: bool = False) -> dict[str, Any]:
        if resume:
            self.compiled.update_state(config, values or {})
            result = self.compiled.invoke(None, config)
        else:
            result = self.compiled.invoke(values, config)
        snapshot = self.get_state(config)
        if snapshot and snapshot.get("status") == "interrupted":
            return snapshot
        merged = dict(snapshot or result or {})
        if merged.get("status") not in {"rejected", "interrupted"}:
            merged["status"] = merged.get("status") or "completed"
        return merged


def compile_langgraph(nodes: dict[str, Any], checkpointer: Any | None = None) -> LangGraphApp:
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.graph import END, START, StateGraph

    builder = StateGraph(AgentState)
    builder.add_node("planner", nodes["planner"])
    builder.add_node("researcher", nodes["researcher"])
    builder.add_node("merge", nodes["merge"])
    builder.add_node("compress", nodes["compress"])
    builder.add_node("operator", nodes["operator"])
    builder.add_node("hitl_gate", nodes["hitl_gate"])
    builder.add_node("tool_node", nodes["tool_node"])
    builder.add_node("synthesize", nodes["synthesize"])
    builder.add_edge(START, "planner")
    builder.add_conditional_edges("planner", nodes["route_researchers"])
    builder.add_edge("researcher", "merge")
    builder.add_edge("merge", "compress")
    builder.add_edge("compress", "operator")
    builder.add_conditional_edges(
        "operator",
        nodes["route_operator"],
        {"hitl_gate": "hitl_gate", "tool_node": "tool_node", "synthesize": "synthesize"},
    )
    builder.add_conditional_edges(
        "hitl_gate",
        nodes["route_after_hitl"],
        {"tool_node": "tool_node", "synthesize": "synthesize", "operator": "operator"},
    )
    builder.add_edge("tool_node", "compress")
    builder.add_edge("synthesize", END)
    compiled = builder.compile(
        checkpointer=checkpointer or MemorySaver(),
        interrupt_before=["hitl_gate"],
    )
    return LangGraphApp(compiled)


def compile_graph(ctx: NodeContext, *, engine: str = "local", checkpointer: Any | None = None) -> Any:
    nodes = make_nodes(ctx)
    if engine == "langgraph":
        try:
            return compile_langgraph(nodes, checkpointer=checkpointer)
        except Exception:
            return LocalCompiledGraph(nodes)
    return LocalCompiledGraph(nodes)
