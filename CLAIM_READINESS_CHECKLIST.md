# Argus Claim Readiness Checklist

Use this checklist before citing Argus reliability numbers in resumes, portfolios, or interviews.

## Evaluation Integrity

- [x] Deterministic suites exist for baseline and failure injection.
- [x] Reports run with fixed seed (`1337` by default, configurable).
- [x] Report schema includes total, pass rate, and degraded execution metrics.
- [x] Per-scenario breakdown is included (`network`, `parser`, `executor`, `permanent`).
- [x] Snapshot test guards against accidental reporting drift.

## Reliability Path Coverage

- [x] Retry policy behavior is tested for transient failures.
- [x] Fallback behavior is tested for failure recovery paths.
- [x] Required vs optional semantics are tested and traced.
- [x] Terminal statuses are explicit and tested.
- [x] Validation failures fail fast and are observable.

## Operational Diagnostics

- [x] Run traces include error type, error classification, attempts, and latency.
- [x] Correlation IDs are threaded through run trace + logs.
- [x] Structured logs emit run start, step completion, and terminal events.
- [x] Metrics counters emit for started/succeeded/failed runs and step outcomes.
- [x] Eval report write path is atomic.

## Configuration Safety

- [x] Runtime policy is configurable from env vars.
- [x] Runtime policy is configurable from JSON file (`ARGUS_RUNTIME_CONFIG`).
- [x] Bad config fails safely with explicit error message.

## Claim Methodology

- [x] Relative uplift formula is documented in README.
- [x] Baseline and reliability numbers are generated from the same deterministic suites.
- [x] Evidence artifacts (`eval_report.json`, tests) are reproducible locally.
