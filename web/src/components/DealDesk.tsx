"use client";

import { useEffect, useMemo, useState } from "react";
import SiteNav from "@/components/SiteNav";
import type { DealRecord, FirmThesis, Opportunity, ScoredDeal } from "@/lib/types";

type CatalogDeal = Pick<DealRecord, "id" | "company" | "document_type" | "filename">;

type IntakeResponse = {
  deal: DealRecord;
  scored: ScoredDeal;
  opportunity: Opportunity;
  hitl: { tool_name: string; destructive: boolean; reason: string };
};

const STAGES: Opportunity["stage"][] = ["New", "Screened", "Diligence", "Passed"];
const STORAGE_KEY = "argus-deal-pipeline";

function fmt(value: number | string | null | undefined, suffix = "") {
  if (value === null || value === undefined || value === "") return "—";
  return `${value}${suffix}`;
}

function recClass(rec: string | null | undefined) {
  if (rec === "advance") return "text-emerald-400";
  if (rec === "pass") return "text-rose-400";
  return "text-amber-300";
}

export default function DealDesk() {
  const [thesis, setThesis] = useState<FirmThesis | null>(null);
  const [inbox, setInbox] = useState<CatalogDeal[]>([]);
  const [status, setStatus] = useState("Loading thesis…");
  const [busy, setBusy] = useState(false);
  const [active, setActive] = useState<IntakeResponse | null>(null);
  const [pipeline, setPipeline] = useState<Opportunity[]>([]);

  useEffect(() => {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        setPipeline(JSON.parse(saved) as Opportunity[]);
      } catch {
        window.localStorage.removeItem(STORAGE_KEY);
      }
    }
    fetch("/api/deals")
      .then((res) => res.json())
      .then((payload) => {
        setThesis(payload.thesis);
        setInbox(payload.deals);
        setStatus("Ready. Intake a CIM.");
      })
      .catch(() => setStatus("Could not load deals."));
  }, []);

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(pipeline));
  }, [pipeline]);

  const chips = useMemo(() => {
    if (!thesis) return [];
    return [
      `Revenue $${thesis.revenue_m_min}–${thesis.revenue_m_max}m`,
      `Growth ≥ ${thesis.growth_pct_min}%`,
      `Leverage ≤ ${thesis.max_net_debt_ebitda}x`,
      ...thesis.sectors,
    ];
  }, [thesis]);

  async function intake(dealId: string) {
    setBusy(true);
    setStatus(`Scoring ${dealId}…`);
    try {
      const res = await fetch("/api/intake", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dealId }),
      });
      const payload = (await res.json()) as IntakeResponse;
      if (!res.ok) {
        setStatus((payload as unknown as { error?: string }).error || "Intake failed.");
        return;
      }
      setActive(payload);
      setPipeline((current) => {
        const next = current.filter((row) => row.deal_id !== payload.opportunity.deal_id);
        return [...next, payload.opportunity];
      });
      setStatus("Paused for associate approval.");
    } catch {
      setStatus("Intake failed.");
    } finally {
      setBusy(false);
    }
  }

  async function resume(feedback: "approve" | "reject") {
    if (!active) return;
    setBusy(true);
    setStatus(feedback === "approve" ? "Writing DealCloud…" : "Blocking CRM write…");
    try {
      const res = await fetch("/api/resume", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          scored: active.scored,
          feedback,
          filename: active.deal.filename,
        }),
      });
      const payload = (await res.json()) as { opportunity: Opportunity; status: string };
      setActive({ ...active, opportunity: payload.opportunity });
      setPipeline((current) => {
        const next = current.filter((row) => row.deal_id !== payload.opportunity.deal_id);
        return [...next, payload.opportunity];
      });
      setStatus(payload.status === "rejected" ? "Write blocked." : "DealCloud updated.");
    } catch {
      setStatus("Resume failed.");
    } finally {
      setBusy(false);
    }
  }

  async function upload(file: File) {
    setBusy(true);
    setStatus(`Reading ${file.name}…`);
    try {
      const body = new FormData();
      body.append("file", file);
      const res = await fetch("/api/upload", { method: "POST", body });
      const payload = (await res.json()) as IntakeResponse & { error?: string };
      if (!res.ok) {
        setStatus(payload.error || "Could not read that file.");
        return;
      }
      setActive(payload);
      setPipeline((current) => {
        const next = current.filter((row) => row.deal_id !== payload.opportunity.deal_id);
        return [...next, payload.opportunity];
      });
      setStatus(
        payload.scored.extraction.missing_fields.length
          ? `Paused for approval. Blank fields: ${payload.scored.extraction.missing_fields.join(", ")}.`
          : "Paused for associate approval.",
      );
    } catch {
      setStatus("Upload failed.");
    } finally {
      setBusy(false);
    }
  }

  const extraction = active?.scored.extraction;
  const pending = active?.opportunity.status === "pending_approval";

  return (
    <div className="min-h-full bg-[#070d19] text-zinc-100">
      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        <header className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-400">
              Argus Deal Intake · Vercel last-mile demo
            </p>
            <div className="mt-3">
              <SiteNav active="desk" />
            </div>
            <h1 className="mt-4 font-sans text-3xl font-semibold tracking-tight">Acme Capital</h1>
            <p className="mt-2 max-w-2xl text-sm text-zinc-400">
              CIM / teaser extract, thesis score, human-in-the-loop, then DealCloud + SharePoint. Same
              associate loop as the Python runtime, shipped on Next.js / Tailwind / Vercel.
            </p>
          </div>
          <p className="text-sm text-zinc-400">{status}</p>
        </header>

        <section className="rounded-2xl border border-slate-700 bg-[#111a2e] p-5">
          <h2 className="text-lg font-semibold">Firm thesis</h2>
          <p className="mt-2 text-sm text-zinc-400">{thesis?.mandate ?? "Loading mandate…"}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {chips.map((chip) => (
              <span key={chip} className="rounded-full border border-slate-700 bg-[#0f1730] px-3 py-1 text-xs text-zinc-300">
                {chip}
              </span>
            ))}
          </div>
        </section>

        <section className="mt-4 grid gap-4 lg:grid-cols-[0.9fr_1.4fr]">
          <article className="rounded-2xl border border-slate-700 bg-[#111a2e] p-5">
            <h3 className="text-base font-semibold">Inbox</h3>
            <p className="mt-1 text-sm text-zinc-400">
              Synthetic packages, or upload your own CIM / teaser (.pdf, .txt, .md). Missing numbers stay blank.
            </p>
            <label className="mt-3 flex cursor-pointer flex-col rounded-xl border border-dashed border-slate-600 bg-[#0f1730] p-3 text-sm hover:border-sky-500">
              <span className="font-medium">Upload a document</span>
              <span className="mt-1 text-xs text-zinc-400">Selectable-text PDF or a text extract. Max 4.5MB.</span>
              <input
                className="mt-2 text-xs"
                type="file"
                accept=".pdf,.txt,.md,.text,application/pdf,text/plain"
                disabled={busy}
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) void upload(file);
                  event.target.value = "";
                }}
              />
            </label>
            <div className="mt-3 flex flex-col gap-2">
              {inbox.map((deal) => (
                <button
                  key={deal.id}
                  type="button"
                  disabled={busy}
                  onClick={() => intake(deal.id)}
                  className="rounded-xl border border-slate-700 bg-[#0f1730] p-3 text-left hover:border-sky-500 disabled:opacity-60"
                >
                  <div className="font-medium">{deal.company}</div>
                  <div className="mt-1 text-xs text-zinc-400">
                    {deal.document_type} · {deal.filename}
                  </div>
                </button>
              ))}
            </div>
          </article>

          <article className="rounded-2xl border border-slate-700 bg-[#111a2e] p-5">
            <h3 className="text-base font-semibold">Active package</h3>
            {!active || !extraction ? (
              <p className="mt-6 text-sm text-zinc-400">Select a document.</p>
            ) : (
              <div className="mt-3">
                <div className="font-medium">{active.deal.company}</div>
                <div className="text-xs text-zinc-400">
                  {active.deal.document_type} · {active.deal.filename}
                </div>
                <p className={`mt-3 text-3xl font-semibold ${recClass(active.scored.recommendation)}`}>
                  {active.scored.score}/100{" "}
                  <span className="text-lg font-medium">{active.scored.recommendation}</span>
                </p>
                <p className="mt-2 text-sm text-zinc-300">{active.scored.rationale}</p>
                {pending ? (
                  <div className="mt-4 rounded-xl border border-amber-800 bg-[#24180a] p-4">
                    <p className="font-semibold text-amber-200">Human-in-the-loop</p>
                    <p className="mt-1 text-sm text-amber-100/80">{active.hitl.reason}</p>
                    <div className="mt-3 flex gap-2">
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => resume("approve")}
                        className="rounded-lg border border-emerald-700 bg-[#16351f] px-3 py-2 text-sm"
                      >
                        Approve write
                      </button>
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => resume("reject")}
                        className="rounded-lg border border-rose-700 bg-[#3a1518] px-3 py-2 text-sm"
                      >
                        Reject
                      </button>
                    </div>
                  </div>
                ) : (
                  <p className="mt-3 text-sm text-zinc-400">
                    Status: {active.opportunity.status}
                    {active.opportunity.sharepoint_path ? ` · ${active.opportunity.sharepoint_path}` : ""}
                  </p>
                )}
                <dl className="mt-4 grid grid-cols-[132px_1fr] gap-x-3 gap-y-2 text-sm">
                  <dt className="text-zinc-400">Sector</dt>
                  <dd>{fmt(extraction.sector)}</dd>
                  <dt className="text-zinc-400">HQ</dt>
                  <dd>{fmt(extraction.headquarters)}</dd>
                  <dt className="text-zinc-400">Revenue</dt>
                  <dd>{fmt(extraction.revenue_m, "m")}</dd>
                  <dt className="text-zinc-400">Growth</dt>
                  <dd>{fmt(extraction.yoy_growth_pct, "%")}</dd>
                  <dt className="text-zinc-400">EBITDA</dt>
                  <dd>{fmt(extraction.ebitda_m, "m")}</dd>
                  <dt className="text-zinc-400">Leverage</dt>
                  <dd>{fmt(extraction.net_debt_ebitda, "x")}</dd>
                  <dt className="text-zinc-400">Blank fields</dt>
                  <dd>{extraction.missing_fields.join(", ") || "None"}</dd>
                </dl>
                <div className="mt-3 space-y-2">
                  {extraction.citations.slice(0, 4).map((cite) => (
                    <p key={`${cite.field}-${cite.page}`} className="border-l-2 border-sky-400 pl-3 text-xs text-zinc-400">
                      p.{cite.page} · {cite.quote}
                    </p>
                  ))}
                </div>
                <pre className="mt-4 max-h-56 overflow-auto whitespace-pre-wrap rounded-xl border border-slate-700 bg-[#0c1326] p-3 text-[11px] text-zinc-300">
                  {active.deal.text}
                </pre>
              </div>
            )}
          </article>
        </section>

        <section className="mt-4 rounded-2xl border border-slate-700 bg-[#111a2e] p-5">
          <h3 className="text-base font-semibold">Pipeline</h3>
          <div className="mt-3 grid gap-3 md:grid-cols-4">
            {STAGES.map((stage) => (
              <div key={stage} className="min-h-36 rounded-xl border border-slate-700 bg-[#0c1326] p-3">
                <h4 className="text-xs font-semibold uppercase tracking-wide text-zinc-400">{stage}</h4>
                <div className="mt-2 flex flex-col gap-2">
                  {pipeline
                    .filter((row) => row.stage === stage)
                    .map((row) => (
                      <div key={row.opportunity_id} className="rounded-lg border border-slate-700 bg-[#0f1730] p-2">
                        <div className="text-sm font-medium">{row.account_name}</div>
                        <div className="text-xs text-zinc-400">
                          {row.status} · {fmt(row.score)}/100 · {fmt(row.recommendation)}
                        </div>
                      </div>
                    ))}
                </div>
              </div>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
