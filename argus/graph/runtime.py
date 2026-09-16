from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import uuid

from argus.graph.checkpoint import CheckpointStore, MemoryCheckpointStore, build_checkpoint_store
from argus.graph.graph import compile_graph
from argus.graph.hitl import interrupt_payload
from argus.graph.nodes import NodeContext, make_node_context
from argus.graph.policy import ScriptedPolicy
from argus.graph.state import initial_state
from argus.observability.otel import TokenBudgetRecorder
from argus.runtime_config import RuntimeConfig
from argus.tools.research_tools import GraphToolEngine


@dataclass
class GraphRuntime:
    ctx: NodeContext
    engine: str = "local"
    checkpoints: CheckpointStore = field(default_factory=MemoryCheckpointStore)
    events: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    _app: Any = field(init=False)

    def __post_init__(self) -> None:
        self._app = compile_graph(self.ctx, engine=self.engine)

    @classmethod
    def create(
        cls,
        *,
        config: RuntimeConfig | None = None,
        policy: ScriptedPolicy | None = None,
        tools: GraphToolEngine | None = None,
        engine: str = "local",
        checkpoints: CheckpointStore | None = None,
        recorder: TokenBudgetRecorder | None = None,
    ) -> GraphRuntime:
        runtime_config = config or RuntimeConfig()
        store = checkpoints or build_checkpoint_store(runtime_config.redis_url)
        ctx = make_node_context(policy=policy, tools=tools, config=runtime_config, recorder=recorder)
        return cls(ctx=ctx, engine=engine, checkpoints=store)

    def _config(self, run_id: str) -> dict[str, Any]:
        return {"configurable": {"thread_id": run_id}}

    def _record(self, run_id: str, event: str, **payload: Any) -> None:
        self.events.setdefault(run_id, []).append({"event": event, **payload})

    def start(self, task: str, *, run_id: str | None = None, query_id: str | None = None) -> dict[str, Any]:
        run_id = run_id or str(uuid.uuid4())
        state = initial_state(
            task,
            run_id,
            context_window=self.ctx.config.context_window,
            compress_threshold=self.ctx.config.compress_threshold,
            query_id=query_id,
        )
        self._record(run_id, "run_started", task=task, query_id=query_id)
        result = self._app.invoke(state, self._config(run_id))
        self.checkpoints.put(run_id, result)
        self._record(run_id, "run_paused" if result.get("status") == "interrupted" else "run_completed", status=result.get("status"))
        return result

    def resume(self, run_id: str, feedback: str) -> dict[str, Any]:
        approved = feedback.strip().lower() not in {"reject", "deny", "no"}
        update = {"human_feedback": feedback, "hitl_approved": approved, "needs_clarification": False}
        self._record(run_id, "human_feedback", feedback=feedback, approved=approved)
        result = self._app.invoke(update, self._config(run_id), resume=True)
        self.checkpoints.put(run_id, result)
        self._record(run_id, "run_paused" if result.get("status") == "interrupted" else "run_completed", status=result.get("status"))
        return result

    def get_state(self, run_id: str) -> dict[str, Any] | None:
        cached = self.checkpoints.get(run_id)
        if cached is not None:
            return cached
        return self._app.get_state(self._config(run_id))

    def inspect(self, run_id: str) -> dict[str, Any]:
        state = self.get_state(run_id) or {}
        payload = {"state": state, "events": list(self.events.get(run_id) or [])}
        if state.get("status") == "interrupted":
            payload["interrupt"] = interrupt_payload(state)
        return payload
