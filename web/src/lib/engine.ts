import { getDeal } from "./corpus";
import { extractCim } from "./extract";
import { scoreDeal } from "./score";
import type { Opportunity, ScoredDeal } from "./types";

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
  const extraction = extractCim(dealId);
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

export function resumeDeal(scored: ScoredDeal, feedback: string) {
  const deal = getDeal(scored.deal_id);
  const rejected = ["reject", "deny", "no"].includes(feedback.trim().toLowerCase());
  if (rejected) {
    return {
      status: "rejected" as const,
      opportunity: {
        ...pendingOpportunity(scored, deal.filename),
        status: "rejected" as const,
      },
    };
  }
  return {
    status: "completed" as const,
    opportunity: writtenOpportunity(scored, deal.filename),
  };
}
