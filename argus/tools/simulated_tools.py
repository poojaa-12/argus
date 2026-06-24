from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from argus.tools.errors import ExecutorError, MalformedResponseError, PermanentToolError, ToolTimeoutError


ERROR_MAP = {
    "timeout": ToolTimeoutError,
    "malformed": MalformedResponseError,
    "executor": ExecutorError,
    "permanent": PermanentToolError,
}


@dataclass
class DeterministicToolEngine:
    """
    Simulates tools with deterministic failure scripts.

    payload supports:
      - key: scenario key, used to look up call script.
      - mode: "normal" for primary tool or "fallback" for fallback tool.
    script values are lists of tokens consumed per call:
      - "ok" => success
      - "timeout" | "malformed" | "executor" | "permanent" => raise mapped error
    """

    scripts: dict[str, list[str]]
    counters: dict[str, int] = field(default_factory=dict)

    def available_tools(self) -> set[str]:
        tools: set[str] = set()
        for script_key in self.scripts:
            parts = script_key.split(":")
            if len(parts) == 3:
                tools.add(parts[1])
        return tools

    def call(self, tool_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        key = payload["key"]
        mode = payload.get("mode", "normal")
        script_key = f"{key}:{tool_name}:{mode}"
        script = self.scripts.get(script_key, ["ok"])
        index = self.counters.get(script_key, 0)
        token = script[min(index, len(script) - 1)]
        self.counters[script_key] = index + 1

        if token == "ok":
            return {
                "tool": tool_name,
                "key": key,
                "mode": mode,
                "status": "ok",
                "simulated_latency_ms": float(payload.get("simulated_latency_ms", 0.0)),
            }

        exc_type = ERROR_MAP[token]
        raise exc_type(f"{tool_name} failed for {key} with {token}")

