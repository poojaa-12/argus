# Argus — sample workspace (Acme Capital)

**Workspace:** synthetic PE mandate (not a real fund)
**Workflow:** upload → extract → score → review evidence → approve → write downstream
**Live:** https://argus-deal-intake.vercel.app
**Product:** https://argus-deal-intake.vercel.app/case-study

## Contract

1. Extract only fields that appear in the document. If EBITDA or leverage is missing, leave it blank.
2. Score against a written mandate: North American B2B software / data, $25–100m revenue, ≥15% growth, ≤6x net debt / EBITDA.
3. Pause before any CRM write. Reject means no opportunity.
4. On approve, emit a CRM payload and attach the source document. The payload is not a live tenant write.

## Frozen eval (gold set)

- 6/6 packages
- 0 invented critical fields
- Meridian: missing fields left blank
- Helios / Atlas: sector pass

Reliability evals on the operator runtime: `39/50 → 46/50` with retries, `12/20 → 18/20` under injected failure.

## Sixty seconds

1. HarborPay opens interrupted. Leverage 6.8x vs ≤6x.
2. Helios. Sector 0. Pass. Reject write.
3. Meridian. EBITDA is `—`. Not on the page.
4. Approve HarborPay. CRM payload gets `record_id`. Source document attaches.
