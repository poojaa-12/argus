from __future__ import annotations

from fastapi.testclient import TestClient

from argus.deals.catalog import intake_task
from argus.deals.corpus import DEALS, get_deal
from argus.deals.extract import extract_cim
from argus.deals.score import score_deal
from argus.deals.store import DealCloudStore
from argus.evals.deals import evaluate_deals
from argus.graph.runtime import GraphRuntime
from argus.runtime_config import RuntimeConfig
from argus.serving.api import create_app
from argus.serving.store import InMemoryRunStore
from argus.tools.research_tools import GraphToolEngine


def _runtime(store: DealCloudStore) -> GraphRuntime:
    return GraphRuntime.create(
        config=RuntimeConfig(),
        tools=GraphToolEngine(pipeline=store),
    )


def test_extraction_matches_gold_and_refuses_missing_fields() -> None:
    report = evaluate_deals()
    assert report["field_accuracy_pct"] == 100.0
    assert report["hallucinated_missing_fields"] == 0
    meridian = extract_cim("meridian")
    assert meridian.ebitda_m is None
    assert "ebitda_m" in meridian.missing_fields


def test_thesis_screen_advances_software_and_passes_epc() -> None:
    northwind = score_deal(extract_cim("northwind"))
    helios = score_deal(extract_cim("helios"))
    harbor = score_deal(extract_cim("harborpay"))
    meridian = score_deal(extract_cim("meridian"))
    assert northwind.recommendation == "advance"
    assert northwind.score >= 75
    assert helios.recommendation == "pass"
    assert harbor.recommendation == "diligence"
    assert meridian.recommendation == "diligence"


def test_deal_intake_interrupts_before_dealcloud_write() -> None:
    store = DealCloudStore()
    runtime = _runtime(store)
    deal = get_deal("northwind")
    state = runtime.start(intake_task(deal), run_id="deal-nw", query_id=deal.id)
    assert state["status"] == "interrupted"
    pending = state.get("pending_action") or {}
    assert pending.get("tool_name") == "crm_upsert"
    assert pending.get("destructive") is True
    names = [event["tool_name"] for event in state["tool_events"]]
    assert names.count("cim_extract") == 1
    assert names.count("thesis_score") == 1
    assert "crm_upsert" not in names
    queued = store.get("opp-northwind")
    assert queued is not None
    assert queued.status == "pending_approval"


def test_associate_approve_writes_dealcloud_reject_does_not() -> None:
    store = DealCloudStore()
    runtime = _runtime(store)
    runtime.start(intake_task(get_deal("quorum")), run_id="deal-q", query_id="quorum")
    completed = runtime.resume("deal-q", "approve")
    assert completed["status"] == "completed"
    written = store.get("opp-quorum")
    assert written is not None
    assert written.status == "written"
    assert written.stage == "Diligence"
    assert written.sharepoint_path.endswith("Quorum_Data_CIM.pdf")

    runtime.start(intake_task(get_deal("helios")), run_id="deal-h", query_id="helios")
    rejected = runtime.resume("deal-h", "reject")
    assert rejected["status"] == "rejected"
    assert all(event["tool_name"] != "crm_upsert" for event in rejected["tool_events"])
    leftover = store.get("opp-helios")
    assert leftover is None or leftover.status != "written"


def test_deal_intake_api_roundtrip() -> None:
    store = DealCloudStore()
    runtime = _runtime(store)
    client = TestClient(create_app(runtime=runtime, store=InMemoryRunStore(), pipeline=store))
    listed = client.get("/v1/deals")
    assert listed.status_code == 200
    assert len(listed.json()["deals"]) == len(DEALS)

    started = client.post("/v1/deals/intake", json={"deal_id": "harborpay", "run_id": "api-harbor"})
    assert started.status_code == 200
    body = started.json()
    assert body["status"] == "interrupted"
    assert body["interrupt"]["tool_name"] == "crm_upsert"

    resumed = client.post("/v1/runs/api-harbor/resume", json={"feedback": "approved"})
    assert resumed.status_code == 200
    assert resumed.json()["status"] == "completed"
    pipeline = client.get("/v1/deals/pipeline").json()["opportunities"]
    harbor = next(row for row in pipeline if row["deal_id"] == "harborpay")
    assert harbor["status"] == "written"
    assert harbor["stage"] == "Screened"
