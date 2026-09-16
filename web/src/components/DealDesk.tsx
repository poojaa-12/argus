"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";
import SiteNav from "@/components/SiteNav";
import type {
  AuditEvent,
  Citation,
  DealCloudRecord,
  EvalStrip,
  FirmThesis,
  InboxDeal,
  IntakePackage,
  Opportunity,
  ScoreBreakdown,
  SharePointItem,
  TraceNode,
  TraceStatus,
} from "@/lib/types";

const STAGES: Opportunity["stage"][] = ["New", "Screened", "Diligence", "Passed"];
const STORAGE_KEY = "argus-deal-pipeline-v2";
const BREAKDOWN: Array<[keyof ScoreBreakdown, number]> = [
  ["sector", 30],
  ["scale", 20],
  ["growth", 20],
  ["geography", 10],
  ["leverage", 10],
  ["risk", 10],
];

type CatalogResponse = {
  thesis: FirmThesis;
  deals: InboxDeal[];
  open: IntakePackage;
  eval?: EvalStrip;
};

function fmt(value: number | string | null | undefined, suffix = "") {
  if (value === null || value === undefined || value === "") return "—";
  return `${value}${suffix}`;
}

function recTone(rec: string | null | undefined) {
  if (rec === "advance") return "text-emerald-400";
  if (rec === "pass") return "text-rose-400";
  return "text-amber-300";
}

function recBg(rec: string | null | undefined) {
  if (rec === "advance") return "border-emerald-800 bg-[#102418] text-emerald-300";
  if (rec === "pass") return "border-rose-900 bg-[#2a1214] text-rose-300";
  return "border-amber-800 bg-[#24180a] text-amber-200";
}

function traceTone(status: TraceStatus) {
  if (status === "done") return "border-emerald-800 text-emerald-300";
  if (status === "interrupted") return "border-amber-700 text-amber-200";
  if (status === "blocked") return "border-rose-800 text-rose-300";
  return "border-zinc-700 text-zinc-500";
}

function statusTone(status: string) {
  if (status.startsWith("INTERRUPTED")) return "border-amber-800 bg-[#1a1408] text-amber-200";
  if (status.startsWith("WRITTEN")) return "border-emerald-800 bg-[#102418] text-emerald-300";
  if (status.includes("BLOCKED") || status.includes("failed") || status.includes("Could not")) {
    return "border-rose-900 bg-[#2a1214] text-rose-300";
  }
  if (
    status.startsWith("Running") ||
    status.startsWith("Writing") ||
    status.startsWith("Reading") ||
    status.startsWith("Blocking") ||
    status.startsWith("Opening")
  ) {
    return "border-sky-900 bg-[#0d1c2a] text-sky-300";
  }
  return "border-[#2c3340] bg-[#11141a] text-zinc-400";
}

