from __future__ import annotations

from argus.deals.corpus import ACME_THESIS
from argus.deals.schemas import DealExtraction, FirmThesis, ScoreBreakdown, ScoredDeal


def _contains_any(haystack: str, needles: list[str]) -> bool:
    lower = haystack.lower()
    return any(needle.lower() in lower for needle in needles)


def score_deal(extraction: DealExtraction, thesis: FirmThesis | None = None) -> ScoredDeal:
    thesis = thesis or ACME_THESIS
    sector_text = extraction.sector or ""
    hq = extraction.headquarters or ""

    sector_pts = 0
    if _contains_any(sector_text, ["project-based", "EPC", "healthcare", "clinic", "pharma", "pharmaceutical", "biotech", *thesis.avoid]):
        sector_pts = 0
    elif _contains_any(sector_text, ["software", "saas", "data", "payments"]):
        sector_pts = 30
    elif _contains_any(sector_text, thesis.sectors):
        sector_pts = 24
    else:
        sector_pts = 8

    scale_pts = 0
    if extraction.revenue_m is None:
        scale_pts = 8
    elif thesis.revenue_m_min <= extraction.revenue_m <= thesis.revenue_m_max:
        scale_pts = 20
    elif extraction.revenue_m < thesis.revenue_m_min:
        scale_pts = 10
    else:
        scale_pts = 12

    growth_pts = 0
    if extraction.yoy_growth_pct is None:
        growth_pts = 6
    elif extraction.yoy_growth_pct >= thesis.growth_pct_min + 10:
        growth_pts = 20
    elif extraction.yoy_growth_pct >= thesis.growth_pct_min:
        growth_pts = 16
    else:
        growth_pts = 6

    geo_pts = 0
    if _contains_any(hq, ["TX", "IL", "CO", "TN", "AZ", "United States", "US", "USA"]):
        geo_pts = 10
    elif _contains_any(hq, ["Canada", "Toronto"]):
        geo_pts = 10
    elif hq:
        geo_pts = 2
    else:
        geo_pts = 4

    lev_pts = 0
    if extraction.net_debt_ebitda is None:
        lev_pts = 4
    elif extraction.net_debt_ebitda <= thesis.max_net_debt_ebitda - 1:
        lev_pts = 10
    elif extraction.net_debt_ebitda <= thesis.max_net_debt_ebitda:
        lev_pts = 7
    else:
        lev_pts = 0

    risk_pts = 10
    if extraction.missing_fields:
        risk_pts -= 6
    if extraction.recurring_revenue_pct is not None and extraction.recurring_revenue_pct < 50:
        risk_pts -= 6
    if any("leverage" in risk.lower() for risk in extraction.risks):
        risk_pts -= 2
    risk_pts = max(0, risk_pts)

    breakdown = ScoreBreakdown(
        sector=sector_pts,
        scale=scale_pts,
        growth=growth_pts,
        geography=geo_pts,
        leverage=lev_pts,
        risk=risk_pts,
    )
    total = sector_pts + scale_pts + growth_pts + geo_pts + lev_pts + risk_pts
    if total >= 75:
        recommendation = "advance"
        rationale = f"Fits {thesis.firm_name} software mandate; send to deal team."
    elif total >= 55:
        recommendation = "diligence"
        rationale = "Partial fit. Associate should review flags before a partner meeting."
    else:
        recommendation = "pass"
        rationale = "Outside mandate or incomplete package. Do not create a live DealCloud opportunity without override."

    if sector_pts == 0:
        recommendation = "pass"
        rationale = "Sector is outside the B2B software / data mandate. Pass unless a partner overrides."
    elif extraction.missing_fields:
        if recommendation == "advance":
            recommendation = "diligence"
        rationale = (
            "Missing CIM fields: "
            + ", ".join(extraction.missing_fields)
            + ". Do not invent numbers. Hold at teaser until the CIM lands."
        )
    elif extraction.net_debt_ebitda is not None and extraction.net_debt_ebitda > thesis.max_net_debt_ebitda:
        if recommendation == "advance":
            recommendation = "diligence"
        rationale = (
            f"Leverage {extraction.net_debt_ebitda}x is above the {thesis.max_net_debt_ebitda}x cap. "
            "Screen in DealCloud but do not auto-advance."
        )

    return ScoredDeal(
        deal_id=extraction.deal_id,
        company=extraction.company,
        score=total,
        recommendation=recommendation,
        rationale=rationale,
        breakdown=breakdown,
        extraction=extraction,
    )
