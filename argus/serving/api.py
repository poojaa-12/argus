from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from argus.deals.catalog import intake_task
from argus.deals.corpus import ACME_THESIS, get_deal, list_deals
from argus.deals.store import DealCloudStore, get_store
from argus.graph.runtime import GraphRuntime
from argus.runtime_config import RuntimeConfig
from argus.serving.store import RunStore, build_store
from argus.tools.research_tools import GraphToolEngine


class StartRunRequest(BaseModel):
    goal: str
    query_id: str | None = None
    run_id: str | None = None


class ResumeRequest(BaseModel):
    feedback: str = Field(min_length=1)


class DealIntakeRequest(BaseModel):
    deal_id: str
    run_id: str | None = None


def _persist(store: RunStore, runtime: GraphRuntime, state: dict[str, Any]) -> None:
    run_id = str(state.get("run_id"))
    store.upsert_run(
        run_id,
        status=str(state.get("status") or "running"),
        task=str(state.get("task") or ""),
        state=state,
        human_feedback=state.get("human_feedback"),
    )
    for event in runtime.events.get(run_id, []):
        store.append_event(run_id, str(event.get("event")), {k: v for k, v in event.items() if k != "event"})


def create_app(
    runtime: GraphRuntime | None = None,
    store: RunStore | None = None,
    config: RuntimeConfig | None = None,
    pipeline: DealCloudStore | None = None,
) -> FastAPI:
    runtime_config = config or RuntimeConfig.from_env()
    pipe = pipeline or get_store()
    graph = runtime or GraphRuntime.create(
        config=runtime_config,
        tools=GraphToolEngine(pipeline=pipe),
    )
    run_store = store or build_store(runtime_config.database_url)
    app = FastAPI(title="Argus Operator", version="0.3.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.runtime = graph
    app.state.store = run_store
    app.state.pipeline = pipe

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/runs")
    def start_run(body: StartRunRequest) -> dict[str, Any]:
        state = graph.start(body.goal, run_id=body.run_id, query_id=body.query_id)
        _persist(run_store, graph, state)
        return {"run_id": state.get("run_id"), "status": state.get("status"), "state": state}

    @app.get("/v1/runs/{run_id}")
    def get_run(run_id: str) -> dict[str, Any]:
        record = run_store.get_run(run_id) or graph.get_state(run_id)
        if record is None:
            raise HTTPException(status_code=404, detail="run not found")
        if "state" not in record:
            record = {"run_id": run_id, "status": record.get("status"), "state": record}
        return record

    @app.get("/v1/runs/{run_id}/state")
    def get_state(run_id: str) -> dict[str, Any]:
        inspected = graph.inspect(run_id)
        if not inspected.get("state"):
            record = run_store.get_run(run_id)
            if record is None:
                raise HTTPException(status_code=404, detail="run not found")
            return {"state": record.get("state"), "events": run_store.list_events(run_id)}
        return inspected

    @app.post("/v1/runs/{run_id}/resume")
    def resume_run(run_id: str, body: ResumeRequest) -> dict[str, Any]:
        existing = graph.get_state(run_id) or (run_store.get_run(run_id) or {}).get("state")
        if existing is None:
            raise HTTPException(status_code=404, detail="run not found")
        if existing.get("status") != "interrupted":
            raise HTTPException(status_code=409, detail="run is not waiting for human feedback")
        state = graph.resume(run_id, body.feedback)
        _persist(run_store, graph, state)
        return {"run_id": run_id, "status": state.get("status"), "state": state}

    @app.websocket("/v1/runs/{run_id}/events")
    async def run_events(websocket: WebSocket, run_id: str) -> None:
        await websocket.accept()
        try:
            events = run_store.list_events(run_id) or list(graph.events.get(run_id) or [])
            for event in events:
                await websocket.send_json(event)
            await websocket.send_json({"event": "done", "run_id": run_id})
        except WebSocketDisconnect:
            return

    @app.get("/v1/deals")
    def list_deal_corpus() -> dict[str, Any]:
        return {
            "thesis": ACME_THESIS.model_dump(),
            "deals": [
                {
                    "id": deal.id,
                    "company": deal.company,
                    "document_type": deal.document_type,
                    "filename": deal.filename,
                }
                for deal in list_deals()
            ],
        }

    @app.get("/v1/deals/pipeline")
    def deal_pipeline() -> dict[str, Any]:
        return {"opportunities": pipe.list_pipeline()}

    @app.get("/v1/deals/{deal_id}")
    def get_deal_package(deal_id: str) -> dict[str, Any]:
        try:
            deal = get_deal(deal_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="deal not found") from exc
        opportunity = pipe.get(f"opp-{deal_id}")
        return {
            "deal": {
                "id": deal.id,
                "company": deal.company,
                "document_type": deal.document_type,
                "filename": deal.filename,
                "text": deal.text,
            },
            "opportunity": None if opportunity is None else opportunity.model_dump(),
        }

    @app.post("/v1/deals/intake")
    def intake_deal(body: DealIntakeRequest) -> dict[str, Any]:
        try:
            deal = get_deal(body.deal_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="deal not found") from exc
        state = graph.start(intake_task(deal), run_id=body.run_id, query_id=deal.id)
        _persist(run_store, graph, state)
        opportunity = pipe.get(f"opp-{deal.id}")
        return {
            "run_id": state.get("run_id"),
            "status": state.get("status"),
            "interrupt": (state.get("pending_action") if state.get("status") == "interrupted" else None),
            "opportunity": None if opportunity is None else opportunity.model_dump(),
            "state": {
                "task": state.get("task"),
                "status": state.get("status"),
                "pending_action": state.get("pending_action"),
                "tool_events": state.get("tool_events"),
            },
        }

    site_dir = Path(__file__).resolve().parents[2] / "site"
    if site_dir.exists():
        app.mount("/ui", StaticFiles(directory=site_dir, html=True), name="ui")

    return app


app = create_app()
