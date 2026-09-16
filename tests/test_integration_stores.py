from __future__ import annotations

import os

import pytest

from argus.graph.checkpoint import RedisCheckpointStore
from argus.serving.store import PostgresRunStore


@pytest.mark.skipif(not os.getenv("ARGUS_INTEGRATION"), reason="set ARGUS_INTEGRATION=1 with docker compose up")
def test_redis_checkpoint_roundtrip() -> None:
    store = RedisCheckpointStore(os.getenv("ARGUS_REDIS_URL", "redis://localhost:6379/0"))
    store.put("itest", {"run_id": "itest", "status": "interrupted"})
    loaded = store.get("itest")
    assert loaded is not None
    assert loaded["status"] == "interrupted"


@pytest.mark.skipif(not os.getenv("ARGUS_INTEGRATION"), reason="set ARGUS_INTEGRATION=1 with docker compose up")
def test_postgres_run_store_roundtrip() -> None:
    dsn = os.getenv("ARGUS_DATABASE_URL", "postgresql://argus:argus@localhost:5434/argus")
    store = PostgresRunStore(dsn)
    store.upsert_run("itest", "completed", "goal", {"run_id": "itest", "status": "completed"})
    loaded = store.get_run("itest")
    assert loaded is not None
    assert loaded["status"] == "completed"
