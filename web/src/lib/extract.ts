import { getDeal } from "./corpus";
import type { Citation, DealExtraction, DocumentType } from "./types";

const PAGE = /\[p\.(\d+)\]/i;

function search(pattern: string, text: string): RegExpMatchArray | null {
  return text.match(new RegExp(pattern, "im"));
}

function asInt(match: RegExpMatchArray | null, group = 1): number | null {
  if (!match?.[group]) return null;
  return Number.parseInt(match[group].replace(/,/g, ""), 10);
}

function firstMatch(text: string, patterns: string[]): RegExpMatchArray | null {
  for (const pattern of patterns) {
    const match = search(pattern, text);
    if (match?.[1]) return match;
  }
  return null;
}

function money(text: string, patterns: string[]): number | null {
  const match = firstMatch(text, patterns);
  if (!match?.[1]) return null;
  return Number.parseFloat(match[1].replace(/,/g, ""));
}

function pct(text: string, patterns: string[]): number | null {
  return money(text, patterns);
}

function field(label: string, text: string): string | null {
  const match =
    search(`^${label}:\\s*(.+)$`, text) || search(`${label}:\\s*(.+)$`, text);
  if (!match?.[1]) return null;
  const value = match[1].replace(PAGE, "").trim();
  return value || null;
}

