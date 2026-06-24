function pct(value) {
  return `${Number(value).toFixed(1)}%`;
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function createMetric(label, value) {
  const box = el("div", "metric");
  box.appendChild(el("div", "label", label));
  box.appendChild(el("div", "value", value));
  return box;
}

function renderEval(containerId, evalData, showUplift = false) {
  const container = document.getElementById(containerId);
  container.innerHTML = "";

  const base = evalData.baseline;
  const improved = evalData.with_reliability;
  const upliftRel =
    base.rate > 0 ? ((improved.rate - base.rate) / base.rate) * 100 : 0;

  const grid = el("div", "metric-grid");
  grid.appendChild(createMetric("Baseline", `${base.passed}/${base.total} (${pct(base.rate_pct)})`));
  grid.appendChild(
    createMetric("With Reliability", `${improved.passed}/${improved.total} (${pct(improved.rate_pct)})`)
  );
  grid.appendChild(createMetric("Delta (pp)", pct(improved.rate_pct - base.rate_pct)));
  if (showUplift) {
    grid.appendChild(createMetric("Relative Uplift", pct(upliftRel)));
  } else {
    grid.appendChild(createMetric("Degraded Runs", `${improved.degraded}/${improved.total}`));
  }
  container.appendChild(grid);
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

      const baseLine = el(
        "div",
        "",
        `Baseline: ${item.baseline.passed}/${item.baseline.total} (${pct(item.baseline.rate_pct)})`
      );
      const relLine = el(
        "div",
        "",
        `Reliable: ${item.with_reliability.passed}/${item.with_reliability.total} (${pct(
          item.with_reliability.rate_pct
        )})`
      );
      const upliftLine = el("div", "", `Uplift (pp): ${pct(item.uplift_rate_points)}`);
      upliftLine.style.color = item.uplift_rate_points > 0 ? "#22c55e" : "#aab6d3";

      const barWrap = el("div", "bar-wrap");
      const bar = el("div", "bar");
      bar.style.width = `${Math.max(0, Math.min(100, item.with_reliability.rate_pct))}%`;
      barWrap.appendChild(bar);

      card.appendChild(baseLine);
      card.appendChild(relLine);
      card.appendChild(upliftLine);
      card.appendChild(barWrap);
      container.appendChild(card);
    });
}

function updateTargetStatus(report) {
  const failure = report.failure_injection_eval;
  const baseline = failure.baseline.rate;
  const reliable = failure.with_reliability.rate;
  const relativeUplift = baseline > 0 ? ((reliable - baseline) / baseline) * 100 : 0;

  const targetLine = document.getElementById("target-line");
  const card = document.getElementById("status-card");
  const hit = relativeUplift >= 35;

  targetLine.textContent = `Target >= 35% relative uplift. Current: ${pct(relativeUplift)} (${pct(
    failure.baseline.rate_pct
  )} -> ${pct(failure.with_reliability.rate_pct)}).`;
  card.classList.remove("good", "warn");
  card.classList.add(hit ? "good" : "warn");
}

async function loadReport() {
  const urls = ["/eval_report.json", "../eval_report.json", "./eval_report.json"];
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

  updateTargetStatus(report);
  renderEval("main-metrics", report.main_eval);
  renderEval("failure-metrics", report.failure_injection_eval, true);
  renderScenarioBlock("main-scenarios", report.main_eval.by_scenario);
  renderScenarioBlock("failure-scenarios", report.failure_injection_eval.by_scenario);
  document.getElementById("runtime-config").textContent = JSON.stringify(
    { seed: report.seed, runtime_config: report.runtime_config },
    null,
    2
  );
}

document.getElementById("reload-btn").addEventListener("click", () => {
  loadReport().catch((err) => {
    document.getElementById("target-line").textContent = err.message;
  });
});

loadReport().catch((err) => {
  document.getElementById("target-line").textContent = err.message;
});
