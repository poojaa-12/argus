from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path


@dataclass
class RuntimeConfig:
    max_retries: int = 2
    base_delay_s: float = 0.0
    jitter_s: float = 0.0
    default_step_timeout_ms: int | None = None
    eval_seed: int = 1337

    @classmethod
    def from_env(cls) -> RuntimeConfig:
        return cls(
            max_retries=int(os.getenv("ARGUS_MAX_RETRIES", "2")),
            base_delay_s=float(os.getenv("ARGUS_BASE_DELAY_S", "0.0")),
            jitter_s=float(os.getenv("ARGUS_JITTER_S", "0.0")),
            default_step_timeout_ms=(
                int(os.getenv("ARGUS_DEFAULT_STEP_TIMEOUT_MS"))
                if os.getenv("ARGUS_DEFAULT_STEP_TIMEOUT_MS")
                else None
            ),
            eval_seed=int(os.getenv("ARGUS_EVAL_SEED", "1337")),
        )

    @classmethod
    def from_file(cls, path: str | Path) -> RuntimeConfig:
        config_path = Path(path)
        raw = json.loads(config_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("Runtime config must be a JSON object")
        return cls(
            max_retries=int(raw.get("max_retries", 2)),
            base_delay_s=float(raw.get("base_delay_s", 0.0)),
            jitter_s=float(raw.get("jitter_s", 0.0)),
            default_step_timeout_ms=(
                int(raw["default_step_timeout_ms"])
                if raw.get("default_step_timeout_ms") is not None
                else None
            ),
            eval_seed=int(raw.get("eval_seed", 1337)),
        )
