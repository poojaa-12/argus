from __future__ import annotations

from typing import Annotated, Any, Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field
import operator

DEFAULT_SYSTEM_INSTRUCTIONS = (
    "You are Argus, a Deep Research and Operator agent. "
    "Never drop the original task or these instructions. Cite tool context only."
)


class ResearchFinding(BaseModel):
    query: str
    content: str
    source: str
    tool_name: str = "web_search"


class ToolEvent(BaseModel):
    tool_name: str
    args: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] | None = None
    ok: bool = True
    attempts: int = 1
    used_fallback: bool = False
    error_type: str | None = None


class PendingAction(BaseModel):
    tool_name: str
    args: dict[str, Any] = Field(default_factory=dict)
    destructive: bool = False
    reason: str = ""


class PlanResult(BaseModel):
    subqueries: list[str]
    needs_clarification: bool = False
    operator_steps: list[str] = Field(default_factory=list)


class OperatorDecision(BaseModel):
    action: Literal["tool", "finish", "wait"]
    tool_name: str | None = None
    args: dict[str, Any] = Field(default_factory=dict)
    reason: str = ""
    destructive: bool = False


class AgentStateModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    task: str
    system_instructions: str = DEFAULT_SYSTEM_INSTRUCTIONS
    correlation_id: str | None = None
    run_id: str = ""
    query_id: str | None = None
    context_window: int = 8192
    compress_threshold: float = 0.8
    messages: list[dict[str, str]] = Field(default_factory=list)
    subqueries: list[str] = Field(default_factory=list)
    current_query: str = ""
    research_findings: list[dict[str, Any]] = Field(default_factory=list)
    tool_events: list[dict[str, Any]] = Field(default_factory=list)
    pending_action: dict[str, Any] | None = None
    interrupt_reason: str | None = None
    human_feedback: str | None = None
    needs_clarification: bool = False
    token_count: int = 0
    tokens_before: int = 0
    tokens_after: int = 0
    summarized: bool = False
    status: str = "running"
    final_answer: str = ""
    citations: list[str] = Field(default_factory=list)
    llm_calls: int = 0
    operator_iterations: int = 0
    hitl_approved: bool = False


class AgentState(TypedDict, total=False):
    task: str
    system_instructions: str
    correlation_id: str
    run_id: str
    query_id: str
    context_window: int
    compress_threshold: float
    messages: list[dict[str, str]]
    subqueries: list[str]
    current_query: str
    research_findings: Annotated[list[dict[str, Any]], operator.add]
    tool_events: Annotated[list[dict[str, Any]], operator.add]
    pending_action: dict[str, Any] | None
    interrupt_reason: str | None
    human_feedback: str | None
    needs_clarification: bool
    token_count: int
    tokens_before: int
    tokens_after: int
    summarized: bool
    status: str
    final_answer: str
    citations: list[str]
    llm_calls: Annotated[int, operator.add]
    operator_iterations: int
    hitl_approved: bool


def initial_state(
    task: str,
    run_id: str,
    *,
    context_window: int = 8192,
    compress_threshold: float = 0.8,
    query_id: str | None = None,
    correlation_id: str | None = None,
    system_instructions: str = DEFAULT_SYSTEM_INSTRUCTIONS,
) -> dict[str, Any]:
    return {
        "task": task,
        "system_instructions": system_instructions,
        "correlation_id": correlation_id or run_id,
        "run_id": run_id,
        "query_id": query_id or "",
        "context_window": context_window,
        "compress_threshold": compress_threshold,
        "messages": [
            {"role": "system", "content": system_instructions},
            {"role": "user", "content": task},
        ],
        "subqueries": [],
        "current_query": "",
        "research_findings": [],
        "tool_events": [],
        "pending_action": None,
        "interrupt_reason": None,
        "human_feedback": None,
        "needs_clarification": False,
        "token_count": 0,
        "tokens_before": 0,
        "tokens_after": 0,
        "summarized": False,
        "status": "running",
        "final_answer": "",
        "citations": [],
        "llm_calls": 0,
        "operator_iterations": 0,
        "hitl_approved": False,
    }
