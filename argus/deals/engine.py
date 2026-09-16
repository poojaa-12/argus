from __future__ import annotations

from typing import Any

from argus.deals.corpus import get_deal
from argus.deals.extract import extract_cim
from argus.deals.score import score_deal
from argus.deals.store import DealCloudStore, get_store


def run_tool(tool_name: str, payload: dict[str, Any], store: DealCloudStore | None = None) -> dict[str, Any]:
    deal_id = str(payload.get("deal_id") or "")
    if not deal_id:
        raise KeyError("deal_id is required")
    deal = get_deal(deal_id)
    pipeline = store or get_store()
    run_id = str(payload.get("key") or payload.get("run_id") or "")

    if tool_name == "cim_extract":
        extraction = extract_cim(deal_id)
        return {
            "tool": tool_name,
            "status": "ok",
            "deal_id": deal_id,
            "extraction": extraction.model_dump(),
            "content": extraction.model_dump_json(),
            "source": f"cim:{deal.filename}",
            "written": False,
        }

    if tool_name == "thesis_score":
        extraction = extract_cim(deal_id)
        scored = score_deal(extraction)
        pipeline.pending(scored, run_id=run_id, filename=deal.filename)
        return {
            "tool": tool_name,
            "status": "ok",
            "deal_id": deal_id,
            "score": scored.score,
            "recommendation": scored.recommendation,
            "rationale": scored.rationale,
            "breakdown": scored.breakdown.model_dump(),
            "extraction": scored.extraction.model_dump(),
            "content": f"{deal.company} score {scored.score}/100 ({scored.recommendation})",
            "source": "thesis:acme-capital",
            "written": False,
        }

    if tool_name in {"crm_upsert", "sharepoint_attach"}:
        extraction = extract_cim(deal_id)
        scored = score_deal(extraction)
        opportunity = pipeline.upsert(scored, run_id=run_id, filename=deal.filename)
        return {
            "tool": tool_name,
            "status": "ok",
            "deal_id": deal_id,
            "written": True,
            "opportunity": opportunity.model_dump(),
            "sharepoint_path": opportunity.sharepoint_path,
            "content": (
                f"Wrote {deal.company} to DealCloud as {opportunity.opportunity_id} "
                f"stage={opportunity.stage}; attached {opportunity.sharepoint_path}"
            ),
            "source": f"dealcloud:{opportunity.opportunity_id}",
        }

    raise KeyError(tool_name)
