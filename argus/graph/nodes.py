from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Callable

from argus.agent.orchestrator import Orchestrator
from argus.agent.schemas import PlanStep
from argus.graph.policy import ScriptedPolicy
from argus.graph.state import OperatorDecision
from argus.memory.token_budget import apply_token_budget, count_tokens
from argus.observability.otel import TokenBudgetRecorder, traced
from argus.runtime_config import RuntimeConfig
from argus.tools.research_tools import DESTRUCTIVE_TOOLS, GraphToolEngine
from argus.tools.reliability import RetryPolicy


@dataclass
class NodeContext:
    policy: ScriptedPolicy
    tools: GraphToolEngine
    orchestrator: Orchestrator
    config: RuntimeConfig
    recorder: TokenBudgetRecorder
    destructive_tools: frozenset[str]


def make_node_context(
    *,
    policy: ScriptedPolicy | None = None,
    tools: GraphToolEngine | None = None,
    config: RuntimeConfig | None = None,
    recorder: TokenBudgetRecorder | None = None,
) -> NodeContext:
    runtime = config or RuntimeConfig()
    engine = tools or GraphToolEngine()
    retry = RetryPolicy(
        max_retries=runtime.max_retries,
        base_delay_s=runtime.base_delay_s,
        jitter_s=runtime.jitter_s,
    )
    orchestrator = Orchestrator(
        tools=engine,
        use_reliability_layer=True,
        retry_policy=retry,
        do_sleep=False,
        default_step_timeout_ms=runtime.default_step_timeout_ms,
    )
    return NodeContext(
        policy=policy or ScriptedPolicy(),
        tools=engine,
        orchestrator=orchestrator,
        config=runtime,
        recorder=recorder or TokenBudgetRecorder(),
        destructive_tools=frozenset(runtime.hitl_destructive_tools) | DESTRUCTIVE_TOOLS,
    )


