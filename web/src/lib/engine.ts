import { ACME_THESIS, getDeal, listDeals } from "./corpus";
import { extractCim, extractFromText, inferCompany, inferDocumentType } from "./extract";
import { scoreDeal } from "./score";
import type {
  AuditEvent,
  CrmRecord,
  DealRecord,
  DocumentSource,
  HitlGate,
  InboxDeal,
  IntakePackage,
  Opportunity,
  ScoredDeal,
  TraceNode,
  EvalStrip,
} from "./types";

const STAGES = {
  advance: "Diligence",
  diligence: "Screened",
  pass: "Passed",
} as const;

export const DEFAULT_OPEN_ID = "harborpay";

export const EVAL_STRIP: EvalStrip = {
  gold: "Gold set 6/6 · 0 invented critical fields",
  detail: "Retries 39/50 → 46/50 · injected failure 12/20 → 18/20",
};

export function pendingOpportunity(scored: ScoredDeal, filename: string): Opportunity {
  return {
    opportunity_id: `opp-${scored.deal_id}`,
    account_name: scored.company,
    deal_id: scored.deal_id,
    stage: "New",
    score: scored.score,
    recommendation: scored.recommendation,
    source_document: filename,
    document_path: documentPath(scored.company, filename),
    extraction: scored.extraction,
    status: "pending_approval",
  };
}

export function writtenOpportunity(scored: ScoredDeal, filename: string): Opportunity {
  return {
    ...pendingOpportunity(scored, filename),
    stage: STAGES[scored.recommendation],
    status: "written",
  };
}

export function intakeDeal(dealId: string) {
  const deal = getDeal(dealId);
  return packageIntake(deal, extractCim(dealId));
}

export function intakeUploaded(text: string, filename: string, dealId: string) {
  const company = inferCompany(text, filename);
  const documentType = inferDocumentType(filename, text);
  const deal: DealRecord = {
    id: dealId,
    company,
    document_type: documentType,
    filename,
    text,
  };
  const extraction = extractFromText(text, {
    dealId,
    company,
    documentType,
  });
  return packageIntake(deal, extraction);
}

function packageIntake(deal: DealRecord, extraction: ReturnType<typeof extractCim>): IntakePackage {
  const scored = scoreDeal(extraction);
  return decorateIntake(deal, scored, pendingOpportunity(scored, deal.filename));
}

export function resumeDeal(scored: ScoredDeal, feedback: string, filename: string, deal?: DealRecord) {
  const rejected = ["reject", "deny", "no"].includes(feedback.trim().toLowerCase());
  const opportunity = rejected
    ? { ...pendingOpportunity(scored, filename), status: "rejected" as const }
    : writtenOpportunity(scored, filename);
  const record: DealRecord = deal ?? {
    id: scored.deal_id,
    company: scored.company,
    document_type: scored.extraction.document_type,
    filename,
    text: "",
  };
  return {
    status: rejected ? ("rejected" as const) : ("completed" as const),
    ...decorateIntake(record, scored, opportunity),
  };
}

export function decorateIntake(deal: DealRecord, scored: ScoredDeal, opportunity: Opportunity): IntakePackage {
  const hitl: HitlGate = {
    tool_name: "crm_write",
    destructive: true,
    reason: `${deal.company} will not be written to the CRM until a reviewer approves.`,
  };
  return {
    deal,
    scored,
    opportunity,
    hitl,
    trace: buildTrace(deal, scored, opportunity),
    crm: buildCrm(scored, opportunity, deal),
    documents: buildDocuments(opportunity),
    audit: buildAudit(deal, scored, opportunity),
  };
}

function documentPath(company: string, filename: string): string {
  const folder = company.replace(/[^\w]+/g, " ").trim();
  return `/documents/${folder}/${filename}`;
}

function buildTrace(deal: DealRecord, scored: ScoredDeal, opportunity: Opportunity): TraceNode[] {
  const pending = opportunity.status === "pending_approval";
  const written = opportunity.status === "written";
  const rejected = opportunity.status === "rejected";
  const missing = scored.extraction.missing_fields.length;
  return [
    {
      id: "planner",
      label: "planner",
      status: "done",
      detail: "extract → score → review → approve → write",
    },
    {
      id: "extract",
      label: "extract",
      status: "done",
      tool: "extract",
      detail: missing
        ? `${deal.document_type} parsed · ${missing} field(s) left blank`
        : `${deal.document_type} parsed · all scored fields present`,
    },
    {
      id: "score",
      label: "score",
      status: "done",
      tool: "score",
      detail: `${scored.score}/100 ${scored.recommendation}`,
    },
    {
      id: "operator",
      label: "operator",
      status: pending ? "interrupted" : "done",
      detail: pending ? "pending action: CRM write (destructive)" : written ? "write authorized" : "write denied",
    },
    {
      id: "approve",
      label: "approve",
      status: pending ? "interrupted" : "done",
      tool: "crm_write",
      detail: pending ? "waiting on reviewer" : written ? "approved" : "rejected",
    },
    {
      id: "crm_write",
      label: "crm_write",
      status: written ? "done" : rejected ? "blocked" : "waiting",
      tool: "crm_write",
      detail: written
        ? `Opportunity ${opportunity.opportunity_id} · ${opportunity.stage}`
        : rejected
          ? "no live record"
          : "blocked until approval",
    },
    {
      id: "attach_source",
      label: "attach_source",
      status: written ? "done" : rejected ? "blocked" : "waiting",
      tool: "attach_source",
      detail: written ? "source document linked" : "not attached",
    },
    {
      id: "synthesize",
      label: "synthesize",
      status: pending ? "waiting" : "done",
      detail: pending ? "paused" : scored.rationale,
    },
  ];
}

