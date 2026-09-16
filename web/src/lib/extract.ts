import { getDeal } from "./corpus";
import type { Citation, DealExtraction } from "./types";

const MONEY = String.raw`\$([0-9]+(?:\.[0-9]+)?)\s*million`;
const PCT = String.raw`([0-9]+(?:\.[0-9]+)?)%`;
const MULT = String.raw`([0-9]+(?:\.[0-9]+)?)x`;
const PAGE = /\[p\.(\d+)\]/i;

function search(pattern: string, text: string): RegExpMatchArray | null {
  return text.match(new RegExp(pattern, "im"));
}

function asFloat(match: RegExpMatchArray | null, group = 1): number | null {
  if (!match?.[group]) return null;
  return Number.parseFloat(match[group]);
}

function asInt(match: RegExpMatchArray | null, group = 1): number | null {
  if (!match?.[group]) return null;
  return Number.parseInt(match[group].replace(/,/g, ""), 10);
}

function field(label: string, text: string): string | null {
  const match =
    search(`^${label}:\\s*(.+)$`, text) || search(`${label}:\\s*(.+)$`, text);
  if (!match?.[1]) return null;
  const value = match[1].replace(PAGE, "").trim();
  return value || null;
}

function lineCitation(text: string, name: string, needle: string): Citation | null {
  for (const raw of text.split("\n")) {
    if (!raw.toLowerCase().includes(needle.toLowerCase())) continue;
    const pageMatch = raw.match(PAGE);
    return {
      field: name,
      quote: raw.replace(/\s+/g, " ").trim().slice(0, 180),
      page: pageMatch ? Number.parseInt(pageMatch[1], 10) : 0,
    };
  }
  return null;
}

export function extractCim(dealId: string): DealExtraction {
  const deal = getDeal(dealId);
  const text = deal.text;
  const revenue = asFloat(search(`Revenue:\\s*${MONEY}`, text));
  const growth = asFloat(search(`YoY growth:\\s*${PCT}`, text));
  const ebitda = asFloat(search(`Adj\\. EBITDA:\\s*${MONEY}`, text));
  const margin = asFloat(search(`EBITDA margin:\\s*${PCT}`, text));
  const leverage = asFloat(search(`Net debt / EBITDA:\\s*${MULT}`, text));
  const recurring = asFloat(search(`Recurring revenue:\\s*${PCT}`, text));
  const employees = asInt(search(String.raw`Employees:\s*([0-9,]+)`, text));
  const sector = field("Sector", text);
  const hq = field("HQ", text);

  const risks: string[] = [];
  let capture = false;
  for (const line of text.split("\n")) {
    if (line.trim().toLowerCase() === "risks") {
      capture = true;
      continue;
    }
    if (!capture) continue;
    const cleaned = line.replace(/^[-*]\s*/, "").replace(PAGE, "").trim();
    if (!cleaned) {
      if (risks.length) break;
      continue;
    }
    risks.push(cleaned);
  }

  const mapping: Record<string, number | null> = {
    revenue_m: revenue,
    yoy_growth_pct: growth,
    ebitda_m: ebitda,
    ebitda_margin_pct: margin,
    net_debt_ebitda: leverage,
    recurring_revenue_pct: recurring,
  };
  const missing = Object.entries(mapping)
    .filter(([, value]) => value === null)
    .map(([name]) => name);

  const citations: Citation[] = [];
  const citePairs: Array<[string, string]> = [
    ["revenue_m", "Revenue:"],
    ["yoy_growth_pct", "YoY growth:"],
    ["ebitda_m", "Adj. EBITDA:"],
    ["net_debt_ebitda", "Net debt / EBITDA:"],
    ["sector", "Sector:"],
    ["headquarters", "HQ:"],
    ["recurring_revenue_pct", "Recurring revenue:"],
  ];
  for (const [name, needle] of citePairs) {
    if (name in mapping && mapping[name] === null) continue;
    const cited = lineCitation(text, name, needle);
    if (cited) citations.push(cited);
  }

  const firstBody =
    text
      .split("\n")
      .map((line) => line.trim())
      .find((line) => line.length > 40 && !line.startsWith("Financials")) ??
    `${deal.company} ${deal.document_type}`;

  return {
    deal_id: deal.id,
    company: deal.company,
    document_type: deal.document_type,
    sector,
    headquarters: hq,
    revenue_m: revenue,
    yoy_growth_pct: growth,
    ebitda_m: ebitda,
    ebitda_margin_pct: margin,
    net_debt_ebitda: leverage,
    recurring_revenue_pct: recurring,
    employees,
    summary: firstBody.slice(0, 240),
    risks,
    citations,
    missing_fields: missing,
  };
}
