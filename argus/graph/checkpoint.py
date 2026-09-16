from __future__ import annotations

import json
from typing import Any, Protocol


class CheckpointStore(Protocol):
    def put(self, thread_id: str, state: dict[str, Any]) -> None: ...

    def get(self, thread_id: str) -> dict[str, Any] | None: ...


class MemoryCheckpointStore:
    def __init__(self) -> None:
        self._data: dict[str, dict[str, Any]] = {}

    def put(self, thread_id: str, state: dict[str, Any]) -> None:
        self._data[thread_id] = json.loads(json.dumps(state, default=str))

    def get(self, thread_id: str) -> dict[str, Any] | None:
        blob = self._data.get(thread_id)
        return json.loads(json.dumps(blob, default=str)) if blob is not None else None


class RedisCheckpointStore:
    def __init__(self, url: str) -> None:
        import redis

        self.client = redis.from_url(url)
        self.prefix = "argus:ckpt:"

    def put(self, thread_id: str, state: dict[str, Any]) -> None:
        self.client.set(f"{self.prefix}{thread_id}", json.dumps(state, default=str))

    def get(self, thread_id: str) -> dict[str, Any] | None:
        raw = self.client.get(f"{self.prefix}{thread_id}")
        if not raw:
            return None
        return json.loads(raw)


def build_checkpoint_store(redis_url: str | None = None) -> CheckpointStore:
    if redis_url:
        try:
            store = RedisCheckpointStore(redis_url)
            store.client.ping()
            return store
        except Exception:
            pass
    return MemoryCheckpointStore()
