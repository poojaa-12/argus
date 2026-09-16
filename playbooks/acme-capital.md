# Acme Capital deployment memo

**Account:** Acme Capital (synthetic flagship PE firm)  
**Workflow:** CIM / teaser intake → thesis score → human approval → DealCloud + SharePoint  
**Runtime:** Argus graph with HITL interrupts on destructive CRM writes  
**Live:** https://argus-deal-intake.vercel.app  
**Case study:** https://argus-deal-intake.vercel.app/case-study  
**Owner analog:** Forward Deployed Engineer, last mile

## What the firm asked for

Associates were pasting CIM numbers into DealCloud by hand. Partners wanted every inbound package scored against the software thesis before it became a live opportunity. They also refused to let a model write to CRM unattended.

## What we scoped

1. Extract only fields that appear in the document. If EBITDA or leverage is missing, leave it blank. Never invent.
2. Score against a written mandate: North American B2B software / data, $25–100m revenue, ≥15% growth, ≤6x net debt / EBITDA.
3. Pause for an associate before `crm_upsert`. Reject means the row stays out of DealCloud.
4. On approve, upsert the opportunity and attach the source file to a SharePoint-style deal room path.

## What we refused to automate

- Partner override on a sector miss (Helios Solar EPC, Atlas Clinics). The system can pass; it cannot quietly reclassify healthcare or project businesses as software.
- Credit conclusions on teasers with no quality of earnings (Meridian). Score is capped at diligence until the CIM lands.

## Repeatable rollout

| Step | Artifact |
| --- | --- |
| Thesis interview | `argus/deals/corpus.py` `ACME_THESIS` |
| Package corpus | six synthetic CIMs/teasers with gold labels |
| Extract / score / write | `cim_extract` → `thesis_score` → HITL → `crm_upsert` |
| Eval gate | `python3 -m argus.evals.deals_report` |
| Associate UI | `http://127.0.0.1:8080/ui/deals.html` |

## Demo script (90 seconds)

1. Open Deal Intake. Thesis chips should match the mandate.
2. Intake **Northwind Analytics**. Score should clear 75. UI pauses on HITL.
3. Approve. Pipeline card moves to Diligence; SharePoint path is filled.
4. Intake **Helios Solar**. Recommendation is pass. Reject the write.
5. Intake **Meridian Logistics**. EBITDA is blank on purpose. Do not invent it.
6. Upload your own `.pdf` / `.txt` CIM. Missing fields stay blank; CRM write still waits for HITL.

## Field insight worth feeding the product

HITL is not a checkbox. Associates will only trust intake if (a) every number has a page citation, (b) missing fields stay missing, and (c) a sector miss cannot become a live DealCloud record without a human.
