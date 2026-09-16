from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import sqlite3
from typing import Any, Protocol


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunStore(Protocol):
    def upsert_run(self, run_id: str, status: str, task: str, state: dict[str, Any], human_feedback: str | None = None) -> None: ...

    def get_run(self, run_id: str) -> dict[str, Any] | None: ...

    def append_event(self, run_id: str, event: str, payload: dict[str, Any] | None = None) -> None: ...

    def list_events(self, run_id: str) -> list[dict[str, Any]]: ...

    def save_eval_result(self, suite: str, payload: dict[str, Any]) -> None: ...


@dataclass
class InMemoryRunStore:
    runs: dict[str, dict[str, Any]] = field(default_factory=dict)
    events: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    evals: list[dict[str, Any]] = field(default_factory=list)

    def upsert_run(self, run_id: str, status: str, task: str, state: dict[str, Any], human_feedback: str | None = None) -> None:
        now = _utcnow()
        existing = self.runs.get(run_id) or {"created_at": now}
        existing.update(
            {
                "run_id": run_id,
                "status": status,
                "task": task,
                "state": state,
                "human_feedback": human_feedback,
                "updated_at": now,
            }
        )
        self.runs[run_id] = existing

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        return self.runs.get(run_id)

    def append_event(self, run_id: str, event: str, payload: dict[str, Any] | None = None) -> None:
        self.events.setdefault(run_id, []).append({"event": event, "payload": payload or {}, "created_at": _utcnow()})

    def list_events(self, run_id: str) -> list[dict[str, Any]]:
        return list(self.events.get(run_id) or [])

    def save_eval_result(self, suite: str, payload: dict[str, Any]) -> None:
        self.evals.append({"suite": suite, "payload": payload, "created_at": _utcnow()})


class SqliteRunStore:
    def __init__(self, path: str) -> None:
        self.path = path.replace("sqlite:///", "").replace("sqlite://", "")
        if self.path.startswith("/"):
            db_path = self.path
        else:
            db_path = self.path or ":memory:"
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self.ensure_schema()

    def ensure_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                task TEXT,
                state_json TEXT NOT NULL,
                human_feedback TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS run_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                event TEXT NOT NULL,
                payload TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS eval_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                suite TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        self._conn.commit()

    def upsert_run(self, run_id: str, status: str, task: str, state: dict[str, Any], human_feedback: str | None = None) -> None:
        now = _utcnow()
        existing = self.get_run(run_id)
        created = existing["created_at"] if existing else now
        self._conn.execute(
            """
            INSERT INTO runs (run_id, status, task, state_json, human_feedback, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                status=excluded.status,
                task=excluded.task,
                state_json=excluded.state_json,
                human_feedback=excluded.human_feedback,
                updated_at=excluded.updated_at
            """,
            (run_id, status, task, json.dumps(state, default=str), human_feedback, created, now),
        )
        self._conn.commit()

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        row = self._conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        if row is None:
            return None
        return {
            "run_id": row["run_id"],
            "status": row["status"],
            "task": row["task"],
            "state": json.loads(row["state_json"]),
            "human_feedback": row["human_feedback"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def append_event(self, run_id: str, event: str, payload: dict[str, Any] | None = None) -> None:
        self._conn.execute(
            "INSERT INTO run_events (run_id, event, payload, created_at) VALUES (?, ?, ?, ?)",
            (run_id, event, json.dumps(payload or {}, default=str), _utcnow()),
        )
        self._conn.commit()

    def list_events(self, run_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT event, payload, created_at FROM run_events WHERE run_id = ? ORDER BY id",
            (run_id,),
        ).fetchall()
        return [
            {"event": row["event"], "payload": json.loads(row["payload"] or "{}"), "created_at": row["created_at"]}
            for row in rows
        ]

    def save_eval_result(self, suite: str, payload: dict[str, Any]) -> None:
        self._conn.execute(
            "INSERT INTO eval_results (suite, payload, created_at) VALUES (?, ?, ?)",
            (suite, json.dumps(payload, default=str), _utcnow()),
        )
        self._conn.commit()


class PostgresRunStore:
    def __init__(self, dsn: str) -> None:
        import psycopg

        self._dsn = dsn
        self._conn = psycopg.connect(dsn, autocommit=True)
        self.ensure_schema()

    def ensure_schema(self) -> None:
        with self._conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    task TEXT,
                    state_json JSONB NOT NULL,
                    human_feedback TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS run_events (
                    id BIGSERIAL PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    event TEXT NOT NULL,
                    payload JSONB,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS eval_results (
                    id BIGSERIAL PRIMARY KEY,
                    suite TEXT NOT NULL,
                    payload JSONB NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )

    def upsert_run(self, run_id: str, status: str, task: str, state: dict[str, Any], human_feedback: str | None = None) -> None:
        with self._conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO runs (run_id, status, task, state_json, human_feedback)
                VALUES (%s, %s, %s, %s::jsonb, %s)
                ON CONFLICT (run_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    task = EXCLUDED.task,
                    state_json = EXCLUDED.state_json,
                    human_feedback = EXCLUDED.human_feedback,
                    updated_at = NOW()
                """,
                (run_id, status, task, json.dumps(state, default=str), human_feedback),
            )

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT run_id, status, task, state_json, human_feedback, created_at, updated_at FROM runs WHERE run_id = %s",
                (run_id,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        state = row[3]
        if isinstance(state, str):
            state = json.loads(state)
        return {
            "run_id": row[0],
            "status": row[1],
            "task": row[2],
            "state": state,
            "human_feedback": row[4],
            "created_at": str(row[5]),
            "updated_at": str(row[6]),
        }

    def append_event(self, run_id: str, event: str, payload: dict[str, Any] | None = None) -> None:
        with self._conn.cursor() as cur:
            cur.execute(
                "INSERT INTO run_events (run_id, event, payload) VALUES (%s, %s, %s::jsonb)",
                (run_id, event, json.dumps(payload or {}, default=str)),
            )

    def list_events(self, run_id: str) -> list[dict[str, Any]]:
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT event, payload, created_at FROM run_events WHERE run_id = %s ORDER BY id",
                (run_id,),
            )
            rows = cur.fetchall()
        out = []
        for event, payload, created_at in rows:
            if isinstance(payload, str):
                payload = json.loads(payload)
            out.append({"event": event, "payload": payload or {}, "created_at": str(created_at)})
        return out

    def save_eval_result(self, suite: str, payload: dict[str, Any]) -> None:
        with self._conn.cursor() as cur:
            cur.execute(
                "INSERT INTO eval_results (suite, payload) VALUES (%s, %s::jsonb)",
                (suite, json.dumps(payload, default=str)),
            )


def build_store(url: str | None = None) -> RunStore:
    if not url or url.startswith("memory"):
        return InMemoryRunStore()
    if url.startswith("sqlite"):
        return SqliteRunStore(url)
    if url.startswith("postgres"):
        return PostgresRunStore(url)
    return InMemoryRunStore()