export default function DealDesk({ initial }: { initial?: CatalogResponse }) {
  const [thesis, setThesis] = useState<FirmThesis | null>(initial?.thesis ?? null);
  const [inbox, setInbox] = useState<InboxDeal[]>(initial?.deals ?? []);
  const [status, setStatus] = useState(
    initial?.open ? "INTERRUPTED · hitl_gate · crm_upsert" : "Opening inbound…",
  );
  const [busy, setBusy] = useState(false);
  const [active, setActive] = useState<IntakePackage | null>(initial?.open ?? null);
  const [pipeline, setPipeline] = useState<Opportunity[]>(
    initial?.open ? [initial.open.opportunity] : [],
  );
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    const savedRaw = window.localStorage.getItem(STORAGE_KEY);
    let saved: Opportunity[] = [];
    if (savedRaw) {
      try {
        saved = JSON.parse(savedRaw) as Opportunity[];
      } catch {
        window.localStorage.removeItem(STORAGE_KEY);
      }
    }
    const seed = initial?.open;
    if (seed) {
      setPipeline(() => {
        if (saved.some((row) => row.deal_id === seed.opportunity.deal_id)) return saved;
        return [...saved, seed.opportunity];
      });
      setHydrated(true);
      return;
    }
    fetch("/api/deals")
      .then((res) => res.json())
      .then((payload: CatalogResponse) => {
        setThesis(payload.thesis);
        setInbox(payload.deals);
        setActive(payload.open);
        setPipeline(() => {
          if (saved.some((row) => row.deal_id === payload.open.opportunity.deal_id)) return saved;
          return [...saved, payload.open.opportunity];
        });
        setHydrated(true);
        setStatus("INTERRUPTED · hitl_gate · crm_upsert");
      })
      .catch(() => setStatus("Could not load desk."));
  }, [initial]);

  useEffect(() => {
    if (!hydrated) return;
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(pipeline));
  }, [hydrated, pipeline]);

  const chips = useMemo(() => {
    if (!thesis) return [];
    return [
      `Rev $${thesis.revenue_m_min}–${thesis.revenue_m_max}m`,
      `Growth ≥${thesis.growth_pct_min}%`,
      `Lev ≤${thesis.max_net_debt_ebitda}x`,
      ...thesis.sectors,
    ];
  }, [thesis]);

  function applyPackage(payload: IntakePackage, nextStatus: string) {
    setActive(payload);
    setPipeline((current) => {
      const next = current.filter((row) => row.deal_id !== payload.opportunity.deal_id);
      return [...next, payload.opportunity];
    });
    setStatus(nextStatus);
  }

  async function intake(dealId: string) {
    setBusy(true);
    setStatus(`Running operator · ${dealId}`);
    try {
      const res = await fetch("/api/intake", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dealId }),
      });
      const payload = (await res.json()) as IntakePackage & { error?: string };
      if (!res.ok) {
        setStatus(payload.error || "Intake failed.");
        return;
      }
      applyPackage(payload, "INTERRUPTED · hitl_gate · crm_upsert");
    } catch {
      setStatus("Intake failed.");
    } finally {
      setBusy(false);
    }
  }

  async function resume(feedback: "approve" | "reject") {
    if (!active) return;
    setBusy(true);
    setStatus(feedback === "approve" ? "Writing Opportunity…" : "Blocking write…");
    try {
      const res = await fetch("/api/resume", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          scored: active.scored,
          feedback,
          filename: active.deal.filename,
          deal: active.deal,
        }),
      });
      const payload = (await res.json()) as IntakePackage & { status: string };
      applyPackage(
        { ...payload, deal: { ...payload.deal, text: active.deal.text || payload.deal.text } },
        payload.opportunity.status === "rejected" ? "WRITE BLOCKED · no live record" : "WRITTEN · DealCloud + SharePoint",
      );
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
      const payload = (await res.json()) as IntakePackage & { error?: string };
      if (!res.ok) {
        setStatus(payload.error || "Could not read that file.");
        return;
      }
      const missing = payload.scored.extraction.missing_fields;
      applyPackage(
        payload,
        missing.length
          ? `INTERRUPTED · blank ${missing.join(", ")}`
          : "INTERRUPTED · hitl_gate · crm_upsert",
      );
    } catch {
      setStatus("Upload failed.");
    } finally {
      setBusy(false);
    }
  }

  const extraction = active?.scored.extraction;
  const pending = active?.opportunity.status === "pending_approval";
  const citeFor = (field: string): Citation | undefined =>
    extraction?.citations.find((row) => row.field === field);

  return (
    <div className="min-h-full bg-[#0a0c10] font-sans text-[13px] text-zinc-200">
      <header className="sticky top-0 z-10 border-b border-[#2c3340] bg-[#0a0c10]/95 backdrop-blur">
        <div className="flex flex-wrap items-start justify-between gap-3 px-4 py-3">
          <div className="min-w-0 max-w-3xl">
            <p className="text-[10px] uppercase tracking-[0.16em] text-zinc-500">Acme Capital · synthetic tenant</p>
            <h1 className="mt-0.5 text-sm font-semibold tracking-tight">Inbound screening</h1>
            <p className="mt-1.5 text-[12px] leading-5 text-zinc-400">
              Prototype built for Metal&apos;s CIM intake workflow — CIM parsing → thesis scoring →
              human-approved DealCloud write. Built by Sai Pooja Sabbani
              {" · "}
              <a className="text-zinc-300 hover:underline" href="https://linkedin.com/in/saipoojasabbani" target="_blank" rel="noreferrer">
                LinkedIn
              </a>
              {" · "}
              <a className="text-zinc-300 hover:underline" href="https://github.com/poojaa-12/argus" target="_blank" rel="noreferrer">
                GitHub
              </a>
            </p>
            <div className="mt-2">
              <SiteNav active="desk" />
            </div>
          </div>
          <span className={`shrink-0 border px-2 py-1 font-mono text-[11px] ${statusTone(status)}`}>{status}</span>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-[#222833] px-4 py-2">
          <p className="font-mono text-[10px] text-zinc-500">
            {initial?.eval?.gold ?? "gold 6/6 · 0 invented blanks"}
            {" · "}
            {initial?.eval?.detail ?? "Helios sector pass · Meridian held"}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-1.5 border-t border-[#222833] px-4 py-2">
          <span className="mr-2 text-[10px] uppercase tracking-[0.14em] text-zinc-500">Mandate</span>
          {chips.map((chip) => (
            <span key={chip} className="border border-[#2c3340] bg-[#11141a] px-2 py-0.5 font-mono text-[10px] text-zinc-300">
              {chip}
            </span>
          ))}
          {thesis?.avoid.slice(0, 2).map((item) => (
            <span key={item} className="border border-rose-950 bg-[#1a1012] px-2 py-0.5 font-mono text-[10px] text-rose-300/80">
              avoid {item}
            </span>
          ))}
        </div>
      </header>

      <main className="grid gap-0 min-[1080px]:grid-cols-[210px_minmax(0,1fr)_280px]">
        <aside className="order-2 border-b border-[#2c3340] min-[1080px]:order-1 min-[1080px]:border-b-0 min-[1080px]:border-r">
          <div className="border-b border-[#2c3340] px-4 py-3">
            <h2 className="text-[10px] font-semibold uppercase tracking-[0.14em] text-zinc-500">Queue</h2>
            <label className="mt-2 block cursor-pointer border border-dashed border-[#3a4252] bg-[#11141a] px-2 py-2 hover:border-zinc-400">
              <span className="text-[11px] font-medium">Drop CIM / teaser</span>
              <span className="mt-0.5 block text-[10px] text-zinc-500">PDF · txt · md · 4.5MB · selectable text</span>
              <input
                className="mt-1 w-full text-[10px] text-zinc-400"
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
          </div>
          <div className="flex flex-col">
            {inbox.map((deal) => {
              const on = active?.deal.id === deal.id;
              return (
                <button
                  key={deal.id}
                  type="button"
                  disabled={busy}
                  onClick={() => intake(deal.id)}
                  className={`border-b border-[#222833] px-4 py-3 text-left hover:bg-[#141820] disabled:opacity-50 ${
                    on ? "bg-[#141820]" : ""
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="text-[13px] font-medium leading-tight">{deal.company}</div>
                      <div className="mt-0.5 font-mono text-[10px] text-zinc-500">
                        {deal.source === "edgar" ? "EDGAR exhibit · not in gold set" : `${deal.document_type} · ${deal.filename.replace(/_/g, " ")}`}
                      </div>
                    </div>
                    <span className={`shrink-0 border px-1.5 py-0.5 font-mono text-[10px] uppercase ${recBg(deal.recommendation)}`}>
                      {deal.score} {deal.recommendation}
                    </span>
                  </div>
                  {deal.missing_fields > 0 ? (
                    <span className="mt-1.5 inline-flex border border-amber-900/70 bg-[#1a1408] px-1.5 py-0.5 text-[10px] text-amber-200/90">
                      Not on page · {deal.missing_fields} {deal.missing_fields === 1 ? "field" : "fields"}
                    </span>
                  ) : null}
                </button>
              );
            })}
          </div>
        </aside>

        <section className="order-1 min-w-0 border-b border-[#2c3340] min-[1080px]:order-2 min-[1080px]:border-b-0 min-[1080px]:border-r">
          {!active || !extraction ? (
            <p className="px-4 py-8 text-zinc-500">Opening package…</p>
          ) : (
            <div>
              <div className="flex flex-wrap items-start justify-between gap-3 border-b border-[#2c3340] px-4 py-3">
                <div>
                  <p className="font-mono text-[10px] uppercase tracking-[0.12em] text-zinc-500">
                    {active.deal.document_type} · {active.deal.filename}
                  </p>
                  <h2 className="text-xl font-semibold tracking-tight">{active.deal.company}</h2>
                  <p className="mt-1 max-w-xl text-[12px] leading-5 text-zinc-400">{active.scored.rationale}</p>
                  {extraction.missing_fields.length > 0 ? (
                    <span className="mt-2 inline-flex border border-amber-900/70 bg-[#1a1408] px-1.5 py-0.5 text-[10px] text-amber-200/90">
                      Not on page · {extraction.missing_fields.length}{" "}
                      {extraction.missing_fields.length === 1 ? "field" : "fields"} left blank
                    </span>
                  ) : null}
                </div>
                <div className="text-right">
                  <p className={`font-mono text-3xl font-semibold leading-none ${recTone(active.scored.recommendation)}`}>
                    {active.scored.score}
                    <span className="text-sm text-zinc-500">/100</span>
                  </p>
                  <p className={`mt-1 font-mono text-[11px] uppercase ${recTone(active.scored.recommendation)}`}>
                    {active.scored.recommendation}
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-6 border-b border-[#2c3340]">
                {BREAKDOWN.map(([key, max]) => (
                  <div key={key} className="border-r border-[#222833] px-2 py-2 last:border-r-0">
                    <p className="font-mono text-[9px] uppercase tracking-wide text-zinc-500">{key}</p>
                    <p className="font-mono text-sm">
                      {active.scored.breakdown[key]}
                      <span className="text-zinc-600">/{max}</span>
                    </p>
                  </div>
                ))}
              </div>

              <ol className="flex flex-wrap gap-x-3 gap-y-1 border-b border-[#2c3340] px-4 py-2">
                {(active.trace ?? []).map((node) => (
                  <li key={node.id} className="flex items-center gap-1.5 font-mono text-[10px]">
                    <span className="text-zinc-300">{node.label}</span>
                    <span className={`uppercase ${traceTone(node.status)}`}>{node.status}</span>
                  </li>
                ))}
              </ol>

              {pending ? (
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-amber-900 bg-[#1a1408] px-4 py-3">
                  <div>
                    <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-amber-300">
                      HITL · {active.hitl.tool_name}
                    </p>
                    <p className="mt-1 max-w-xl text-[12px] text-amber-100/80">{active.hitl.reason}</p>
                  </div>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => resume("approve")}
                      className="border border-emerald-700 bg-[#16351f] px-3 py-1.5 text-[12px] font-medium"
                    >
                      Approve write
                    </button>
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => resume("reject")}
                      className="border border-rose-800 bg-[#3a1518] px-3 py-1.5 text-[12px] font-medium"
                    >
                      Reject
                    </button>
                  </div>
                </div>
              ) : (
                <p className={`border-b px-4 py-3 font-mono text-[11px] ${
                  active.opportunity.status === "written"
                    ? "border-emerald-900 bg-[#102418] text-emerald-300"
                    : "border-rose-900 bg-[#2a1214] text-rose-300"
                }`}>
                  {active.opportunity.status === "written"
                    ? `Written · ${active.opportunity.opportunity_id} · ${active.opportunity.stage}`
                    : "Rejected · no live record"}
                </p>
              )}

              <table className="w-full text-left">
                <thead>
                  <tr className="border-b border-[#2c3340] text-[10px] uppercase tracking-[0.12em] text-zinc-500">
                    <th className="px-4 py-2 font-medium">Field</th>
                    <th className="px-2 py-2 font-medium">Value</th>
                    <th className="px-4 py-2 font-medium">Source quote</th>
                  </tr>
                </thead>
                <tbody>
                  {(
                    [
                      ["sector", "Sector", fmt(extraction.sector)],
                      ["headquarters", "HQ", fmt(extraction.headquarters)],
                      ["revenue_m", "Revenue", fmt(extraction.revenue_m, "m")],
                      ["yoy_growth_pct", "Growth", fmt(extraction.yoy_growth_pct, "%")],
                      ["ebitda_m", "EBITDA", fmt(extraction.ebitda_m, "m")],
                      ["ebitda_margin_pct", "Margin", fmt(extraction.ebitda_margin_pct, "%")],
                      ["net_debt_ebitda", "ND/EBITDA", fmt(extraction.net_debt_ebitda, "x")],
                      ["recurring_revenue_pct", "Recurring", fmt(extraction.recurring_revenue_pct, "%")],
                    ] as const
                  ).map(([field, label, value]) => {
                    const cite = citeFor(field);
                    const blank = extraction.missing_fields.includes(field) || value === "—";
                    return (
                      <tr key={field} className="border-b border-[#1c222c]">
                        <td className="px-4 py-2 font-mono text-[11px] text-zinc-500">{label}</td>
                        <td className={`px-2 py-2 font-mono text-[12px] ${blank ? "text-amber-300" : ""}`}>
                          {blank ? "—" : value}
                        </td>
                        <td className="px-4 py-2 text-[11px] leading-4 text-zinc-500">
                          {cite ? (
                            <>
                              <span className="text-zinc-600">p.{cite.page}</span> {cite.quote}
                            </>
                          ) : blank ? (
                            <span className="inline-flex border border-amber-900/70 bg-[#1a1408] px-1.5 py-0.5 text-[10px] text-amber-200/90">
                              Not on page · left blank
                            </span>
                          ) : (
                            "—"
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              {extraction.risks.length ? (
                <div className="px-4 py-3">
                  <p className="text-[10px] uppercase tracking-[0.14em] text-zinc-500">Risks on page</p>
                  <ul className="mt-1 space-y-1 text-[12px] text-zinc-400">
                    {extraction.risks.map((risk) => (
                      <li key={risk}>— {risk}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </div>
          )}
        </section>

        <aside className="order-3 min-w-0">
          <Panel title="Operator">
            <ol className="relative ml-1 border-l border-[#2c3340] pl-3">
              {(active?.trace ?? []).map((node) => (
                <TraceRow key={node.id} node={node} />
              ))}
            </ol>
          </Panel>
          <Panel title="DealCloud · Opportunity">
            <DealCloudCard record={active?.dealcloud} />
          </Panel>
          <Panel title="SharePoint · DealRoom">
            <SharePointCard item={active?.sharepoint} />
          </Panel>
          <Panel title="Audit">
            <AuditList events={active?.audit ?? []} />
          </Panel>
        </aside>
      </main>

      <section className="border-t border-[#2c3340]">
        <div className="flex items-center justify-between px-4 py-3">
          <h3 className="text-[10px] font-semibold uppercase tracking-[0.14em] text-zinc-500">Pipeline</h3>
          <p className="font-mono text-[10px] text-zinc-600">{pipeline.length} record(s) · this browser</p>
        </div>
        <div className="grid md:grid-cols-4">
          {STAGES.map((stage) => (
            <div key={stage} className="min-h-28 border-t border-[#2c3340] px-4 py-3 md:border-l md:border-t-0 md:first:border-l-0">
              <h4 className="flex items-center justify-between text-[10px] font-semibold uppercase tracking-[0.14em] text-zinc-500">
                {stage}
                <span className="font-mono text-zinc-600">
                  {pipeline.filter((row) => row.stage === stage).length}
                </span>
              </h4>
              <div className="mt-2 flex flex-col gap-1.5">
                {pipeline
                  .filter((row) => row.stage === stage)
                  .map((row) => (
                    <div key={row.opportunity_id} className="border border-[#2c3340] bg-[#11141a] px-2 py-1.5">
                      <div className="text-[12px] font-medium">{row.account_name}</div>
                      <div className="font-mono text-[10px] text-zinc-500">
                        {row.status} · {fmt(row.score)} · {fmt(row.recommendation)}
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="border-b border-[#2c3340] px-4 py-3">
      <h3 className="text-[10px] font-semibold uppercase tracking-[0.14em] text-zinc-500">{title}</h3>
      <div className="mt-2">{children}</div>
    </div>
  );
}

function TraceRow({ node }: { node: TraceNode }) {
  return (
    <li className="relative pb-2.5 last:pb-0">
      <span className={`absolute -left-[17px] top-1 h-2 w-2 rounded-full border ${traceTone(node.status)} bg-[#0a0c10]`} />
      <div className="flex items-baseline justify-between gap-2">
        <span className="font-mono text-[11px]">{node.label}</span>
        <span className={`font-mono text-[9px] uppercase ${traceTone(node.status)}`}>{node.status}</span>
      </div>
      <p className="mt-0.5 text-[11px] leading-4 text-zinc-500">{node.detail}</p>
    </li>
  );
}

function DealCloudCard({ record }: { record?: DealCloudRecord }) {
  if (!record) return <p className="text-[12px] text-zinc-500">No Opportunity mapped.</p>;
  return (
    <div>
      <p className="font-mono text-[10px] uppercase text-zinc-500">{record.note}</p>
      <p className="mt-1 font-mono text-[11px] text-zinc-400">
        POST {record.system}/{record.object} · {record.write_status}
      </p>
      <JsonView data={record.payload} />
    </div>
  );
}

function JsonView({ data }: { data: Record<string, string | number | null> }) {
  const json = JSON.stringify(data, null, 2);
  const nodes: ReactNode[] = [];
  const re = /("(?:\\.|[^"\\])*")(\s*:)?|(-?\d+(?:\.\d+)?)|\b(true|false|null)\b/g;
  let last = 0;
  let match: RegExpExecArray | null;
  while ((match = re.exec(json))) {
    if (match.index > last) nodes.push(json.slice(last, match.index));
    if (match[1] && match[2]) {
      nodes.push(
        <span key={`${match.index}-k`} className="text-sky-300">
          {match[1]}
        </span>,
        match[2],
      );
    } else if (match[1]) {
      nodes.push(
        <span key={`${match.index}-s`} className="text-emerald-300">
          {match[1]}
        </span>,
      );
    } else if (match[3]) {
      nodes.push(
        <span key={`${match.index}-n`} className="text-amber-300">
          {match[3]}
        </span>,
      );
    } else {
      nodes.push(
        <span key={`${match.index}-l`} className="text-zinc-500">
          {match[4]}
        </span>,
      );
    }
    last = re.lastIndex;
  }
  if (last < json.length) nodes.push(json.slice(last));
  return (
    <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap border border-[#2c3340] bg-[#0d1016] px-2 py-2 font-mono text-[10px] leading-4 text-zinc-400">
      {nodes}
    </pre>
  );
}

function SharePointCard({ item }: { item?: SharePointItem }) {
  if (!item) return <p className="text-[12px] text-zinc-500">No library path.</p>;
  return (
    <div className="font-mono text-[11px] leading-5">
      <p className="text-zinc-500">
        /sites/{item.site}/{item.library}
      </p>
      <p className="break-all text-zinc-300">{item.path}</p>
      <p className={item.attached ? "text-emerald-400" : "text-zinc-500"}>
        {item.attached ? "attached" : "not attached · waiting HITL"}
      </p>
    </div>
  );
}

function AuditList({ events }: { events: AuditEvent[] }) {
  if (!events.length) return <p className="text-[12px] text-zinc-500">No events.</p>;
  return (
    <ol className="space-y-1.5">
      {events.map((event) => (
        <li key={event.seq} className="grid grid-cols-[28px_1fr] gap-2 font-mono text-[10px] leading-4">
          <span className="text-zinc-600">{event.seq}</span>
          <span>
            <span className="text-zinc-300">{event.actor}</span>{" "}
            <span className="text-zinc-500">{event.action}</span>
            <span className="mt-0.5 block text-zinc-500">{event.detail}</span>
          </span>
        </li>
      ))}
    </ol>
  );
}
