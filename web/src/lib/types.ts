export type DocumentType = "CIM" | "teaser";
export type Recommendation = "advance" | "diligence" | "pass";

export type Citation = {
  field: string;
  quote: string;
  page: number;
};

export type DealExtraction = {
  deal_id: string;
  company: string;
  document_type: DocumentType;
  sector: string | null;
  headquarters: string | null;
  revenue_m: number | null;
  yoy_growth_pct: number | null;
  ebitda_m: number | null;
  ebitda_margin_pct: number | null;
  net_debt_ebitda: number | null;
  recurring_revenue_pct: number | null;
  employees: number | null;
  summary: string;
  risks: string[];
  citations: Citation[];
  missing_fields: string[];
};

export type ScoreBreakdown = {
  sector: number;
  scale: number;
  growth: number;
  geography: number;
  leverage: number;
  risk: number;
};

export type ScoredDeal = {
  deal_id: string;
  company: string;
  score: number;
  recommendation: Recommendation;
  rationale: string;
  breakdown: ScoreBreakdown;
  extraction: DealExtraction;
};

export type FirmThesis = {
  firm_id: string;
  firm_name: string;
  mandate: string;
  sectors: string[];
  geographies: string[];
  revenue_m_min: number;
  revenue_m_max: number;
  growth_pct_min: number;
  max_net_debt_ebitda: number;
  avoid: string[];
};

export type DealRecord = {
  id: string;
  company: string;
  document_type: DocumentType;
  filename: string;
  text: string;
};

export type Opportunity = {
  opportunity_id: string;
  account_name: string;
  deal_id: string;
  stage: "New" | "Screened" | "Diligence" | "Passed";
  score: number | null;
  recommendation: Recommendation | null;
  source_document: string | null;
  sharepoint_path: string | null;
  extraction: DealExtraction | null;
  status: "pending_approval" | "written" | "rejected";
};
