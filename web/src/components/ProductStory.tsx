const STEPS = [
  { id: "upload", label: "Upload" },
  { id: "extract", label: "Extract" },
  { id: "score", label: "Score" },
  { id: "review", label: "Review evidence" },
  { id: "approve", label: "Approve" },
  { id: "write", label: "Write downstream" },
] as const;

export type WorkflowPhase = (typeof STEPS)[number]["id"];

const HARD_POINTS = [
  {
    title: "Missing fields stay blank",
    body: "If EBITDA or leverage is not on the page, Argus leaves a dash. It does not invent a number to complete the record.",
  },
  {
    title: "Retries must not duplicate writes",
    body: "Intake can be re-run. Downstream CRM and document actions stay pending until a human approves, so a retry cannot create a second live record.",
  },
  {
    title: "Humans gate every external write",
    body: "Extract and score can run unattended. Creating or updating a CRM opportunity cannot.",
  },
];

export function productOneLiner() {
  return "Argus converts unstructured investment documents into validated structured records, with human approval before any downstream write.";
}

export function WorkflowStrip({ phase }: { phase: WorkflowPhase }) {
  const current = STEPS.findIndex((step) => step.id === phase);
  return (
    <ol className="flex flex-wrap items-center gap-x-1 gap-y-1">
      {STEPS.map((step, index) => {
        const done = index < current;
        const on = index === current;
        return (
          <li key={step.id} className="flex items-center gap-1">
            {index > 0 ? <span className="px-0.5 text-[10px] text-zinc-600">→</span> : null}
            <span
              className={`border px-2 py-0.5 font-mono text-[10px] ${
                on
                  ? "border-amber-800 bg-[#1a1408] text-amber-200"
                  : done
                    ? "border-emerald-900 bg-[#102418] text-emerald-300/90"
                    : "border-[#2c3340] bg-[#11141a] text-zinc-500"
              }`}
            >
              {step.label}
            </span>
          </li>
        );
      })}
    </ol>
  );
}

export function WhyHard() {
  return (
    <section className="border-t border-[#2c3340]">
      <h2 className="px-4 pt-3 text-[10px] font-semibold uppercase tracking-[0.14em] text-zinc-500">Why this is hard</h2>
      <div className="grid gap-0 md:grid-cols-3">
        {HARD_POINTS.map((point) => (
          <div key={point.title} className="border-t border-[#2c3340] px-4 py-3 md:border-t-0 md:border-l md:first:border-l-0">
            <h3 className="text-[11px] font-semibold tracking-tight text-zinc-200">{point.title}</h3>
            <p className="mt-1 text-[12px] leading-5 text-zinc-500">{point.body}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

export function Architecture() {
  return (
    <section className="border-t border-[#2c3340] px-4 py-3">
      <h3 className="text-[10px] font-semibold uppercase tracking-[0.14em] text-zinc-500">Architecture</h3>
      <p className="mt-1.5 font-mono text-[11px] leading-5 text-zinc-300">
        TypeScript UI → Next.js APIs → extract / score → human approval → CRM / document payload
      </p>
      <p className="mt-1 font-mono text-[11px] leading-5 text-zinc-500">
        Operator runtime: FastAPI → workflow / state → retrieval / tools → Redis / PostgreSQL
      </p>
    </section>
  );
}

export function workflowPhase(status: string, pending: boolean, missing = false): WorkflowPhase {
  if (status.startsWith("Reading") || status.startsWith("Opening") || status.includes("Could not")) {
    return "upload";
  }
  if (status.startsWith("Running")) return "extract";
  if (pending && missing) return "review";
  if (pending) return "approve";
  if (
    status.startsWith("Written") ||
    status.startsWith("Write blocked") ||
    status.startsWith("Writing") ||
    status.startsWith("Blocking")
  ) {
    return "write";
  }
  return "review";
}