function lineCitation(text: string, name: string, needle: string): Citation | null {
  for (const raw of text.split(/\n/)) {
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

function risksFrom(text: string): string[] {
  const risks: string[] = [];
  let capture = false;
  for (const line of text.split(/\n/)) {
    if (/^(key\s+)?risks\b/i.test(line.trim())) {
      capture = true;
      continue;
    }
    if (!capture) continue;
    const cleaned = line.replace(/^[-*]\s*/, "").replace(PAGE, "").trim();
    if (!cleaned) {
      if (risks.length) break;
      continue;
    }
    if (/^[A-Z][A-Za-z ]{0,24}$/.test(cleaned) && !cleaned.includes(" ")) break;
    risks.push(cleaned);
  }
  return risks;
}

export function inferCompany(text: string, filename: string): string {
  const labeled = field("Company", text);
  if (labeled) return labeled.split(/[(\n]/)[0].trim();
  const legal = search(
    String.raw`^([A-Z][A-Za-z0-9&.\- ]+),\s+(Inc\.?|LLC|Ltd\.?|Group)\s*$`,
    text,
  );
  if (legal?.[1]) return legal[1].trim();
  const heading = text
    .split(/\n/)
    .map((line) => line.trim())
    .find(
      (line) =>
        line.length > 3 &&
        line === line.toUpperCase() &&
        /[A-Z]/.test(line) &&
        !/confidential|memorandum|teaser|prepared/i.test(line),
    );
  if (heading) {
    return heading.replace(/,?\s+(INC\.|LLC|LTD\.?|GROUP)$/i, "").replace(/\./g, "").trim();
  }
  return filename.replace(/\.[^.]+$/, "").replace(/[_-]+/g, " ").trim() || "Uploaded company";
}

export function inferDocumentType(filename: string, text: string): DocumentType {
  const blob = `${filename} ${text.slice(0, 400)}`.toLowerCase();
  if (blob.includes("teaser") || blob.includes("one-pager") || blob.includes("one pager")) return "teaser";
  return "CIM";
}

export function extractFromText(
  text: string,
  meta: { dealId: string; company: string; documentType: DocumentType },
): DealExtraction {
  const revenue = money(text, [
    String.raw`Revenue:\s*\$([0-9]+(?:\.[0-9]+)?)\s*million`,
    String.raw`(?:(?:total|fy\d{2,4})\s+)*revenue(?:\s+was|\s+of|:)\s*\$([0-9,]+(?:\.[0-9]+)?)\s*(?:million|mm)\b`,
    String.raw`\$([0-9,]+(?:\.[0-9]+)?)\s*(?:million|mm)\s+(?:of |in )?(?:total )?revenue`,
  ]);
  const growth = pct(text, [
    String.raw`YoY growth:\s*([0-9]+(?:\.[0-9]+)?)%`,
    String.raw`up ([0-9]+(?:\.[0-9]+)?)%\s+year-over-year`,
    String.raw`(?:year-over-year|yoy)\s*(?:growth)?[:\s,]+(?:of\s+)?([0-9]+(?:\.[0-9]+)?)%`,
    String.raw`grew ([0-9]+(?:\.[0-9]+)?)%`,
  ]);
  const ebitda = money(text, [
    String.raw`Adj\. EBITDA:\s*\$([0-9]+(?:\.[0-9]+)?)\s*million`,
    String.raw`(?:adj(?:usted)?\.?\s+)?ebitda(?:\s+was|\s+of|:)\s*\$([0-9,]+(?:\.[0-9]+)?)\s*(?:million|mm)`,
  ]);
  const margin = pct(text, [
    String.raw`EBITDA margin:\s*([0-9]+(?:\.[0-9]+)?)%`,
    String.raw`ebitda margin(?:\s+of|:)\s*([0-9]+(?:\.[0-9]+)?)%`,
    String.raw`\$[0-9,]+(?:\.[0-9]+)?\s*million\s*\(([0-9]+(?:\.[0-9]+)?)%\s*margin\)`,
  ]);
  const leverage = money(text, [
    String.raw`Net debt / EBITDA:\s*([0-9]+(?:\.[0-9]+)?)x`,
    String.raw`net debt\s*/\s*ebitda[^\d]{0,24}([0-9]+(?:\.[0-9]+)?)x`,
    String.raw`leverage of ([0-9]+(?:\.[0-9]+)?)x`,
  ]);
  const recurring = pct(text, [
    String.raw`Recurring revenue:\s*([0-9]+(?:\.[0-9]+)?)%`,
    String.raw`recurring revenue[^\d%]{0,32}([0-9]+(?:\.[0-9]+)?)%`,
  ]);
  const employees = asInt(
    firstMatch(text, [String.raw`Employees:\s*([0-9,]+)`, String.raw`([0-9,]+)\s+employees`]),
  );

  const sector =
    field("Sector", text) ||
    (search(String.raw`is an?\s+([^\n.]{8,80}?)\s+company`, text)?.[1]?.trim() ?? null);
  const hq =
    field("HQ", text) ||
    field("Headquarters", text) ||
    (search(String.raw`based in\s+([A-Za-z .]+,\s*[A-Z]{2})\b`, text)?.[1]?.trim() ?? null);

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
    ["revenue_m", "Revenue"],
    ["yoy_growth_pct", "growth"],
    ["ebitda_m", "EBITDA"],
    ["net_debt_ebitda", "Net debt"],
    ["sector", "Sector"],
    ["headquarters", "HQ"],
    ["recurring_revenue_pct", "Recurring"],
  ];
  for (const [name, needle] of citePairs) {
    if (name in mapping && mapping[name] === null && name !== "sector" && name !== "headquarters") continue;
    const cited = lineCitation(text, name, needle);
    if (cited) citations.push(cited);
  }

  const firstBody =
    text
      .split(/\n/)
      .map((line) => line.trim())
      .find((line) => line.length > 40 && !line.toLowerCase().startsWith("financials")) ??
    `${meta.company} ${meta.documentType}`;

  return {
    deal_id: meta.dealId,
    company: meta.company,
    document_type: meta.documentType,
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
    risks: risksFrom(text),
    citations,
    missing_fields: missing,
  };
}

export function extractCim(dealId: string): DealExtraction {
  const deal = getDeal(dealId);
  return extractFromText(deal.text, {
    dealId: deal.id,
    company: deal.company,
    documentType: deal.document_type,
  });
}
