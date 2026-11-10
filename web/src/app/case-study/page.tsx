import type { Metadata } from "next";
import Link from "next/link";
import SiteNav from "@/components/SiteNav";
import { Architecture, productOneLiner, WhyHard, WorkflowStrip } from "@/components/ProductStory";

export const metadata: Metadata = {
  title: "Argus · product",
  description: productOneLiner(),
};

export default function CaseStudyPage() {
  return (
    <div className="min-h-full bg-[#0a0c10] text-zinc-200">
      <main className="mx-auto max-w-2xl px-4 py-8 sm:px-6">
        <div className="flex flex-wrap items-center gap-3">
          <p className="text-sm font-semibold tracking-tight">Argus</p>
          <SiteNav active="case-study" />
        </div>
        <h1 className="mt-5 text-2xl font-semibold tracking-tight">A workflow that is allowed to stop</h1>
        <p className="mt-2 text-[13px] leading-6 text-zinc-300">{productOneLiner()}</p>
        <p className="mt-3 text-sm leading-6 text-zinc-400">
          I built Argus to take an ambiguous inbound document, extract only what the page supports, score it against a
          written mandate, and refuse to write downstream until a human approves. The live desk is a complete product
          loop, not a prompt wrapped in a form.
        </p>
        <div className="mt-4">
          <WorkflowStrip phase="approve" />
        </div>
        <p className="mt-3 font-mono text-[11px] text-zinc-500">
          <Link className="text-zinc-300 hover:underline" href="/">
            Open the desk
          </Link>
          {" · "}
          Gold set 6/6 · 0 invented critical fields · retries 39/50 → 46/50 · injected failure 12/20 → 18/20
        </p>

        <div className="mt-8 -mx-4 border-y border-[#2c3340] sm:-mx-6">
          <WhyHard />
          <Architecture />
        </div>

        <section className="mt-8">
          <h2 className="text-[10px] font-semibold uppercase tracking-[0.14em] text-zinc-500">What the desk will not do</h2>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-sm leading-6 text-zinc-400">
            <li>Quietly reclassify Helios (solar EPC) or Pernix (specialty pharma) as software.</li>
            <li>Invent Meridian EBITDA or leverage from a teaser that does not contain them.</li>
            <li>Write a live CRM record or attach a source file without approval.</li>
            <li>Let a retry of intake create a second downstream write.</li>
          </ul>
        </section>

        <section className="mt-6 border-t border-[#2c3340] pt-4">
          <h2 className="text-[10px] font-semibold uppercase tracking-[0.14em] text-zinc-500">Sixty seconds on the desk</h2>
          <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm leading-6 text-zinc-400">
            <li>HarborPay opens interrupted. Leverage is 6.8x against a 6x cap. Do not approve yet.</li>
            <li>Open Helios. Sector scores 0. Pass. Reject the write — no CRM record.</li>
            <li>Open Meridian. EBITDA is a dash. Not on the page. That is the failure case.</li>
            <li>Approve HarborPay. The CRM payload gets a record id. The source document attaches.</li>
          </ol>
        </section>
      </main>
    </div>
  );
}
