import type { Metadata } from "next";
import Link from "next/link";
import SiteNav from "@/components/SiteNav";

export const metadata: Metadata = {
  title: "Field memo · Inbound screening",
  description:
    "Scoping notes for a CIM-to-DealCloud last mile: what the firm asked, what we refused, frozen evals, week-1 at a real flagship.",
};

export default function CaseStudyPage() {
  return (
    <div className="min-h-full bg-[#0a0c10] text-zinc-200">
      <main className="mx-auto max-w-2xl px-4 py-8 sm:px-6">
        <p className="text-[10px] uppercase tracking-[0.16em] text-zinc-500">Field memo · synthetic tenant</p>
        <div className="mt-3">
          <SiteNav active="case-study" />
        </div>
        <h1 className="mt-5 text-2xl font-semibold tracking-tight">CIM intake that is allowed to stop</h1>
        <p className="mt-2 text-[12px] leading-5 text-zinc-500">
          Prototype built for Metal&apos;s CIM intake workflow — CIM parsing → thesis scoring → human-approved DealCloud
          write. Built by Sai Pooja Sabbani
          {" · "}
          <a className="text-zinc-300 hover:underline" href="https://linkedin.com/in/saipoojasabbani" target="_blank" rel="noreferrer">
            LinkedIn
          </a>
          {" · "}
          <a className="text-zinc-300 hover:underline" href="https://github.com/poojaa-12/argus" target="_blank" rel="noreferrer">
            GitHub
          </a>
        </p>
        <p className="mt-3 text-sm leading-6 text-zinc-400">
          Associates were pasting CIM numbers into DealCloud. Partners wanted every inbound package scored against a
          written software thesis before it became a live opportunity, and refused an unattended CRM write. This tenant
          freezes that contract. It is not a real fund. Rapid build to show the mechanism — fields missing from the page
          stay blank rather than guessed.
        </p>
        <p className="mt-2 font-mono text-[11px] text-zinc-500">
          <Link className="text-zinc-300 hover:underline" href="/">
            Desk
          </Link>
          {" · "}
          gold 6/6 · 0 invented blanks · Helios sector pass · Meridian held
        </p>

        <section className="mt-8 border-t border-[#2c3340] pt-4">
          <h2 className="text-[10px] font-semibold uppercase tracking-[0.14em] text-zinc-500">What we scoped</h2>
          <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm leading-6 text-zinc-400">
            <li>Extract only what is on the page. Missing EBITDA stays blank.</li>
            <li>Score a written mandate: NA B2B software/data, $25–100m, ≥15% growth, ≤6x ND/EBITDA.</li>
            <li>Interrupt before <span className="font-mono text-zinc-200">crm_upsert</span>. Reject means no record.</li>
            <li>On approve, emit a DealCloud Opportunity payload and attach SharePoint only then.</li>
          </ol>
        </section>

        <section className="mt-6 border-t border-[#2c3340] pt-4">
          <h2 className="text-[10px] font-semibold uppercase tracking-[0.14em] text-zinc-500">What we refused</h2>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-sm leading-6 text-zinc-400">
            <li>Quietly reclassifying Helios (solar EPC) or Pernix (specialty pharma) as software.</li>
            <li>Inventing Meridian EBITDA / leverage from a teaser.</li>
            <li>A live DealCloud tenant, LinkedIn mapping, or portfolio reporting on this slice.</li>
            <li>An LLM on the public desk. A model can fill this schema later; it cannot change the gates.</li>
          </ul>
        </section>

        <section className="mt-6 border-t border-[#2c3340] pt-4">
          <h2 className="text-[10px] font-semibold uppercase tracking-[0.14em] text-zinc-500">90 seconds</h2>
          <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm leading-6 text-zinc-400">
            <li>Open the desk. HarborPay is already interrupted. 6.8x vs ≤6x. Do not approve yet.</li>
            <li>Helios. Sector 0. Pass. Reject the write.</li>
            <li>Meridian. EBITDA is a dash. Not on the page.</li>
            <li>Approve HarborPay. Payload gets a record_id. SharePoint attaches.</li>
            <li>Optional: Pernix, EDGAR Guggenheim book, not in the gold set. Pass, blanks stay blank.</li>
          </ol>
        </section>

        <section className="mt-6 border-t border-[#2c3340] pt-4">
          <h2 className="text-[10px] font-semibold uppercase tracking-[0.14em] text-zinc-500">Week 1 at a real flagship</h2>
          <p className="mt-3 text-sm leading-6 text-zinc-400">
            Map their DealCloud fields and HITL users. Freeze an eval on the last 20 CIMs they actually received. Ask who
            owns the account in CRM versus the CIM cover (that is the LinkedIn mapping question). Do not start with
            portfolio reporting. Inbound screening is the wedge; the rest of the stack is a field note, not this demo.
          </p>
        </section>
      </main>
    </div>
  );
}
