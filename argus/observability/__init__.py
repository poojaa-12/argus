from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class StructuredLogger:
    def log_event(self, event: str, **fields: Any) -> None:
        raise NotImplementedError


class MetricsExporter:
    def increment(self, metric_name: str, value: int = 1, **labels: str) -> None:
        raise NotImplementedError


class NoopStructuredLogger(StructuredLogger):
    def log_event(self, event: str, **fields: Any) -> None:
        _ = (event, fields)


class NoopMetricsExporter(MetricsExporter):
    def increment(self, metric_name: str, value: int = 1, **labels: str) -> None:
        _ = (metric_name, value, labels)


@dataclass
class InMemoryStructuredLogger(StructuredLogger):
    events: list[dict[str, Any]] = field(default_factory=list)

    def log_event(self, event: str, **fields: Any) -> None:
        self.events.append({"event": event, **fields})


@dataclass
class InMemoryMetricsExporter(MetricsExporter):
    counters: dict[tuple[str, tuple[tuple[str, str], ...]], int] = field(default_factory=dict)

    def increment(self, metric_name: str, value: int = 1, **labels: str) -> None:
        key = (metric_name, tuple(sorted(labels.items())))
        self.counters[key] = self.counters.get(key, 0) + value
