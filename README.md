# Argus

Argus is a small Python project for testing reliability patterns in a ReAct-style
agent execution loop.

The repository focuses on three operational controls:

- typed retries with exponential backoff for transient tool failures
- fallback routing when a primary tool path is unavailable
- required vs optional step handling in multi-step plans

It also includes deterministic failure-injection evals so results are reproducible.

## Run tests

```bash
python3 -m pytest -q
```

## Generate reliability report

```bash
PYTHONPATH=. python3 -m argus.evals.report
```

This writes `eval_report.json` with:

- Full-suite baseline vs reliability-enabled success rate (50 tasks).
- Injected-failure baseline vs reliability-enabled recovery rate (20 tasks).

The current deterministic suites produce:

- Main suite: `39/50` (78.0%) -> `46/50` (92.0%, ~91% rounded narrative).
- Failure injection: `12/20` (60.0%) -> `18/20` (90.0%).

