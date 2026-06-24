# Argus Architecture Plan (Senior Engineer Design)

## 1) Product Goal

Argus is a reliability-first, ReAct-style agent runtime designed to sustain high task success under UI and tool instability. The core objective is to raise recovery success in volatile environments by at least 35% versus a no-reliability baseline, with deterministic, reproducible eval evidence.

## 2) Success Criteria and SLOs

- Recovery success uplift: `>= 35%` relative increase over baseline on failure-injected suites.
- End-to-end task success on standard suite: `>= 90%`.
- Deterministic eval reproducibility: same seed and scripts produce identical outcomes.
- P95 orchestration latency budget per step remains bounded even with retries.
- Zero silent failures: every failed step emits structured error and trace metadata.

## 3) Scope and Non-Goals

In scope:
- Planning + execution loop for multi-step tasks.
- Reliability controls (retry, fallback, optional-step semantics).
- Deterministic simulation/eval harness for regression-proof claims.
- Observability artifacts (run traces, counters, outcome breakdowns).

Out of scope (for v1):
- Real browser automation in production environments.
- Human-in-the-loop UI, dashboards, and policy management UI.
- Distributed orchestration across many workers.

## 4) High-Level Architecture

### Control Plane

- **Task Intake**: receives task plans with required/optional steps and fallback candidates.
- **Policy Engine**: attaches reliability policy per step (retry budget, backoff class, timeout class, fallback eligibility).
- **Eval Config Manager**: owns deterministic scenario scripts and failure profiles.

### Data Plane

- **Orchestrator** (`argus/agent/orchestrator.py`): executes the plan, tracks attempts, applies reliability policy.
- **Tool Adapter Layer**: normalized interface around tools; maps raw exceptions into typed categories.
- **Fallback Router**: chooses backup tool path after terminal primary failure.
- **Trace Writer**: emits structured `RunTrace` and per-step telemetry.

### Evaluation Plane

- **Suite Builder** (`argus/evals/suites.py`): generates baseline + failure-injected tasks.
- **Harness** (`argus/evals/harness.py`): runs orchestrator with policy on/off.
- **Reporter** (`argus/evals/report.py`): computes rates and writes immutable report artifacts.

## 5) Runtime Data Model (Current + Target)

Current model is solid (`TaskPlan`, `PlanStep`, `StepRequirement`, `RunTrace`), and should be extended with:

- `plan_version`: schema version for forward compatibility.
- `step_timeout_ms`: hard timeout budget per step.
- `max_step_attempts_override`: per-step override on retry budget.
- `error_classification`: transient / permanent / unknown.
- `termination_reason`: required_step_failed | policy_exhausted | completed.
- `correlation_id`: request-level trace key for observability joins.

## 6) Execution State Machine

For each step:
1. Validate payload and preconditions.
2. Execute primary tool call with timeout guard.
3. On error, classify as retryable/non-retryable.
4. If retryable and budget remains, retry with bounded exponential backoff.
5. On terminal failure, attempt fallback if allowed.
6. Resolve step outcome:
   - required + failed -> fail-fast run termination.
   - optional + failed -> continue and record degraded execution.
7. Emit `StepTrace` and aggregate run-level status.

Terminal run states:
- `SUCCESS`
- `FAILED_REQUIRED_STEP`
- `FAILED_POLICY_EXHAUSTED`
- `PARTIAL_SUCCESS_OPTIONAL_DEGRADED` (explicitly tracked even if current boolean success is true)

## 7) Reliability Policy Design

- **Retry policy**:
  - bounded retries (`max_retries`), no unbounded loops.
  - jittered exponential backoff.
  - retry only transient classes (`timeout`, `malformed`, `executor`), never permanent.
- **Fallback policy**:
  - fallback only after primary exhaustion/finality.
  - fallback payload mutation must be explicit and audited.
  - fallback failures are separately tagged to avoid root-cause ambiguity.
- **Optional step policy**:
  - optional failures never hide required-step failures.
  - optional failure ratio is a first-class quality metric.

## 8) Edge Cases and Failure Modes

### Plan and Schema
- Empty plans (no steps) should be invalid unless explicitly allowed.
- Duplicate `step_id` in same plan should fail validation.
- Missing tool bindings should fail fast before execution.
- Unknown requirement enum should hard-fail parse.

### Reliability and Control Flow
- Off-by-one retry bugs (attempt counting) must be unit-tested.
- Backoff overflow or negative values must be clamped.
- Fallback loops (primary<->fallback ping-pong) must be impossible by design.
- Optional step failure followed by required step failure should preserve both facts.

### Tool Behavior
- Non-deterministic tool responses should be normalized for deterministic eval mode.
- Partial tool output should be treated as malformed unless schema-valid.
- Slow-hanging tool call should be timeout-classified, not left running.

### Data and Reporting
- Report writes must be atomic to avoid truncated JSON.
- Metrics should include denominator checks (avoid divide-by-zero surprises).
- Ensure deterministic suites stay deterministic across Python versions/random seeds.

## 9) Observability and Diagnostics

Required telemetry per step:
- `task_id`, `step_id`, `tool_name`, `attempt`, `outcome`
- `error_type`, `error_classification`, `used_fallback`
- `latency_ms` (primary and fallback)

Required run-level metrics:
- total success rate
- failure-injection recovery rate
- retry attempt distribution
- fallback invocation rate
- optional degradation rate

Artifacts:
- structured run traces (JSON lines)
- eval summary report (`eval_report.json`)
- scenario-level confusion matrix (transient vs permanent outcomes)

## 10) Testing and Eval Strategy

Test pyramid:
- **Unit tests**: retry math, fallback trigger conditions, optional/required semantics.
- **Property tests**: attempt counters and terminal states remain consistent under random scripts.
- **Integration tests**: multi-step plans with mixed failure classes.
- **Regression evals**: deterministic suites with frozen expected outcomes.

Quality gates:
- PR fails if baseline/reliability delta regresses.
- PR fails if deterministic suite output changes without fixture update rationale.
- PR fails if new error classes lack retry/fallback policy mapping.

## 11) Security and Safety

- Tool payload sanitization and schema validation before execution.
- Strict exception typing; avoid leaking sensitive payloads in error messages.
- Guardrails against untrusted fallback routing.
- Explicit allowlist for tool names in production mode.

## 12) Incremental Implementation Plan (Argus First)

### Phase 1: Core hardening (immediate)
- Add plan validation module (`argus/agent/validators.py`).
- Add explicit terminal run status enum in schema.
- Add `latency_ms` timing to `StepTrace`.
- Add atomic report write helper.

### Phase 2: Reliability policy maturity
- Add per-step timeout and retry override.
- Add error classification enum and mapping table.
- Add policy matrix tests for each error class.

### Phase 3: Eval sophistication
- Add scenario tags (network, parser, executor, permanent).
- Add per-scenario uplift breakdown in report.
- Add deterministic seed controls and fixture snapshots.

### Phase 4: Production-readiness hooks
- Add structured logging interface and correlation IDs.
- Add metrics exporter abstraction.
- Add runtime config loading for policy tuning.

## 13) Definition of Done (for claim readiness)

Argus is claim-ready when:
- deterministic report reproduces target uplift consistently,
- all reliability paths are covered by tests,
- run traces explain every failure and recovery path,
- and failure-injection evals demonstrate sustained recovery gain (>=35%) with documented methodology.
