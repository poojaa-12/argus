from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path


DEFAULT_DESTRUCTIVE_TOOLS = ("db_write", "delete_record")


def _parse_tool_list(raw: str | None) -> tuple[str, ...]:
    if not raw:
        return DEFAULT_DESTRUCTIVE_TOOLS
    tools = tuple(part.strip() for part in raw.split(",") if part.strip())
    return tools or DEFAULT_DESTRUCTIVE_TOOLS


@dataclass
class RuntimeConfig:
    max_retries: int = 2
    base_delay_s: float = 0.0
    jitter_s: float = 0.0
    default_step_timeout_ms: int | None = None
    eval_seed: int = 1337
    context_window: int = 8192
    compress_threshold: float = 0.8
    hitl_destructive_tools: tuple[str, ...] = DEFAULT_DESTRUCTIVE_TOOLS
    llm_provider: str = "scripted"
    llm_model: str = "gpt-4o-mini"
    max_operator_iters: int = 6
    redis_url: str | None = None
    database_url: str | None = None

    @classmethod
    def from_env(cls) -> RuntimeConfig:
        timeout_raw = os.getenv("ARGUS_DEFAULT_STEP_TIMEOUT_MS")
        return cls(
            max_retries=int(os.getenv("ARGUS_MAX_RETRIES", "2")),
            base_delay_s=float(os.getenv("ARGUS_BASE_DELAY_S", "0.0")),
            jitter_s=float(os.getenv("ARGUS_JITTER_S", "0.0")),
            default_step_timeout_ms=int(timeout_raw) if timeout_raw else None,
            eval_seed=int(os.getenv("ARGUS_EVAL_SEED", "1337")),
            context_window=int(os.getenv("ARGUS_CONTEXT_WINDOW", "8192")),
            compress_threshold=float(os.getenv("ARGUS_COMPRESS_THRESHOLD", "0.8")),
            hitl_destructive_tools=_parse_tool_list(os.getenv("ARGUS_DESTRUCTIVE_TOOLS")),
            llm_provider=os.getenv("ARGUS_LLM_PROVIDER", "scripted"),
            llm_model=os.getenv("ARGUS_LLM_MODEL", "gpt-4o-mini"),
            max_operator_iters=int(os.getenv("ARGUS_MAX_OPERATOR_ITERS", "6")),
            redis_url=os.getenv("ARGUS_REDIS_URL"),
            database_url=os.getenv("ARGUS_DATABASE_URL"),
        )

    @classmethod
    def from_file(cls, path: str | Path) -> RuntimeConfig:
        config_path = Path(path)
        raw = json.loads(config_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("Runtime config must be a JSON object")
        timeout = raw.get("default_step_timeout_ms")
        destructive = raw.get("hitl_destructive_tools")
        if isinstance(destructive, list):
            hitl_tools = tuple(str(item) for item in destructive)
        else:
            hitl_tools = _parse_tool_list(raw.get("hitl_destructive_tools"))
        return cls(
            max_retries=int(raw.get("max_retries", 2)),
            base_delay_s=float(raw.get("base_delay_s", 0.0)),
            jitter_s=float(raw.get("jitter_s", 0.0)),
            default_step_timeout_ms=int(timeout) if timeout is not None else None,
            eval_seed=int(raw.get("eval_seed", 1337)),
            context_window=int(raw.get("context_window", 8192)),
            compress_threshold=float(raw.get("compress_threshold", 0.8)),
            hitl_destructive_tools=hitl_tools or DEFAULT_DESTRUCTIVE_TOOLS,
            llm_provider=str(raw.get("llm_provider", "scripted")),
            llm_model=str(raw.get("llm_model", "gpt-4o-mini")),
            max_operator_iters=int(raw.get("max_operator_iters", 6)),
            redis_url=raw.get("redis_url"),
            database_url=raw.get("database_url"),
        )
