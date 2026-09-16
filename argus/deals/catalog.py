from __future__ import annotations

from typing import Any

from argus.deals.corpus import DEALS, get_deal
from argus.deals.schemas import DealRecord

DEAL_OPERATOR_STEPS = ["cim_extract", "thesis_score", "crm_upsert"]
DEAL_DESTRUCTIVE = {"crm_upsert", "sharepoint_attach"}


def intake_task(deal: DealRecord) -> str:
    return (
        f"Intake the {deal.company} {deal.document_type} for Acme Capital. "
        "Extract cited fields, score against the software thesis, and write to DealCloud only after associate approval."
    )


def _catalog_item(deal: DealRecord) -> dict[str, Any]:
    return {
        "id": deal.id,
        "query": intake_task(deal),
        "subqueries": [
            f"Extract financials, risks, and citations from the {deal.company} {deal.document_type}",
            f"Score {deal.company} against the Acme Capital B2B software thesis",
        ],
        "operator_steps": list(DEAL_OPERATOR_STEPS),
        "needs_clarification": False,
        "deal_id": deal.id,
    }


DEAL_CATALOG: dict[str, dict[str, Any]] = {deal.id: _catalog_item(deal) for deal in DEALS}


def resolve_deal(task: str, query_id: str | None = None) -> DealRecord | None:
    if query_id:
        try:
            return get_deal(query_id)
        except KeyError:
            pass
    lowered = (task or "").lower()
    for deal in DEALS:
        if deal.id == lowered.strip() or deal.id in lowered or deal.company.lower() in lowered:
            return deal
    return None


def plan_deal_intake(task: str, query_id: str | None = None):
    from argus.graph.state import PlanResult

    deal = resolve_deal(task, query_id)
    if deal is None:
        return None
    item = DEAL_CATALOG[deal.id]
    return PlanResult(
        subqueries=list(item["subqueries"]),
        needs_clarification=False,
        operator_steps=list(item["operator_steps"]),
    )


def decide_deal(state: dict[str, Any], deal: DealRecord):
    from argus.graph.state import OperatorDecision

    used = [str(event.get("tool_name")) for event in state.get("tool_events") or []]
    args = {"deal_id": deal.id, "firm_id": "acme-capital", "query": deal.company}
    for tool_name in DEAL_OPERATOR_STEPS:
        if tool_name not in used:
            return OperatorDecision(
                action="tool",
                tool_name=tool_name,
                args=args,
                reason=(
                    "Associate approval required before writing to DealCloud / SharePoint."
                    if tool_name in DEAL_DESTRUCTIVE
                    else f"{tool_name} for {deal.company}"
                ),
                destructive=tool_name in DEAL_DESTRUCTIVE,
            )
    return None
