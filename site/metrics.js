function pct(value) {
  return `${Number(value).toFixed(1)}%`;
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function renderScenarioBlock(containerId, scenarios) {
  const container = document.getElementById(containerId);
  container.innerHTML = "";
  Object.keys(scenarios)
    .sort()
    .forEach((name) => {
      const item = scenarios[name];
      const card = el("div", "scenario");
      card.appendChild(el("div", "name", name));
      card.appendChild(
        el(
          "div",
          "",
          `Baseline: ${item.baseline.passed}/${item.baseline.total} (${pct(item.baseline.rate_pct)})`
        )
      );
      card.appendChild(
        el(
          "div",
          "",
          `Reliable: ${item.with_reliability.passed}/${item.with_reliability.total} (${pct(
            item.with_reliability.rate_pct
          )})`
        )
      );
      const uplift = el("div", "", `Uplift (pp): ${pct(item.uplift_rate_points)}`);
      uplift.style.color = item.uplift_rate_points > 0 ? "#22c55e" : "#aab6d3";
      card.appendChild(uplift);
      container.appendChild(card);
    });
}

function appendRows(tbody, suiteName, suite) {
  Object.keys(suite.by_scenario)
    .sort()
    .forEach((scenario) => {
      const item = suite.by_scenario[scenario];
      const row = document.createElement("tr");
      [
        suiteName,
        scenario,
        `${item.baseline.passed}/${item.baseline.total}`,
        pct(item.baseline.rate_pct),
        `${item.with_reliability.passed}/${item.with_reliability.total}`,
        pct(item.with_reliability.rate_pct),
        pct(item.uplift_rate_points),
        pct(item.degradation_delta_points),
      ].forEach((value) => row.appendChild(el("td", "", value)));
      tbody.appendChild(row);
    });
}

function renderMetricsTable(report) {
  const wrap = document.getElementById("metrics-table-wrap");
  wrap.innerHTML = "";
  const table = el("table", "metrics-table");
  const head = document.createElement("thead");
  const headerRow = document.createElement("tr");
  [
    "Suite",
    "Scenario",
    "Baseline Passed",
    "Baseline %",
    "Reliable Passed",
    "Reliable %",
    "Uplift (pp)",
    "Degradation Delta (pp)",
  ].forEach((h) => headerRow.appendChild(el("th", "", h)));
  head.appendChild(headerRow);
  table.appendChild(head);

  const body = document.createElement("tbody");
  appendRows(body, "main_eval", report.main_eval);
  appendRows(body, "failure_injection_eval", report.failure_injection_eval);
  table.appendChild(body);
  wrap.appendChild(table);
}

async function loadReport() {
  const urls = [
    new URL("../eval_report.json", window.location.href).toString(),
    new URL("./eval_report.json", window.location.href).toString(),
    `${window.location.origin}/eval_report.json`,
  ];
  let report = null;
  let lastError = null;
  for (const url of urls) {
    try {
      const res = await fetch(url, { cache: "no-store" });
      if (!res.ok) continue;
      report = await res.json();
      break;
    } catch (err) {
      lastError = err;
    }
  }
  if (!report) {
    throw new Error(`Could not load eval_report.json. ${lastError || ""}`);
  }

  const f = report.failure_injection_eval;
  const relUplift = f.baseline.rate > 0 ? ((f.with_reliability.rate - f.baseline.rate) / f.baseline.rate) * 100 : 0;
  document.getElementById(
    "metrics-summary"
  ).textContent = `Failure recovery uplift: ${pct(relUplift)} (${pct(f.baseline.rate_pct)} -> ${pct(
    f.with_reliability.rate_pct
  )}).`;
  renderMetricsTable(report);
  renderScenarioBlock("main-metrics-scenarios", report.main_eval.by_scenario);
  renderScenarioBlock("failure-metrics-scenarios", report.failure_injection_eval.by_scenario);
  const syncNode = document.getElementById("last-sync");
  if (syncNode) syncNode.textContent = `Sync: ${new Date().toLocaleTimeString()}`;
}

const reloadBtn = document.getElementById("reload-btn");
reloadBtn.addEventListener("click", async () => {
  reloadBtn.disabled = true;
  reloadBtn.textContent = "Reloading...";
  try {
    await loadReport();
  } catch (err) {
    document.getElementById("metrics-summary").textContent = err.message;
  } finally {
    reloadBtn.disabled = false;
    reloadBtn.textContent = "Reload Report";
  }
});

loadReport().catch((err) => {
  document.getElementById("metrics-summary").textContent = err.message;
});
