import { ACME_THESIS } from "./corpus";
import type { DealExtraction, FirmThesis, Recommendation, ScoreBreakdown, ScoredDeal } from "./types";

function containsAny(haystack: string, needles: string[]): boolean {
  const lower = haystack.toLowerCase();
  return needles.some((needle) => lower.includes(needle.toLowerCase()));
}

export function scoreDeal(extraction: DealExtraction, thesis: FirmThesis = ACME_THESIS): ScoredDeal {
  const sectorText = extraction.sector ?? "";
  const hq = extraction.headquarters ?? "";

  let sectorPts = 0;
  if (containsAny(sectorText, ["project-based", "EPC", "healthcare", "clinic", "pharma", "pharmaceutical", "biotech", ...thesis.avoid])) {
    sectorPts = 0;
  } else if (containsAny(sectorText, ["software", "saas", "data", "payments"])) {
    sectorPts = 30;
  } else if (containsAny(sectorText, thesis.sectors)) {
    sectorPts = 24;
  } else {
    sectorPts = 8;
  }

  let scalePts = 0;
  if (extraction.revenue_m === null) scalePts = 8;
  else if (extraction.revenue_m >= thesis.revenue_m_min && extraction.revenue_m <= thesis.revenue_m_max) scalePts = 20;
  else if (extraction.revenue_m < thesis.revenue_m_min) scalePts = 10;
  else scalePts = 12;

  let growthPts = 0;
  if (extraction.yoy_growth_pct === null) growthPts = 6;
  else if (extraction.yoy_growth_pct >= thesis.growth_pct_min + 10) growthPts = 20;
  else if (extraction.yoy_growth_pct >= thesis.growth_pct_min) growthPts = 16;
  else growthPts = 6;

  let geoPts = 0;
  if (
    containsAny(hq, ["TX", "IL", "CO", "TN", "AZ", "MA", "NY", "CA", "WA", "FL", "United States", "US", "USA"]) ||
    /,\s*[A-Z]{2}\b/.test(hq)
  ) {
    geoPts = 10;
  } else if (containsAny(hq, ["Canada", "Toronto"])) {
    geoPts = 10;
  } else if (hq) {
    geoPts = 2;
  } else {
    geoPts = 4;
  }

  let levPts = 0;
  if (extraction.net_debt_ebitda === null) levPts = 4;
  else if (extraction.net_debt_ebitda <= thesis.max_net_debt_ebitda - 1) levPts = 10;
  else if (extraction.net_debt_ebitda <= thesis.max_net_debt_ebitda) levPts = 7;
  else levPts = 0;

  let riskPts = 10;
  if (extraction.missing_fields.length) riskPts -= 6;
  if (extraction.recurring_revenue_pct !== null && extraction.recurring_revenue_pct < 50) riskPts -= 6;
  if (extraction.risks.some((risk) => risk.toLowerCase().includes("leverage"))) riskPts -= 2;
  riskPts = Math.max(0, riskPts);

  const breakdown: ScoreBreakdown = {
    sector: sectorPts,
    scale: scalePts,
    growth: growthPts,
    geography: geoPts,
    leverage: levPts,
    risk: riskPts,
  };
  const total = sectorPts + scalePts + growthPts + geoPts + levPts + riskPts;

  let recommendation: Recommendation;
  let rationale: string;
  if (total >= 75) {
    recommendation = "advance";
    rationale = `Fits ${thesis.firm_name} software mandate; send to deal team.`;
  } else if (total >= 55) {
    recommendation = "diligence";
    rationale = "Partial fit. Associate should review flags before a partner meeting.";
  } else {
    recommendation = "pass";
    rationale = "Outside mandate or incomplete package. Do not create a live DealCloud opportunity without override.";
  }

  if (sectorPts === 0) {
    recommendation = "pass";
    rationale = "Sector is outside the B2B software / data mandate. Pass unless a partner overrides.";
  } else if (extraction.missing_fields.length) {
    if (recommendation === "advance") recommendation = "diligence";
    rationale =
      "Missing CIM fields: " +
      extraction.missing_fields.join(", ") +
      ". Do not invent numbers. Hold at teaser until the CIM lands.";
  } else if (extraction.net_debt_ebitda !== null && extraction.net_debt_ebitda > thesis.max_net_debt_ebitda) {
    if (recommendation === "advance") recommendation = "diligence";
    rationale = `Leverage ${extraction.net_debt_ebitda}x is above the ${thesis.max_net_debt_ebitda}x cap. Screen in DealCloud but do not auto-advance.`;
  }

  return {
    deal_id: extraction.deal_id,
    company: extraction.company,
    score: total,
    recommendation,
    rationale,
    breakdown,
    extraction,
  };
}
