from __future__ import annotations

from fastapi.testclient import TestClient

from argus.evals.judge.dataset import build_corpus, build_suite
from argus.graph.checkpoint import MemoryCheckpointStore
from argus.graph.policy import ScriptedPolicy
from argus.graph.runtime import GraphRuntime
from argus.runtime_config import RuntimeConfig
from argus.serving.api import create_app
from argus.serving.store import InMemoryRunStore, SqliteRunStore
from argus.tools.research_tools import GraphToolEngine


def _runtime() -> GraphRuntime:
    suite = build_suite()
    return GraphRuntime.create(
        config=RuntimeConfig(),
        policy=ScriptedPolicy(catalog={item["id"]: item for item in suite}),
        tools=GraphToolEngine(corpus=build_corpus(suite)),
        checkpoints=MemoryCheckpointStore(),
    )


def test_hitl_interrupt_and_resume_destructive_tool() -> None:
    runtime = _runtime()
    item = next(row for row in build_suite() if row["id"] == "dr-050")
    state = runtime.start(item["query"], run_id="hitl-delete", query_id=item["id"])
    assert state["status"] == "interrupted"
    inspected = runtime.inspect("hitl-delete")
    assert inspected["interrupt"]["destructive"] is True
    resumed = runtime.resume("hitl-delete", "approved")
    assert resumed["status"] == "completed"
    assert any(event["tool_name"] == "delete_record" for event in resumed["tool_events"])


def test_hitl_reject_skips_destructive_tool() -> None:
    runtime = _runtime()
    item = next(row for row in build_suite() if row["id"] == "dr-049")
    runtime.start(item["query"], run_id="hitl-reject", query_id=item["id"])
    resumed = runtime.resume("hitl-reject", "reject")
    assert resumed["status"] == "rejected"
    assert all(event["tool_name"] != "db_write" for event in resumed["tool_events"])


def test_api_inspect_and_resume(tmp_path) -> None:
    runtime = _runtime()
    store = InMemoryRunStore()
    client = TestClient(create_app(runtime=runtime, store=store))
    item = next(row for row in build_suite() if row["id"] == "dr-048")
    started = client.post("/v1/runs", json={"goal": item["query"], "query_id": item["id"], "run_id": "api-048"})
    assert started.status_code == 200
    body = started.json()
    assert body["status"] == "interrupted"
    inspected = client.get("/v1/runs/api-048/state")
    assert inspected.status_code == 200
    assert inspected.json()["state"]["status"] == "interrupted"
    resumed = client.post("/v1/runs/api-048/resume", json={"feedback": "target table operator_records"})
    assert resumed.status_code == 200
    assert resumed.json()["status"] == "completed"
    with client.websocket_connect("/v1/runs/api-048/events") as websocket:
        event = websocket.receive_json()
        assert "event" in event


def test_sqlite_run_store_roundtrip(tmp_path) -> None:
    store = SqliteRunStore(str(tmp_path / "argus.db"))
    store.upsert_run("r1", "interrupted", "task", {"run_id": "r1", "status": "interrupted"})
    store.append_event("r1", "run_started", {"task": "task"})
    loaded = store.get_run("r1")
    assert loaded is not None
    assert loaded["status"] == "interrupted"
    assert store.list_events("r1")[0]["event"] == "run_started"
