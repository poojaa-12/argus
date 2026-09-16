from __future__ import annotations

from dataclasses import dataclass, field
import json
import re
from typing import Any

from argus.deals.catalog import DEAL_DESTRUCTIVE, decide_deal, plan_deal_intake, resolve_deal
from argus.graph.state import OperatorDecision, PlanResult
from argus.tools.research_tools import DESTRUCTIVE_TOOLS


@dataclass
class ScriptedPolicy:
    """Deterministic planner/operator used in CI. Optional LangChain LLM overlay."""

    catalog: dict[str, dict[str, Any]] = field(default_factory=dict)
    llm: Any | None = None

    def lookup(self, task: str, query_id: str | None = None) -> dict[str, Any] | None:
        if query_id and query_id in self.catalog:
            return self.catalog[query_id]
        for item in self.catalog.values():
            if item.get("query") == task:
                return item
        return None

    def plan(self, task: str, query_id: str | None = None) -> PlanResult:
        if self.llm is not None:
            planned = self._plan_with_llm(task)
            if planned is not None:
                return planned
        deal_plan = plan_deal_intake(task, query_id)
        if deal_plan is not None:
            return deal_plan
        item = self.lookup(task, query_id)
        if item is not None:
            return PlanResult(
                subqueries=list(item.get("subqueries") or [task]),
                needs_clarification=bool(item.get("needs_clarification")),
                operator_steps=list(item.get("operator_steps") or []),
            )
        parts = [part.strip() for part in re.split(r"\band\b|,", task) if len(part.strip()) > 8]
        subqueries = parts[:3] if len(parts) >= 2 else [task, f"background context for: {task[:120]}"]
        return PlanResult(subqueries=subqueries)

    def decide(self, state: dict[str, Any]) -> OperatorDecision:
        if self.llm is not None:
            decision = self._decide_with_llm(state)
            if decision is not None:
                return decision
        task = str(state.get("task", ""))
        query_id = str(state.get("query_id") or "") or None
        item = self.lookup(task, query_id)
        iterations = int(state.get("operator_iterations") or 0)
        events = list(state.get("tool_events") or [])
        used = [str(event.get("tool_name")) for event in events]

        deal = resolve_deal(task, query_id)
        if deal is not None:
            decision = decide_deal(state, deal)
            if decision is not None:
                return decision

        if item and item.get("needs_clarification") and not state.get("human_feedback"):
            return OperatorDecision(action="wait", reason="ambiguous requirements")

        operator_tools = list(item.get("operator_steps") or []) if item else []
        for tool_name in operator_tools:
            if tool_name not in used:
                destructive = tool_name in DESTRUCTIVE_TOOLS or tool_name in DEAL_DESTRUCTIVE
                args = {"query": task, "table": "operator_records"}
                return OperatorDecision(
                    action="tool",
                    tool_name=tool_name,
                    args=args,
                    reason="operator step from plan",
                    destructive=destructive,
                )

        if iterations >= 6:
            return OperatorDecision(action="finish", reason="iteration budget")
        return OperatorDecision(action="finish", reason="research complete")

    def synthesize(self, state: dict[str, Any]) -> str:
        findings = list(state.get("research_findings") or [])
        parts: list[str] = []
        for finding in findings:
            content = str(finding.get("content", ""))
            if "CORE_FACTS:" in content:
                content = content.split("CORE_FACTS:", 1)[1].strip()
            parts.append(content)
        for event in state.get("tool_events") or []:
            output = event.get("output") or {}
            if event.get("tool_name") in DESTRUCTIVE_TOOLS | {"cim_extract", "thesis_score"} and (
                output.get("written") or output.get("content")
            ):
                parts.append(str(output.get("content") or f"{event['tool_name']} applied"))
        feedback = state.get("human_feedback")
        if feedback:
            parts.append(f"human_feedback={feedback}")
        return " ".join(part for part in parts if part).strip() or "No findings."

    def _plan_with_llm(self, task: str) -> PlanResult | None:
        try:
            message = self.llm.invoke(
                "Return JSON {\"subqueries\": [..], \"needs_clarification\": false} for: " + task
            )
            text = getattr(message, "content", message)
            data = json.loads(text)
            return PlanResult(
                subqueries=list(data.get("subqueries") or [task]),
                needs_clarification=bool(data.get("needs_clarification", False)),
            )
        except Exception:
            return None

    def _decide_with_llm(self, state: dict[str, Any]) -> OperatorDecision | None:
        try:
            message = self.llm.invoke("Return JSON {\"action\": \"finish\"} to close the task.")
            text = getattr(message, "content", message)
            data = json.loads(text)
            return OperatorDecision(
                action=data.get("action", "finish"),
                tool_name=data.get("tool_name"),
                args=dict(data.get("args") or {}),
                reason=str(data.get("reason") or "llm"),
                destructive=bool(data.get("destructive", False)),
            )
        except Exception:
            return None
