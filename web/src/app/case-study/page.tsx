import type { Metadata } from "next";
import type { ReactNode } from "react";
import Link from "next/link";
import SiteNav from "@/components/SiteNav";

export const metadata: Metadata = {
  title: "Case study · Argus Deal Intake",
  description:
    "How Argus Deal Intake works, why the last-mile is gated by a human, current features, edge cases, and what comes next.",
};

const STEPS = [
  {
    n: "01",
    title: "Thesis first",
    body: "Acme Capital’s mandate is written down before any model runs: North American B2B software and data, $25–100m revenue, ≥15% growth, ≤6x net debt / EBITDA. The scorer does not get to invent a different firm.",
  },
  {
    n: "02",
    title: "Extract only what is on the page",
    body: "Labeled CIM lines, prose financials, or selectable-text PDFs are parsed into a deal object. If EBITDA is not in the package, the field stays blank. Nothing is inferred from “typical SaaS margins.”",
  },
  {
    n: "03",
    title: "Score against the mandate",
    body: "Sector, scale, growth, geography, leverage, and risk each get points. A sector miss is a pass. Missing financials cannot auto-advance. Leverage above 6x is screened, not quietly promoted.",
  },
  {
    n: "04",
    title: "Stop for a human",
    body: "crm_upsert is a destructive tool. The graph (and the Vercel desk) interrupt before DealCloud. Approve writes the opportunity and a SharePoint-style path. Reject leaves no live record.",
  },
  {
    n: "05",
    title: "Measure the claim",
    body: "A frozen eval suite checks field accuracy and hallucinated-missing-field rate. The Python runtime also has HITL inspect/resume APIs, retries, and judge evals. The UI is the associate surface, not the source of truth.",
  },
];

const FEATURES = [
  "CIM / teaser inbox for a synthetic PE firm (Acme Capital)",
  "Upload your own .pdf, .txt, or .md package",
  "Cited extract: revenue, growth, EBITDA, leverage, recurring mix",
  "Thesis scorer with advance / diligence / pass",
  "Human-in-the-loop gate before any CRM write",
  "DealCloud-shaped pipeline: New, Screened, Diligence, Passed",
  "SharePoint-style deal-room path on approve",
  "Python LangGraph operator with inspect/resume for the same loop",
];

const PROS = [
  {
    title: "Trust before automation",
    body: "Associates will not use a workflow that can mint a live opportunity by itself. Pausing on write is the product, not a disclaimer.",
  },
  {
    title: "Blank is a feature",
    body: "A teaser with no EBITDA should look incomplete. Inventing 22% margin to “complete the form” is how deal teams lose faith in AI.",
  },
  {
    title: "Mandate is data, not prompt vibes",
    body: "The thesis is a scored config. Changing the firm means changing the mandate object, not hoping the model remembers PE software screens.",
  },
  {
    title: "Last-mile is full-stack",
    body: "Extraction without a pipeline board, or a board without HITL, is a demo. This is scoped like an embedded deployment: document in, system of record out.",
  },
];

const EDGES = [
  {
    title: "Scanned or image-only PDFs",
    body: "Unpdf reads selectable text. A photographed CIM returns “no usable text.” Workaround: export a .txt from the PDF and upload that.",
  },
  {
    title: "Tables, footnotes, and unit chaos",
    body: "Extract looks for million / mm style figures and common labels. A CIM that only says “$62,500 (000s)” or hides EBITDA in a 12-column table can miss the field. The miss is preferred over a wrong number.",
  },
  {
    title: "Company name inference",
    body: "If there is no Company: line, the parser uses a legal-name heading or the filename. “Project SuperNova” teasers can land under the file stem until a human edits the account name.",
  },
  {
    title: "No live LLM on the Vercel path",
    body: "The public desk is deterministic so a founder demo never depends on an API key. The Python graph can overlay an LLM; the scoring contract stays the same.",
  },
  {
    title: "Pipeline state is local",
    body: "The Vercel board stores opportunities in the browser so serverless instances do not pretend to be a CRM. A refresh on another laptop is a blank board. That is honest. A real DealCloud write would be the durable store.",
  },
  {
    title: "English, PE-shaped language",
    body: "Patterns are built for US/Canada CIM English. A French CIM or a credit agreement with covenant math will under-extract.",
  },
];

const FUTURE = [
  {
    title: "Real DealCloud / Salesforce upsert",
    body: "Replace the in-memory opportunity with an idempotent CRM adapter, field mapping per tenant, and retries. HITL stays in front of the write.",
  },
  {
    title: "LLM extract behind the same schema",
    body: "Use a model to fill DealExtraction, then run the identical blank-if-missing and thesis gates. The schema is the product; the model is a backend.",
  },
  {
    title: "Page-level citations on PDFs",
    body: "Keep [p.N] quotes for text CIMs and add true PDF page anchors so an associate can click through to the source sentence.",
  },
  {
    title: "OCR for scanned books",
    body: "A second path for image PDFs, still forbidden from inventing EBITDA when OCR confidence is low.",
  },
  {
    title: "Firm playbooks",
    body: "Turn Acme Capital’s thesis into a tenant config: multiple mandates, excluded sectors, and “what we refused to automate” notes from the field.",
  },
];

function Card({ title, children }: { title: string; children: ReactNode }) {
  return (
    <article className="rounded-2xl border border-slate-700 bg-[#111a2e] p-5">
      <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
      <div className="mt-3 space-y-3 text-sm leading-6 text-zinc-300">{children}</div>
    </article>
  );
}

