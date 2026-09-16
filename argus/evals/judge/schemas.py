from __future__ import annotations

from pydantic import BaseModel, Field


class ClaimCheck(BaseModel):
    claim: str
    entailed: bool
    source: str | None = None


class ToolSelectionScore(BaseModel):
    expected: list[str]
    actual: list[str]
    correct: int
    total: int
    accuracy: float


class TrajectoryStats(BaseModel):
    llm_calls: int
    tool_calls: int
    operator_iterations: int


class JudgeVerdict(BaseModel):
    query_id: str
    tool_selection: ToolSelectionScore
    hallucination_rate: float
    claims: list[ClaimCheck] = Field(default_factory=list)
    trajectory: TrajectoryStats
    token_reduction: float | None = None
    status: str = "completed"


class JudgeSuiteReport(BaseModel):
    seed: int
    total: int
    tool_selection_accuracy: float
    hallucination_rate: float
    mean_llm_calls: float
    token_reduction: float | None = None
    verdicts: list[JudgeVerdict] = Field(default_factory=list)
