from __future__ import annotations

from threading import Lock
from typing import Any

from argus.deals.schemas import Opportunity, ScoredDeal

_STAGES = {
    "advance": "Diligence",
    "diligence": "Screened",
    "pass": "Passed",
}


class DealCloudStore:
    """In-process Salesforce/DealCloud-shaped opportunity store plus SharePoint paths."""

    def __init__(self) -> None:
        self._lock = Lock()
        self.opportunities: dict[str, Opportunity] = {}
        self.documents: dict[str, dict[str, Any]] = {}

    def reset(self) -> None:
        with self._lock:
            self.opportunities.clear()
            self.documents.clear()

    def pending(self, scored: ScoredDeal, *, run_id: str, filename: str) -> Opportunity:
        opportunity = Opportunity(
            opportunity_id=f"opp-{scored.deal_id}",
            account_name=scored.company,
            deal_id=scored.deal_id,
            stage="New",
            score=scored.score,
            recommendation=scored.recommendation,
            source_document=filename,
            sharepoint_path=f"/sites/dealroom/{scored.deal_id}/{filename}",
            extraction=scored.extraction.model_dump(),
            run_id=run_id,
            status="pending_approval",
        )
        with self._lock:
            self.opportunities[opportunity.opportunity_id] = opportunity
        return opportunity

    def upsert(self, scored: ScoredDeal, *, run_id: str, filename: str) -> Opportunity:
        stage = _STAGES.get(scored.recommendation, "Screened")
        path = f"/sites/dealroom/{scored.deal_id}/{filename}"
        opportunity = Opportunity(
            opportunity_id=f"opp-{scored.deal_id}",
            account_name=scored.company,
            deal_id=scored.deal_id,
            stage=stage,
            score=scored.score,
            recommendation=scored.recommendation,
            source_document=filename,
            sharepoint_path=path,
            extraction=scored.extraction.model_dump(),
            run_id=run_id,
            status="written",
        )
        with self._lock:
            self.opportunities[opportunity.opportunity_id] = opportunity
            self.documents[scored.deal_id] = {
                "path": path,
                "filename": filename,
                "company": scored.company,
                "run_id": run_id,
            }
        return opportunity

    def get(self, opportunity_id: str) -> Opportunity | None:
        return self.opportunities.get(opportunity_id)

    def list_pipeline(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = [opp.model_dump() for opp in self.opportunities.values()]
        order = {"New": 0, "Screened": 1, "Diligence": 2, "Passed": 3}
        rows.sort(key=lambda row: (order.get(str(row.get("stage")), 9), str(row.get("account_name"))))
        return rows


_STORE = DealCloudStore()


def get_store() -> DealCloudStore:
    return _STORE


def reset_store() -> None:
    _STORE.reset()