def _call_tool(ctx: NodeContext, state: dict[str, Any], tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    payload = dict(args)
    payload.setdefault("key", state.get("run_id") or state.get("query_id") or "graph")
    fallback = "backup_search" if tool_name in {"web_search", "primary_search"} else None
    step = PlanStep(
        step_id=f"{state.get('run_id', 'run')}-{tool_name}-{len(state.get('tool_events') or [])}",
        tool_name=tool_name,
        payload=payload,
        fallback_tool_name=fallback,
    )
    result = ctx.orchestrator._call_step(step)
    return {
        "tool_name": tool_name,
        "args": args,
        "ok": result.ok,
        "attempts": result.attempts,
        "used_fallback": result.used_fallback,
        "output": result.output,
        "error_type": result.error_type,
    }


def _pre_model_budget(state: dict[str, Any], ctx: NodeContext) -> dict[str, Any]:
    messages = list(state.get("messages") or [])
    compressed, before, after, summarized = apply_token_budget(
        messages,
        task=str(state.get("task", "")),
        system_instructions=str(state.get("system_instructions", "")),
        context_window=int(state.get("context_window") or ctx.config.context_window),
        threshold=float(state.get("compress_threshold") or ctx.config.compress_threshold),
        recorder=ctx.recorder,
    )
    return {
        "messages": compressed,
        "token_count": after,
        "tokens_before": before,
        "tokens_after": after,
        "summarized": bool(state.get("summarized")) or summarized,
    }


def planner_node(ctx: NodeContext) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def planner(state: dict[str, Any]) -> dict[str, Any]:
        budget = _pre_model_budget(state, ctx)
        plan = ctx.policy.plan(str(state.get("task", "")), str(state.get("query_id") or "") or None)
        messages = list(budget["messages"])
        messages.append({"role": "assistant", "content": f"plan subqueries={plan.subqueries}"})
        return {
            **budget,
            "messages": messages,
            "subqueries": plan.subqueries,
            "needs_clarification": plan.needs_clarification,
            "llm_calls": 1,
        }

    return traced("planner", planner)


def researcher_node(ctx: NodeContext) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def researcher(state: dict[str, Any]) -> dict[str, Any]:
        query = str(state.get("current_query") or state.get("task") or "")
        event = _call_tool(ctx, state, "web_search", {"query": query})
        output = event.get("output") or {}
        finding = {
            "query": query,
            "content": output.get("content", ""),
            "source": output.get("source", f"corpus:{query}"),
            "tool_name": "web_search",
        }
        return {
            "research_findings": [finding],
            "tool_events": [event],
            "llm_calls": 1,
        }

    return traced("researcher", researcher)


def research_all_node(ctx: NodeContext) -> Callable[[dict[str, Any]], dict[str, Any]]:
    inner = researcher_node(ctx)

    def research_all(state: dict[str, Any]) -> dict[str, Any]:
        queries = list(state.get("subqueries") or [state.get("task")])
        findings: list[dict[str, Any]] = []
        events: list[dict[str, Any]] = []
        llm_calls = 0
        for query in queries:
            piece = inner({**state, "current_query": query})
            findings.extend(piece.get("research_findings") or [])
            events.extend(piece.get("tool_events") or [])
            llm_calls += int(piece.get("llm_calls") or 0)
        return {"research_findings": findings, "tool_events": events, "llm_calls": llm_calls}

    return traced("research_all", research_all)


def _merge_pair(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    return {
        "query": f"{left.get('query', '')} | {right.get('query', '')}",
        "content": f"{left.get('content', '')} {right.get('content', '')}".strip(),
        "source": f"{left.get('source', '')};{right.get('source', '')}",
        "tool_name": "merge",
    }


def recursive_merge(findings: list[dict[str, Any]]) -> dict[str, Any]:
    if not findings:
        return {"query": "", "content": "", "source": "", "tool_name": "merge"}
    if len(findings) == 1:
        return findings[0]
    mid = len(findings) // 2
    return _merge_pair(recursive_merge(findings[:mid]), recursive_merge(findings[mid:]))


def merge_node(_ctx: NodeContext) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def merge(state: dict[str, Any]) -> dict[str, Any]:
        findings = list(state.get("research_findings") or [])
        merged = recursive_merge(findings)
        messages = list(state.get("messages") or [])
        for finding in findings:
            messages.append({"role": "tool", "content": str(finding.get("content", ""))})
        messages.append({"role": "assistant", "content": f"merged {len(findings)} findings source={merged.get('source', '')}"})
        return {"messages": messages}

    return traced("merge", merge)


def compress_node(ctx: NodeContext) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def compress(state: dict[str, Any]) -> dict[str, Any]:
        return _pre_model_budget(state, ctx)

    return traced("compress", compress)


def operator_node(ctx: NodeContext) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def operator(state: dict[str, Any]) -> dict[str, Any]:
        budget = _pre_model_budget(state, ctx)
        decision: OperatorDecision = ctx.policy.decide({**state, **budget})
        pending = None
        if decision.action == "tool" and decision.tool_name:
            pending = {
                "tool_name": decision.tool_name,
                "args": decision.args,
                "destructive": decision.destructive or decision.tool_name in ctx.destructive_tools,
                "reason": decision.reason,
            }
        elif decision.action == "wait":
            pending = {"tool_name": "wait", "args": {}, "destructive": False, "reason": decision.reason}
        return {
            **budget,
            "pending_action": pending,
            "operator_iterations": int(state.get("operator_iterations") or 0) + 1,
            "llm_calls": 1,
            "status": "running",
        }

    return traced("operator", operator)


def needs_hitl(state: dict[str, Any], destructive_tools: frozenset[str]) -> bool:
    if state.get("hitl_approved"):
        return False
    pending = state.get("pending_action") or {}
    tool_name = str(pending.get("tool_name") or "")
    if tool_name == "wait" or pending.get("destructive"):
        return True
    if tool_name in destructive_tools:
        return True
    if state.get("needs_clarification") and not state.get("human_feedback"):
        return True
    return False


def route_operator(state: dict[str, Any]) -> str:
    pending = state.get("pending_action") or {}
    tool_name = str(pending.get("tool_name") or "")
    if needs_hitl(state, frozenset(DESTRUCTIVE_TOOLS)):
        return "hitl_gate"
    if tool_name and tool_name != "wait":
        return "tool_node"
    return "synthesize"


def hitl_node(_ctx: NodeContext) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def hitl_gate(state: dict[str, Any]) -> dict[str, Any]:
        pending = state.get("pending_action") or {}
        feedback = str(state.get("human_feedback") or "")
        rejected = feedback.strip().lower() in {"reject", "deny", "no"}
        if rejected:
            return {
                "pending_action": None,
                "hitl_approved": False,
                "interrupt_reason": None,
                "status": "rejected",
            }
        return {
            "hitl_approved": True,
            "interrupt_reason": None,
            "status": "running",
            "pending_action": None if pending.get("tool_name") == "wait" else pending,
        }

    return traced("hitl_gate", hitl_gate)


def route_after_hitl(state: dict[str, Any]) -> str:
    if state.get("status") == "rejected":
        return "synthesize"
    pending = state.get("pending_action") or {}
    tool_name = str(pending.get("tool_name") or "")
    if tool_name and tool_name != "wait":
        return "tool_node"
    return "operator"


def tool_node(ctx: NodeContext) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def run_tool(state: dict[str, Any]) -> dict[str, Any]:
        pending = state.get("pending_action") or {}
        tool_name = str(pending.get("tool_name") or "web_search")
        args = dict(pending.get("args") or {})
        event = _call_tool(ctx, state, tool_name, args)
        messages = list(state.get("messages") or [])
        messages.append({"role": "tool", "content": json.dumps(event.get("output") or {})})
        finding_update: dict[str, Any] = {}
        output = event.get("output") or {}
        if output.get("content"):
            finding_update["research_findings"] = [
                {
                    "query": args.get("query", tool_name),
                    "content": output.get("content", ""),
                    "source": output.get("source", f"operator:{tool_name}"),
                    "tool_name": tool_name,
                }
            ]
        return {
            "tool_events": [event],
            "messages": messages,
            "pending_action": None,
            "hitl_approved": False,
            "interrupt_reason": None,
            **finding_update,
        }

    return traced("tool_node", run_tool)


def synthesize_node(ctx: NodeContext) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def synthesize(state: dict[str, Any]) -> dict[str, Any]:
        budget = _pre_model_budget(state, ctx)
        answer = ctx.policy.synthesize({**state, **budget})
        citations = []
        for finding in state.get("research_findings") or []:
            source = finding.get("source")
            if source and source not in citations:
                citations.append(source)
        return {
            **budget,
            "final_answer": answer,
            "citations": citations,
            "status": "completed" if state.get("status") != "rejected" else "rejected",
            "llm_calls": 1,
            "token_count": count_tokens(answer) + int(budget.get("token_count") or 0),
        }

    return traced("synthesize", synthesize)


def route_researchers(state: dict[str, Any]) -> list[Any]:
    try:
        from langgraph.types import Send
    except Exception:
        return ["research_all"]
    queries = list(state.get("subqueries") or [state.get("task")])
    return [Send("researcher", {"task": state.get("task"), "current_query": query, "run_id": state.get("run_id")}) for query in queries]


def make_nodes(ctx: NodeContext) -> dict[str, Any]:
    return {
        "planner": planner_node(ctx),
        "researcher": researcher_node(ctx),
        "research_all": research_all_node(ctx),
        "merge": merge_node(ctx),
        "compress": compress_node(ctx),
        "operator": operator_node(ctx),
        "hitl_gate": hitl_node(ctx),
        "tool_node": tool_node(ctx),
        "synthesize": synthesize_node(ctx),
        "route_operator": route_operator,
        "route_after_hitl": route_after_hitl,
        "route_researchers": route_researchers,
    }