export default function CaseStudyPage() {
  return (
    <div className="min-h-full bg-[#070d19] text-zinc-100">
      <main className="mx-auto max-w-3xl px-4 py-10 sm:px-6">
        <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-400">
          Argus · forward-deployed last mile
        </p>
        <div className="mt-3">
          <SiteNav active="case-study" />
        </div>
        <h1 className="mt-6 text-3xl font-semibold tracking-tight sm:text-4xl">
          Case study: CIM intake that is allowed to stop
        </h1>
        <p className="mt-4 text-base leading-7 text-zinc-400">
          Argus Deal Intake is a last-mile workflow for a private-markets desk. A package comes in, it is
          scored against a written thesis, and a human has to approve before anything is written to CRM.
          I built it this way because that is how an investment firm actually lets software into the
          process, and because that is the job of a Forward Deployed Engineer.
        </p>
        <p className="mt-3 text-sm text-zinc-500">
          Live desk:{" "}
          <Link className="text-sky-400 hover:underline" href="/">
            argus-deal-intake.vercel.app
          </Link>
          {" · "}
          <a className="text-sky-400 hover:underline" href="https://github.com/poojaa-12/argus">
            github.com/poojaa-12/argus
          </a>
        </p>

        <div className="mt-8 space-y-5">
          <Card title="What this is">
            <p>
              A synthetic flagship account, Acme Capital, needs inbound CIMs and teasers screened before
              they become DealCloud opportunities. Associates were going to paste numbers by hand. Partners
              wanted speed, but they did not want a model to create a live record unattended.
            </p>
            <p>
              The public site is the associate surface: Next.js, Tailwind, Vercel. Under it is the same
              contract as the Python Argus operator: extract → score → HITL → write. The Python graph adds
              inspect/resume APIs, retries, and evals. The desk is what a deal team can click in ninety
              seconds.
            </p>
          </Card>

          <Card title="Features in this build">
            <ul className="list-disc space-y-1 pl-5">
              {FEATURES.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </Card>

          <Card title="How it works">
            <ol className="space-y-4">
              {STEPS.map((step) => (
                <li key={step.n} className="flex gap-4">
                  <span className="mt-0.5 font-mono text-xs text-sky-400">{step.n}</span>
                  <div>
                    <p className="font-medium text-zinc-100">{step.title}</p>
                    <p className="mt-1 text-zinc-400">{step.body}</p>
                  </div>
                </li>
              ))}
            </ol>
          </Card>

          <Card title="Way of working">
            <p>
              I treat this like an embedded deployment, not a chatbot. First I write down what the firm
              actually screens on. Then I define the object that must come out of a CIM (the extraction
              schema). Then I decide which actions are destructive. Only then does UI or a model show up.
            </p>
            <p>
              The loop I want in the room with a customer: scope the workflow, refuse the parts that need
              judgment, ship a thin slice to production, measure extraction misses, and feed that back as
              a playbook another account can reuse.
            </p>
            <p>
              That is why HITL sits in front of <code className="text-zinc-100">crm_upsert</code>, why
              evals are frozen, and why a sector miss cannot be “fixed” by a friendlier prompt.
            </p>
          </Card>

          <Card title="Why I am thinking this way">
            <p>
              Private-markets software fails in the last mile. The model can summarize a CIM in ten
              seconds and still be unusable if it writes the wrong EBITDA into DealCloud, or if nobody
              trusts it enough to stop pasting from the PDF.
            </p>
            <p>
              Metal’s FDE seat is that last mile: CIM intake, thesis scoring, HITL, CRM, pipeline. I
              wanted a public artifact that already behaves like that seat. A generic RAG demo would
              show I can call an API. This shows I will not let the API become the system of record.
            </p>
            <p>
              Deterministic extract on Vercel is a choice. Founders should be able to click the desk
              without a key. When a live model is added, it has to fill the same schema and fail the
              same way: blank beats fabricated.
            </p>
          </Card>

          <Card title="Pros">
            <div className="grid gap-4 sm:grid-cols-2">
              {PROS.map((item) => (
                <div key={item.title} className="rounded-xl border border-slate-700 bg-[#0f1730] p-4">
                  <p className="font-medium text-zinc-100">{item.title}</p>
                  <p className="mt-2 text-zinc-400">{item.body}</p>
                </div>
              ))}
            </div>
          </Card>

          <Card title="Current edge cases">
            <div className="space-y-4">
              {EDGES.map((item) => (
                <div key={item.title}>
                  <p className="font-medium text-zinc-100">{item.title}</p>
                  <p className="mt-1 text-zinc-400">{item.body}</p>
                </div>
              ))}
            </div>
          </Card>

          <Card title="Future developments">
            <div className="space-y-4">
              {FUTURE.map((item) => (
                <div key={item.title}>
                  <p className="font-medium text-zinc-100">{item.title}</p>
                  <p className="mt-1 text-zinc-400">{item.body}</p>
                </div>
              ))}
            </div>
          </Card>
        </div>

        <p className="mt-10 text-sm text-zinc-500">
          Try the desk: intake Northwind (advance + approve), Helios (pass), Meridian (blank EBITDA),
          then upload your own package.{" "}
          <Link className="text-sky-400 hover:underline" href="/">
            Open Deal Intake
          </Link>
        </p>
      </main>
    </div>
  );
}
