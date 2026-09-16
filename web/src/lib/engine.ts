import { getDeal } from "./corpus";
import { extractCim, extractFromText, inferCompany, inferDocumentType } from "./extract";
import { scoreDeal } from "./score";
import type { DealRecord, Opportunity, ScoredDeal } from "./types";

const STAGES = {
  advance: "Diligence",
  diligence: "Screened",
  pass: "Passed",
} as const;

export function pendingOpportunity(scored: ScoredDeal, filename: string): Opportunity {
  return {
    opportunity_id: `opp-${scored.deal_id}`,
    account_name: scored.company,
    deal_id: scored.deal_id,
    stage: "New",
    score: scored.score,
    recommendation: scored.recommendation,
    source_document: filename,
    sharepoint_path: `/sites/dealroom/${scored.deal_id}/${filename}`,
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

function packageIntake(deal: DealRecord, extraction: ReturnType<typeof extractCim>) {
  const scored = scoreDeal(extraction);
  return {
    deal,
    scored,
    opportunity: pendingOpportunity(scored, deal.filename),
    hitl: {
      tool_name: "crm_upsert",
      destructive: true,
      reason: `Associate approval required before writing ${deal.company} to DealCloud / SharePoint.`,
    },
  };
}

export function resumeDeal(scored: ScoredDeal, feedback: string, filename: string) {
  const rejected = ["reject", "deny", "no"].includes(feedback.trim().toLowerCase());
  if (rejected) {
    return {
      status: "rejected" as const,
      opportunity: {
        ...pendingOpportunity(scored, filename),
        status: "rejected" as const,
      },
    };
  }
  return {
    status: "completed" as const,
    opportunity: writtenOpportunity(scored, filename),
  };
}
