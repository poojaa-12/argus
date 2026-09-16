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
  source?: "gold" | "edgar";
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

export type TraceStatus = "done" | "interrupted" | "waiting" | "blocked";

export type TraceNode = {
  id: string;
  label: string;
  status: TraceStatus;
  tool?: string;
  detail: string;
};

export type DealCloudField = {
  api_name: string;
  label: string;
  value: string | number | null;
  source: string;
};

export type DealCloudRecord = {
  system: "DealCloud";
  object: "Opportunity";
  record_id: string | null;
  write_status: Opportunity["status"];
  note: string;
  fields: DealCloudField[];
  payload: Record<string, string | number | null>;
};

export type SharePointItem = {
  site: string;
  library: string;
  path: string;
  attached: boolean;
};

export type AuditEvent = {
  seq: string;
  actor: string;
  action: string;
  detail: string;
};

export type HitlGate = {
  tool_name: string;
  destructive: boolean;
  reason: string;
};

export type IntakePackage = {
  deal: DealRecord;
  scored: ScoredDeal;
  opportunity: Opportunity;
  hitl: HitlGate;
  trace: TraceNode[];
  dealcloud: DealCloudRecord;
  sharepoint: SharePointItem;
  audit: AuditEvent[];
};

export type InboxDeal = Pick<DealRecord, "id" | "company" | "document_type" | "filename"> & {
  score: number;
  recommendation: Recommendation;
  missing_fields: number;
  source: "gold" | "edgar";
};

export type EvalStrip = {
  gold: string;
  detail: string;
};
