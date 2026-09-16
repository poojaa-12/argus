import { ACME_THESIS, getDeal, listDeals } from "./corpus";
import { extractCim, extractFromText, inferCompany, inferDocumentType } from "./extract";
import { scoreDeal } from "./score";
import type {
  AuditEvent,
  DealCloudRecord,
  DealRecord,
  HitlGate,
  InboxDeal,
  IntakePackage,
  Opportunity,
  ScoredDeal,
  SharePointItem,
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
  gold: "gold 6/6 · 0 invented blanks",
  detail: "Helios sector pass · Meridian held",
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
    sharepoint_path: sharepointPath(scored.company, filename),
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
    tool_name: "crm_upsert",
    destructive: true,
    reason: `interrupt_before hitl_gate — ${deal.company} will not be written to DealCloud until an associate approves.`,
  };
  return {
    deal,
    scored,
    opportunity,
    hitl,
    trace: buildTrace(deal, scored, opportunity),
    dealcloud: buildDealCloud(scored, opportunity, deal),
    sharepoint: buildSharePoint(opportunity),
    audit: buildAudit(deal, scored, opportunity),
  };
}

function sharepointPath(company: string, filename: string): string {
  const folder = company.replace(/[^\w]+/g, " ").trim();
  return `/sites/AcmeCapital/DealRoom/${folder}/${filename}`;
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
      detail: "cim_extract → thesis_score → crm_upsert",
    },
    {
      id: "cim_extract",
      label: "cim_extract",
      status: "done",
      tool: "cim_extract",
      detail: missing
        ? `${deal.document_type} parsed · ${missing} field(s) left blank`
        : `${deal.document_type} parsed · all scored fields present`,
    },
    {
      id: "thesis_score",
      label: "thesis_score",
      status: "done",
      tool: "thesis_score",
      detail: `${scored.score}/100 ${scored.recommendation}`,
    },
    {
      id: "operator",
      label: "operator",
      status: pending ? "interrupted" : "done",
      detail: pending ? "pending_action: crm_upsert (destructive)" : written ? "write authorized" : "write denied",
    },
    {
      id: "hitl_gate",
      label: "hitl_gate",
      status: pending ? "interrupted" : "done",
      tool: "crm_upsert",
      detail: pending ? "waiting on associate" : written ? "approved" : "rejected",
    },
    {
      id: "crm_upsert",
      label: "crm_upsert",
      status: written ? "done" : rejected ? "blocked" : "waiting",
      tool: "crm_upsert",
      detail: written
        ? `Opportunity ${opportunity.opportunity_id} · ${opportunity.stage}`
        : rejected
          ? "no live record"
          : "blocked until HITL",
    },
    {
      id: "sharepoint_attach",
      label: "sharepoint_attach",
      status: written ? "done" : rejected ? "blocked" : "waiting",
      tool: "sharepoint_attach",
      detail: written ? "deal-room file linked" : "not attached",
    },
    {
      id: "synthesize",
      label: "synthesize",
      status: pending ? "waiting" : "done",
      detail: pending ? "paused" : scored.rationale,
    },
  ];
}

function buildDealCloud(scored: ScoredDeal, opportunity: Opportunity, deal: DealRecord): DealCloudRecord {
  const ex = scored.extraction;
  const fields = [
    { api_name: "AccountName", label: "Account", value: scored.company, source: "extract.company" },
    { api_name: "OpportunityName", label: "Name", value: `${scored.company} ${deal.document_type}`, source: "filename" },
    { api_name: "Stage", label: "Stage", value: opportunity.stage, source: "score.recommendation" },
    { api_name: "Sector__c", label: "Sector", value: ex.sector, source: "extract.sector" },
    { api_name: "HQ__c", label: "HQ", value: ex.headquarters, source: "extract.headquarters" },
    { api_name: "Revenue_mm__c", label: "Revenue $m", value: ex.revenue_m, source: "extract.revenue_m" },
    { api_name: "Growth_pct__c", label: "YoY %", value: ex.yoy_growth_pct, source: "extract.yoy_growth_pct" },
    { api_name: "EBITDA_mm__c", label: "EBITDA $m", value: ex.ebitda_m, source: "extract.ebitda_m" },
    { api_name: "ND_EBITDA__c", label: "ND/EBITDA", value: ex.net_debt_ebitda, source: "extract.net_debt_ebitda" },
    { api_name: "ThesisScore__c", label: "Score", value: scored.score, source: "thesis_score" },
    { api_name: "Recommendation__c", label: "Rec", value: scored.recommendation, source: "thesis_score" },
    { api_name: "SourceDocument__c", label: "Source", value: deal.filename, source: "inbox" },
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
    system: "DealCloud",
    object: "Opportunity",
    record_id: opportunity.status === "written" ? opportunity.opportunity_id : null,
    write_status: opportunity.status,
    note: "payload · not a live tenant",
    fields,
    payload,
  };
}

function buildSharePoint(opportunity: Opportunity): SharePointItem {
  return {
    site: "AcmeCapital",
    library: "DealRoom",
    path: opportunity.sharepoint_path || "",
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
      actor: "cim_extract",
      action: "extract",
      detail: scored.extraction.missing_fields.length
        ? `Blank: ${scored.extraction.missing_fields.join(", ")}`
        : "No blank scored fields",
    },
    {
      seq: "03",
      actor: "thesis_score",
      action: "score",
      detail: `${scored.score}/100 ${scored.recommendation} · sector ${scored.breakdown.sector} scale ${scored.breakdown.scale} growth ${scored.breakdown.growth}`,
    },
    {
      seq: "04",
      actor: "hitl_gate",
      action: "interrupt",
      detail: "crm_upsert is destructive · associate required",
    },
  ];
  if (opportunity.status === "written") {
    events.push({
      seq: "05",
      actor: "associate",
      action: "approve",
      detail: `DealCloud ${opportunity.opportunity_id} · ${opportunity.stage}`,
    });
    events.push({
      seq: "06",
      actor: "sharepoint_attach",
      action: "attach",
      detail: opportunity.sharepoint_path || "",
    });
  } else if (opportunity.status === "rejected") {
    events.push({
      seq: "05",
      actor: "associate",
      action: "reject",
      detail: "No Opportunity created · SharePoint unchanged",
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
