from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class Citation(BaseModel):
    field: str
    quote: str
    page: int


class DealExtraction(BaseModel):
    deal_id: str
    company: str
    document_type: Literal["CIM", "teaser"]
    sector: str | None = None
    headquarters: str | None = None
    revenue_m: float | None = None
    yoy_growth_pct: float | None = None
    ebitda_m: float | None = None
    ebitda_margin_pct: float | None = None
    net_debt_ebitda: float | None = None
    recurring_revenue_pct: float | None = None
    employees: int | None = None
    summary: str = ""
    risks: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)


class ScoreBreakdown(BaseModel):
    sector: int = 0
    scale: int = 0
    growth: int = 0
    geography: int = 0
    leverage: int = 0
    risk: int = 0


class ScoredDeal(BaseModel):
    deal_id: str
    company: str
    score: int
    recommendation: Literal["advance", "diligence", "pass"]
    rationale: str
    breakdown: ScoreBreakdown
    extraction: DealExtraction


class FirmThesis(BaseModel):
    firm_id: str = "acme-capital"
    firm_name: str = "Acme Capital"
    mandate: str
    sectors: list[str]
    geographies: list[str]
    revenue_m_min: float
    revenue_m_max: float
    growth_pct_min: float
    max_net_debt_ebitda: float
    avoid: list[str]


class DealRecord(BaseModel):
    id: str
    company: str
    document_type: Literal["CIM", "teaser"]
    filename: str
    text: str
    gold: DealExtraction


class Opportunity(BaseModel):
    opportunity_id: str
    account_name: str
    deal_id: str
    stage: str
    score: int | None = None
    recommendation: str | None = None
    source_document: str | None = None
    sharepoint_path: str | None = None
    extraction: dict[str, Any] = Field(default_factory=dict)
    run_id: str | None = None
    status: str = "pending_approval"


class CrmWriteResult(BaseModel):
    written: bool
    opportunity: Opportunity
    sharepoint_path: str