function buildCrm(scored: ScoredDeal, opportunity: Opportunity, deal: DealRecord): CrmRecord {
  const ex = scored.extraction;
  const fields = [
    { api_name: "account_name", label: "Account", value: scored.company, source: "extract.company" },
    { api_name: "opportunity_name", label: "Name", value: `${scored.company} ${deal.document_type}`, source: "filename" },
    { api_name: "stage", label: "Stage", value: opportunity.stage, source: "score.recommendation" },
    { api_name: "sector", label: "Sector", value: ex.sector, source: "extract.sector" },
    { api_name: "headquarters", label: "HQ", value: ex.headquarters, source: "extract.headquarters" },
    { api_name: "revenue_m", label: "Revenue $m", value: ex.revenue_m, source: "extract.revenue_m" },
    { api_name: "growth_pct", label: "YoY %", value: ex.yoy_growth_pct, source: "extract.yoy_growth_pct" },
    { api_name: "ebitda_m", label: "EBITDA $m", value: ex.ebitda_m, source: "extract.ebitda_m" },
    { api_name: "nd_ebitda", label: "ND/EBITDA", value: ex.net_debt_ebitda, source: "extract.net_debt_ebitda" },
    { api_name: "thesis_score", label: "Score", value: scored.score, source: "score" },
    { api_name: "recommendation", label: "Rec", value: scored.recommendation, source: "score" },
    { api_name: "source_document", label: "Source", value: deal.filename, source: "inbox" },
  ];
  const payload: Record<string, string | number | null> = {
    object: "Opportunity",
    operation: opportunity.status === "written" ? "upsert" : "pending",
    record_id: opportunity.status === "written" ? opportunity.opportunity_id : null,
  };
  for (const field of fields) {
    payload[field.api_name] = field.value;
  }
  return {
    system: "CRM",
    object: "Opportunity",
    record_id: opportunity.status === "written" ? opportunity.opportunity_id : null,
    write_status: opportunity.status,
    note: "payload · not a live CRM write",
    fields,
    payload,
  };
}

function buildDocuments(opportunity: Opportunity): DocumentSource {
  return {
    workspace: "Acme Capital",
    collection: "Deal files",
    path: opportunity.document_path || "",
    attached: opportunity.status === "written",
  };
}

function buildAudit(deal: DealRecord, scored: ScoredDeal, opportunity: Opportunity): AuditEvent[] {
  const events: AuditEvent[] = [
    {
      seq: "01",
      actor: "planner",
      action: "plan",
      detail: `Intake ${deal.company} ${deal.document_type}`,
    },
    {
      seq: "02",
      actor: "extract",
      action: "extract",
      detail: scored.extraction.missing_fields.length
        ? `Blank: ${scored.extraction.missing_fields.join(", ")}`
        : "No blank scored fields",
    },
    {
      seq: "03",
      actor: "score",
      action: "score",
      detail: `${scored.score}/100 ${scored.recommendation} · sector ${scored.breakdown.sector} scale ${scored.breakdown.scale} growth ${scored.breakdown.growth}`,
    },
    {
      seq: "04",
      actor: "approve",
      action: "interrupt",
      detail: "CRM write is destructive · reviewer required",
    },
  ];
  if (opportunity.status === "written") {
    events.push({
      seq: "05",
      actor: "reviewer",
      action: "approve",
      detail: `CRM ${opportunity.opportunity_id} · ${opportunity.stage}`,
    });
    events.push({
      seq: "06",
      actor: "attach_source",
      action: "attach",
      detail: opportunity.document_path || "",
    });
  } else if (opportunity.status === "rejected") {
    events.push({
      seq: "05",
      actor: "reviewer",
      action: "reject",
      detail: "No opportunity created · document source unchanged",
    });
  }
  return events;
}

export function buildCatalog(): {
  thesis: typeof ACME_THESIS;
  openId: string;
  open: IntakePackage;
  deals: InboxDeal[];
  eval: EvalStrip;
} {
  return {
    thesis: ACME_THESIS,
    openId: DEFAULT_OPEN_ID,
    open: intakeDeal(DEFAULT_OPEN_ID),
    eval: EVAL_STRIP,
    deals: (() => {
      const ranked = [
        ...listDeals().filter((deal) => deal.id === DEFAULT_OPEN_ID),
        ...listDeals().filter((deal) => deal.id !== DEFAULT_OPEN_ID && deal.source !== "edgar"),
        ...listDeals().filter((deal) => deal.source === "edgar"),
      ];
      return ranked.map((deal) => {
        const scored = scoreDeal(extractCim(deal.id));
        return {
          id: deal.id,
          company: deal.company,
          document_type: deal.document_type,
          filename: deal.filename,
          score: scored.score,
          recommendation: scored.recommendation,
          missing_fields: scored.extraction.missing_fields.length,
          source: deal.source ?? "gold",
        };
      });
    })(),
  };
}
