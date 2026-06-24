# Argus

Argus is a small Python project for testing reliability patterns in a ReAct-style
agent execution loop.

The repository focuses on three operational controls:

- typed retries with exponential backoff for transient tool failures
- fallback routing when a primary tool path is unavailable
- required vs optional step handling in multi-step plans
- explicit run terminal statuses and per-step latency traces
- strict plan validation before execution

It also includes deterministic failure-injection evals so results are reproducible.

## Run tests

```bash
python3 -m pytest -q
```

## Generate reliability report

```bash
PYTHONPATH=. python3 -m argus.evals.report
```

Optional runtime config via env-backed JSON:

```bash
ARGUS_RUNTIME_CONFIG=./runtime_config.json PYTHONPATH=. python3 -m argus.evals.report
```

This writes `eval_report.json` with:

- Full-suite baseline vs reliability-enabled success rate (50 tasks).
- Injected-failure baseline vs reliability-enabled recovery rate (20 tasks).

The current deterministic suites produce:

- Main suite: `39/50` (78.0%) -> `46/50` (92.0%, ~91% rounded narrative).
- Failure injection: `12/20` (60.0%) -> `18/20` (90.0%).

## Run outcome statuses

Argus run traces include terminal statuses:

- `success`
- `partial_success_optional_degraded`
- `failed_required_step`
- `failed_policy_exhausted`
- `failed_validation`

## Reliability policy defaults

- Global retry budget is controlled by `RetryPolicy(max_retries=2)` (3 attempts total).
- A step can override attempts via `max_step_attempts_override`.
- A step can enforce timeout budget via `step_timeout_ms`.
- Error classes in traces are normalized to `transient`, `permanent`, or `unknown`.

## Deterministic eval methodology

- Reports are generated with a fixed seed (`1337`) for reproducibility.
- Reports now include per-scenario breakdowns (`network`, `parser`, `executor`, `permanent`).
- Relative recovery uplift should be reported as:
  - `(with_reliability_rate - baseline_rate) / baseline_rate`.
- Example from failure injection suite:
  - baseline `0.60`, reliability `0.90`, relative uplift `0.50` (50%).

## Observability hooks

- `Orchestrator` supports correlation IDs in traces (`TaskPlan.correlation_id`).
- Structured events are emitted for run start, step completion, and terminal outcomes.
- Metrics counters are emitted for run and step outcomes via pluggable exporter interface.

## Interview dashboard (live UI)

Argus includes a lightweight static dashboard at `site/` that renders `eval_report.json`.

Run locally:

```bash
PYTHONPATH=. python3 -m argus.evals.report
python3 -m http.server 8000
```

Then open:

- `http://localhost:8000/site/`

### Deploy to a live URL (`.io`)

1. Push repo to GitHub.
2. Deploy with Netlify or Vercel as a static site (project root as publish root).
3. Point your `.io` domain to that deployment.
4. Re-run evals before interviews so `eval_report.json` is fresh.

