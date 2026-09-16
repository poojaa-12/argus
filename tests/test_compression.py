from __future__ import annotations

from argus.graph.state import DEFAULT_SYSTEM_INSTRUCTIONS
from argus.memory.token_budget import apply_token_budget, compress_messages, count_tokens, should_compress
from argus.observability.otel import TokenBudgetRecorder


def test_count_tokens_positive() -> None:
    assert count_tokens("hello world") >= 1


def test_should_compress_at_80_percent() -> None:
    assert should_compress(80, context_window=100, threshold=0.8)
    assert not should_compress(79, context_window=100, threshold=0.8)


def test_compress_preserves_task_and_instructions() -> None:
    task = "Research fusion energy"
    bloated = ("PADDING " * 400) + "CORE_FACTS: tokamak confinement is hard."
    messages = [
        {"role": "system", "content": DEFAULT_SYSTEM_INSTRUCTIONS},
        {"role": "user", "content": task},
        {"role": "tool", "content": bloated},
    ]
    compressed = compress_messages(messages, task=task, system_instructions=DEFAULT_SYSTEM_INSTRUCTIONS)
    assert compressed[0]["content"] == DEFAULT_SYSTEM_INSTRUCTIONS or any(
        m["content"] == DEFAULT_SYSTEM_INSTRUCTIONS for m in compressed
    )
    assert any(m["content"] == task for m in compressed)
    tool = next(m for m in compressed if m["role"] == "tool")
    assert "CORE_FACTS:" in tool["content"]
    assert "tokamak confinement is hard." in tool["content"]
    assert len(tool["content"]) < len(bloated)


def test_apply_token_budget_records_reduction() -> None:
    task = "keep this task"
    instructions = "keep these instructions"
    bloated = ("x" * 8000) + "CORE_FACTS: only this fact matters."
    messages = [
        {"role": "system", "content": instructions},
        {"role": "user", "content": task},
        {"role": "tool", "content": bloated},
    ]
    recorder = TokenBudgetRecorder()
    compressed, before, after, summarized = apply_token_budget(
        messages,
        task=task,
        system_instructions=instructions,
        context_window=200,
        threshold=0.8,
        recorder=recorder,
    )
    assert summarized is True
    assert after < before
    assert recorder.reduction_rate > 0.35
    assert any(m["content"] == task for m in compressed)
    assert any(m["content"] == instructions for m in compressed)
