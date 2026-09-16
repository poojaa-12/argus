from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Callable, Iterator

from opentelemetry import metrics, trace

from argus.observability import MetricsExporter, StructuredLogger


class TokenBudgetRecorder:
    """In-process token counters used by compression middleware and evals."""

    def __init__(self) -> None:
        self.tokens_before: int = 0
        self.tokens_after: int = 0
        self.compressions: int = 0

    def record(self, before: int, after: int) -> None:
        self.compressions += 1
        if before >= self.tokens_before:
            self.tokens_before = before
            self.tokens_after = after
        try:
            meter = metrics.get_meter("argus")
            meter.create_counter("argus.tokens.before").add(before)
            meter.create_counter("argus.tokens.after").add(after)
        except Exception:
            pass

    @property
    def reduction_rate(self) -> float:
        if self.tokens_before <= 0:
            return 0.0
        return max(0.0, (self.tokens_before - self.tokens_after) / self.tokens_before)


class OpenTelemetryLogger(StructuredLogger):
    def log_event(self, event: str, **fields: Any) -> None:
        tracer = trace.get_tracer("argus")
        with tracer.start_as_current_span(f"argus.event.{event}") as span:
            for key, value in fields.items():
                if value is None:
                    continue
                span.set_attribute(f"argus.{key}", str(value))


class OpenTelemetryMetrics(MetricsExporter):
    def increment(self, metric_name: str, value: int = 1, **labels: str) -> None:
        meter = metrics.get_meter("argus")
        meter.create_counter(metric_name).add(value, attributes=labels or None)


def configure_otel_for_tests() -> tuple[Any, Any]:
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import InMemoryMetricReader
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    span_exporter = InMemorySpanExporter()
    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(SimpleSpanProcessor(span_exporter))
    trace.set_tracer_provider(tracer_provider)
    reader = InMemoryMetricReader()
    metrics.set_meter_provider(MeterProvider(metric_readers=[reader]))
    return span_exporter, reader


@contextmanager
def node_span(name: str, state: dict[str, Any]) -> Iterator[None]:
    tracer = trace.get_tracer("argus")
    with tracer.start_as_current_span(f"argus.graph.{name}") as span:
        span.set_attribute("argus.run_id", str(state.get("run_id", "")))
        span.set_attribute("argus.status", str(state.get("status", "")))
        yield


def traced(name: str, fn: Callable[[dict[str, Any]], dict[str, Any]]) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def wrapped(state: dict[str, Any]) -> dict[str, Any]:
        with node_span(name, state):
            return fn(state)

    return wrapped
