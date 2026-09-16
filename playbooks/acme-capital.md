# Inbound screening — deployment memo

**Tenant:** synthetic PE mandate (not a real fund)  
**Workflow:** CIM / teaser → cited extract → thesis score → HITL → DealCloud payload + SharePoint attach  
**Live:** https://argus-deal-intake.vercel.app  
**Notes:** https://argus-deal-intake.vercel.app/case-study

## What the firm asked for

Associates were pasting CIM numbers into DealCloud by hand. Partners wanted every inbound package scored against the software thesis before it became a live opportunity. They refused an unattended CRM write.

## What we scoped

1. Extract only fields that appear in the document. If EBITDA or leverage is missing, leave it blank. Never invent.
2. Score against a written mandate: North American B2B software / data, $25–100m revenue, ≥15% growth, ≤6x net debt / EBITDA.
3. Pause for an associate before `crm_upsert`. Reject means no Opportunity.
4. On approve, emit a DealCloud upsert payload and attach the source file to a SharePoint-style deal-room path. The payload is not a live tenant.

## What we refused to automate

- Partner override on a sector miss (Helios Solar EPC, Atlas Clinics, Pernix specialty pharma). The system can pass; it cannot quietly reclassify those books as software.
- Credit conclusions on teasers with no quality of earnings (Meridian). Score is capped at diligence until the CIM lands.
- LinkedIn account mapping and portfolio reporting on this slice. Those are week-1 questions at a real flagship, not this demo.

## Frozen eval (gold set)

`python3 -m argus.evals.deals_report`

- 6/6 packages
- Field accuracy 100%
- 0 hallucinated missing fields
- 5 fields correctly left blank (Meridian)
- Helios / Atlas: sector pass

Pernix is an EDGAR Guggenheim exhibit, **not** in the gold set. It is there to show under-extraction on a messy real book.

## 90-second script

1. Open the desk. Do not click. HarborPay is already interrupted. Leverage 6.8x vs ≤6x cap.
2. Helios Solar. Sector 0. Pass. Reject. No live record.
3. Meridian Logistics. EBITDA is `—`. Do not invent it.
4. Approve HarborPay. DealCloud payload gets `record_id`. SharePoint path attaches.
5. Optional: Pernix. Specialty pharma, `$91.1M of Net Sales` — blanks stay blank, recommendation is pass.

Do not narrate the stack. If asked how this lands on Metal: same contract, their field map, their HITL users.

## Week 1 at a real flagship

- Map DealCloud / Salesforce fields and which roles can approve a write.
- Freeze an eval on their last 20 CIMs, not this corpus.
- Ask who owns the account in CRM versus the CIM cover (LinkedIn mapping).
- Do not start with portfolio reporting.

## Field insight worth feeding the product

HITL is not a checkbox. Associates will only trust intake if (a) every number has a page citation, (b) missing fields stay missing, and (c) a sector miss cannot become a live DealCloud record without a human.
