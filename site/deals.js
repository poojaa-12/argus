const API = window.location.port === "8080" ? "" : "http://127.0.0.1:8080";

const state = {
  deals: [],
  thesis: null,
  active: null,
  run: null,
};

function $(id) {
  return document.getElementById(id);
}

async function fetchJson(path, options) {
  const response = await fetch(`${API}${path}`, options);
  if (!response.ok) {
    throw new Error(`${path} failed (${response.status})`);
  }
  return response.json();
}

function fmt(value, suffix) {
  if (value === null || value === undefined || value === "") return "—";
  return suffix ? `${value}${suffix}` : String(value);
}

function recClass(rec) {
  return rec === "advance" ? "rec-advance" : rec === "pass" ? "rec-pass" : "rec-diligence";
}

function scoreFromEvents(events) {
  const scoreEvent = [...(events || [])].reverse().find((event) => event.tool_name === "thesis_score");
  return (scoreEvent && scoreEvent.output) || null;
}

function renderThesis(thesis) {
  $("thesis-mandate").textContent = thesis.mandate;
  $("thesis-chips").innerHTML = [
    `Revenue $${thesis.revenue_m_min}–${thesis.revenue_m_max}m`,
    `Growth ≥ ${thesis.growth_pct_min}%`,
    `Leverage ≤ ${thesis.max_net_debt_ebitda}x`,
    ...thesis.sectors,
  ]
    .map((label) => `<span class="chip">${label}</span>`)
    .join("");
}

function renderInbox() {
  $("inbox").innerHTML = state.deals
    .map(
      (deal) => `
      <button class="inbox-item" data-id="${deal.id}" type="button">
        <div class="name">${deal.company}</div>
        <div class="meta">${deal.document_type} · ${deal.filename}</div>
      </button>`
    )
    .join("");
  $("inbox").querySelectorAll(".inbox-item").forEach((button) => {
    button.addEventListener("click", () => intake(button.dataset.id));
  });
}

function renderPipeline(opportunities) {
  const byStage = { New: [], Screened: [], Diligence: [], Passed: [] };
  for (const row of opportunities || []) {
    (byStage[row.stage] || byStage.New).push(row);
  }
  document.querySelectorAll(".lane").forEach((lane) => {
    const stage = lane.dataset.stage;
    const body = lane.querySelector(".lane-body");
    body.innerHTML = (byStage[stage] || [])
      .map(
        (row) => `
        <div class="lane-card">
          <div class="name">${row.account_name}</div>
          <div class="meta">${row.status} · ${fmt(row.score)}/100 · ${fmt(row.recommendation)}</div>
        </div>`
      )
      .join("");
  });
}

function renderPackage() {
  const host = $("active-package");
  if (!state.active) {
    host.innerHTML = `<div class="package-empty">Select a document.</div>`;
    return;
  }
  const deal = state.active.deal;
  const scored = scoreFromEvents(state.run?.state?.tool_events);
  const pending = state.run?.status === "interrupted";
  const extraction = scored?.extraction || state.active.opportunity?.extraction || {};
  const rec = scored?.recommendation || state.active.opportunity?.recommendation;
  host.innerHTML = `
    <div class="name">${deal.company}</div>
    <div class="meta">${deal.document_type} · ${deal.filename}</div>
    ${
      scored
        ? `<p class="score-hero ${recClass(rec)}">${scored.score}/100 <span>${rec}</span></p>
           <p>${scored.rationale || ""}</p>`
        : ""
    }
    ${
      pending
        ? `<div class="hitl-banner">
            <strong>Human-in-the-loop</strong>
            <p>CRM upsert is blocked until an associate approves writing ${deal.company} to DealCloud and SharePoint.</p>
            <div class="btn-row">
              <button class="btn good" id="approve-btn" type="button">Approve write</button>
              <button class="btn bad" id="reject-btn" type="button">Reject</button>
            </div>
          </div>`
        : ""
    }
    <div class="kv">
      <div class="label">Sector</div><div>${fmt(extraction.sector)}</div>
      <div class="label">HQ</div><div>${fmt(extraction.headquarters)}</div>
      <div class="label">Revenue</div><div>${fmt(extraction.revenue_m, "m")}</div>
      <div class="label">Growth</div><div>${fmt(extraction.yoy_growth_pct, "%")}</div>
      <div class="label">EBITDA</div><div>${fmt(extraction.ebitda_m, "m")}</div>
      <div class="label">Leverage</div><div>${fmt(extraction.net_debt_ebitda, "x")}</div>
      <div class="label">Blank fields</div><div>${(extraction.missing_fields || []).join(", ") || "None"}</div>
    </div>
    ${(extraction.citations || [])
      .slice(0, 4)
      .map((cite) => `<div class="quote">p.${cite.page} · ${cite.quote}</div>`)
      .join("")}
    <pre class="doc">${deal.text}</pre>
  `;
  const approve = $("approve-btn");
  const reject = $("reject-btn");
  if (approve) approve.addEventListener("click", () => resume("approve"));
  if (reject) reject.addEventListener("click", () => resume("reject"));
}

async function refreshPipeline() {
  const payload = await fetchJson("/v1/deals/pipeline");
  renderPipeline(payload.opportunities);
}

async function intake(dealId) {
  $("status-line").textContent = `Scoring ${dealId}…`;
  state.run = await fetchJson("/v1/deals/intake", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ deal_id: dealId, run_id: `ui-${dealId}` }),
  });
  state.active = await fetchJson(`/v1/deals/${dealId}`);
  $("status-line").textContent =
    state.run.status === "interrupted"
      ? "Paused for associate approval."
      : `Status: ${state.run.status}`;
  renderPackage();
  await refreshPipeline();
}

async function resume(feedback) {
  if (!state.run?.run_id) return;
  $("status-line").textContent = "Writing DealCloud…";
  const resumed = await fetchJson(`/v1/runs/${state.run.run_id}/resume`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ feedback }),
  });
  state.run = { ...state.run, status: resumed.status, state: resumed.state };
  if (state.active?.deal?.id) {
    state.active = await fetchJson(`/v1/deals/${state.active.deal.id}`);
  }
  $("status-line").textContent = resumed.status === "rejected" ? "Write blocked." : "DealCloud updated.";
  renderPackage();
  await refreshPipeline();
}

async function boot() {
  try {
    const payload = await fetchJson("/v1/deals");
    state.deals = payload.deals;
    state.thesis = payload.thesis;
    renderThesis(payload.thesis);
    renderInbox();
    await refreshPipeline();
    $("status-line").textContent = "Ready. Intake a CIM.";
  } catch (error) {
    $("status-line").textContent = "Start the API: make api";
    $("thesis-mandate").textContent = String(error);
  }
}

boot();
