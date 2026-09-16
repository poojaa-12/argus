from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from argus.deals.engine import run_tool as run_deal_tool
from argus.deals.store import DealCloudStore, get_store
from argus.tools.errors import ExecutorError, MalformedResponseError, PermanentToolError, ToolTimeoutError
from argus.tools.simulated_tools import DeterministicToolEngine

RESEARCH_TOOLS = {"web_search", "read_document", "primary_search", "primary_summarize", "backup_search"}
DEAL_TOOLS = {"cim_extract", "thesis_score", "crm_upsert", "sharepoint_attach"}
DESTRUCTIVE_TOOLS = {"db_write", "delete_record", "crm_upsert", "sharepoint_attach"}
GRAPH_TOOLS = RESEARCH_TOOLS | DESTRUCTIVE_TOOLS | DEAL_TOOLS | {
    "primary_enrich",
    "backup_enrich",
}

ERROR_MAP = {
    "timeout": ToolTimeoutError,
    "malformed": MalformedResponseError,
    "executor": ExecutorError,
    "permanent": PermanentToolError,
}

BLOAT_PREFIX = "PADDING:" + ("lorem ipsum scratchpad overflow " * 80)
BLOAT_MARKER = "CORE_FACTS:"


@dataclass
class GraphToolEngine:
    """Research + operator tools that still honor deterministic failure scripts."""

    scripts: dict[str, list[str]] = field(default_factory=dict)
    corpus: dict[str, str] = field(default_factory=dict)
    bloat_chars: int = 0
    pipeline: DealCloudStore | None = None
    inner: DeterministicToolEngine = field(init=False)

    def __post_init__(self) -> None:
        self.inner = DeterministicToolEngine(scripts=self.scripts)

    def available_tools(self) -> set[str]:
        return set(GRAPH_TOOLS) | self.inner.available_tools()

    def _bloated(self, content: str) -> str:
        if self.bloat_chars <= 0:
            return f"{BLOAT_MARKER} {content}"
        n_tokens = max(80, self.bloat_chars // 8)
        pad = " ".join(f"scratch{i:04d}" for i in range(n_tokens))
        return f"{pad}\n{BLOAT_MARKER} {content}"

    def call(self, tool_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        key = str(payload.get("key", payload.get("query", "graph")))
        mode = payload.get("mode", "normal")
        script_key = f"{key}:{tool_name}:{mode}"
        if script_key in self.scripts:
            return self.inner.call(tool_name, payload)

        query = str(payload.get("query") or payload.get("key") or "")
        if tool_name in RESEARCH_TOOLS:
            content = self.corpus.get(query) or self.corpus.get(key) or f"No corpus hit for {query}"
            return {
                "tool": tool_name,
                "key": key,
                "query": query,
                "status": "ok",
                "content": self._bloated(content),
                "source": f"corpus:{query or key}",
                "simulated_latency_ms": float(payload.get("simulated_latency_ms", 0.0)),
            }

        if tool_name in DEAL_TOOLS:
            result = run_deal_tool(tool_name, payload, store=self.pipeline or get_store())
            result.setdefault("key", key)
            result.setdefault("simulated_latency_ms", float(payload.get("simulated_latency_ms", 0.0)))
            return result

        if tool_name in DESTRUCTIVE_TOOLS:
            return {
                "tool": tool_name,
                "key": key,
                "status": "ok",
                "written": True,
                "args": {k: v for k, v in payload.items() if k != "key"},
                "content": f"{tool_name} applied",
                "source": f"operator:{tool_name}",
                "simulated_latency_ms": float(payload.get("simulated_latency_ms", 0.0)),
            }

        return self.inner.call(tool_name, payload)
