from __future__ import annotations

from argus.graph.nodes import needs_hitl
from argus.tools.research_tools import DESTRUCTIVE_TOOLS


def interrupt_payload(state: dict) -> dict:
    pending = state.get("pending_action") or {}
    return {
        "run_id": state.get("run_id"),
        "task": state.get("task"),
        "reason": state.get("interrupt_reason") or pending.get("reason") or "human_approval_required",
        "pending_action": pending,
        "needs_clarification": bool(state.get("needs_clarification")),
        "destructive": bool(pending.get("destructive") or pending.get("tool_name") in DESTRUCTIVE_TOOLS),
    }


def should_interrupt(state: dict) -> bool:
    return needs_hitl(state, frozenset(DESTRUCTIVE_TOOLS))
