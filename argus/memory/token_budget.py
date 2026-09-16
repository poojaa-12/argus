from __future__ import annotations

from typing import Iterable, Mapping

PINNED_KEYS = ("task", "system_instructions", "correlation_id", "context_window")
DEFAULT_CONTEXT_WINDOW = 8192
DEFAULT_COMPRESS_THRESHOLD = 0.8


def count_tokens(text: str) -> int:
    if not text:
        return 0
    try:
        import tiktoken

        encoder = tiktoken.get_encoding("cl100k_base")
        return len(encoder.encode(text))
    except Exception:
        return max(1, (len(text) + 3) // 4)


def messages_token_count(messages: Iterable[Mapping[str, str]]) -> int:
    total = 0
    for message in messages:
        total += count_tokens(str(message.get("content", "")))
    return total


def should_compress(
    token_count: int,
    context_window: int = DEFAULT_CONTEXT_WINDOW,
    threshold: float = DEFAULT_COMPRESS_THRESHOLD,
) -> bool:
    if context_window <= 0:
        return False
    return token_count >= threshold * context_window


def _summarize_tool_content(content: str) -> str:
    marker = "CORE_FACTS:"
    if marker in content:
        cores: list[str] = []
        for chunk in content.split(marker)[1:]:
            core = chunk.strip()
            if "scratch" in core:
                core = core.split("scratch", 1)[0].strip()
            if core:
                cores.append(core)
        omitted = max(0, len(content) - sum(len(part) for part in cores))
        joined = " ".join(cores) if cores else content[-240:]
        return f"summarized_tool_output omitted_chars={omitted} {marker} {joined}"
    if len(content) <= 240:
        return content
    omitted = len(content) - 240
    return f"summarized_tool_output omitted_chars={omitted} {content[:120]} … {content[-80:]}"


def compress_messages(
    messages: list[dict[str, str]],
    *,
    task: str,
    system_instructions: str,
) -> list[dict[str, str]]:
    compressed: list[dict[str, str]] = []
    for message in messages:
        role = message.get("role", "user")
        content = message.get("content", "")
        if role == "tool":
            compressed.append({"role": "tool", "content": _summarize_tool_content(content)})
        else:
            compressed.append({"role": role, "content": content})

    if not any(m.get("role") == "user" and m.get("content") == task for m in compressed):
        compressed.insert(0, {"role": "user", "content": task})
    if not any(m.get("role") == "system" and m.get("content") == system_instructions for m in compressed):
        compressed.insert(0, {"role": "system", "content": system_instructions})
    return compressed


def apply_token_budget(
    messages: list[dict[str, str]],
    *,
    task: str,
    system_instructions: str,
    context_window: int,
    threshold: float = DEFAULT_COMPRESS_THRESHOLD,
    recorder: object | None = None,
) -> tuple[list[dict[str, str]], int, int, bool]:
    before = messages_token_count(messages)
    if not should_compress(before, context_window, threshold):
        return messages, before, before, False
    compressed = compress_messages(messages, task=task, system_instructions=system_instructions)
    after = messages_token_count(compressed)
    if recorder is not None and hasattr(recorder, "record"):
        recorder.record(before, after)
    return compressed, before, after, True
