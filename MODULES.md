# Modules & Build Order

Per-module contracts and the phased order we build them in. We discuss and agree a module's
contract, implement it (TDD where it carries weight), verify its milestone, then move on —
keeping a thin working path through every requirement alive at each phase.

Signatures below are the *intended shape*, not final. `→` is "returns".

---

## Module contracts

### `config`
- **Purpose.** One typed, validated source of truth: allowlist, risk policy, redaction rules,
  timeouts, detectors, model id. Merges a tenant overlay.
- **Interface.** `Settings` (frozen pydantic) · `load_settings(tenant: str | None = None) →
  Settings` · `Settings.for_tenant(id) → Settings`.
- **Depends on.** `pydantic`, `pydantic-settings`, `pyyaml`. Nothing in `cua`.
- **Must not.** Read secrets from anywhere but the environment. Have import side effects.
- **Tests that matter.** Overlay merge semantics; env override; rejects unknown keys.

### `tracing`
- **Purpose.** Append-only JSONL event stream per run — the primary evidence surface.
- **Interface.** `Tracer.event(kind: str, **fields)` · `Tracer.span(kind, **fields)` (context
  manager) · `new_run_tracer(run_id, sink_dir) → Tracer`.
- **Depends on.** `structlog`, `redaction`.
- **Must not.** Write a field that didn't pass through `redaction`. Inline big blobs (store
  file refs).
- **Tests.** Every event is valid JSON on one line; scrubber is applied; ordering preserved.

### `redaction`
- **Purpose.** Keep secrets/PII out of every persisted byte. Declaration-driven, regex
  backstop.
- **Interface.** `Sensitivity(Enum)` · `scrub(value, sensitivity) → value` ·
  `scrub_mapping(d, schema) → dict` · `scrub_text(s) → str`.
- **Depends on.** `config.redaction`. Leaf module.
- **Must not.** Be skippable on any sink. Log pre-scrub values.
- **Tests.** `secret→drop`; `pii→mask_last4` keeps only last 4 + length; SSN/token/card
  backstop patterns; idempotent.

### `actions`
- **Purpose.** The closed, typed action vocabulary + intrinsic risk class.
- **Interface.** `RiskClass(Enum)` · `Action` = tagged union `Navigate | Click | TypeText |
  SelectOption | PressKey | ReadValue | WaitFor | AssertCondition | DismissDialog` ·
  `Condition` = typed predicate union.
- **Depends on.** `pydantic`; `locators.TargetSpec` (type-only).
- **Must not.** Contain execution logic or any Playwright reference.
- **Tests.** Union (de)serialises by tag; unknown tag rejected; `TypeText` carries
  `sensitivity`.

### `artifact`
- **Purpose.** The Capability schema — typed, versioned, serializable, transcript-decoupled.
- **Interface.** `Capability`, `Step`, `ParamSpec`, `OutputSpec`, `Checkpoint`, `Provenance`,
  `SurfaceRef`, `TenantOverlay` · `load(path) → Capability` · `dump(cap, path)` ·
  `merge(base, overlay) → Capability` · `Capability.json_schema() → dict`.
- **Depends on.** `pydantic`, `actions`, `locators`.
- **Must not.** Embed model messages. Do surface I/O. Contain tenant concrete values in a base.
- **Tests.** `dump→load` byte-stable; `schema_version` mismatch rejected; malformed file →
  precise error; `merge` leaf-wins + list rules (ADR-014).

### `surface`
- **Purpose.** The perceive/act adapter boundary. Only seam to a concrete UI technology.
- **Interface.** `Surface(Protocol)`: `open() / close()`, `current_url() → str`,
  `raw_perception() → RawPerception`, `perform(action: Action) → ActionResult`,
  `snapshot(reason) → SnapshotRef` · `WebSurface(Surface)` · `DesktopSurface(Surface)` (stub).
- **Depends on.** `playwright` (WebSurface only), `actions`, `policy` (perform is gated here),
  `config`.
- **Must not.** Leak Playwright handles to callers. Decide *what* to do.
- **Tests.** `WebSurface.perform` honours a `policy.Block`; `raw_perception` shape stable;
  `DesktopSurface` raises `NotImplementedError` clearly.

### `perception`
- **Purpose.** Normalize `RawPerception` → model-friendly `Observation`; no raw HTML.
- **Interface.** `Observation`, `Node` · `build_observation(raw) → Observation` ·
  `diff(prev, curr) → ObservationDelta` · `evaluate(cond: Condition, obs) → bool`.
- **Depends on.** `surface` (types), `actions.Condition`, `tracing`.
- **Must not.** Include markup/DOM. Persist anything.
- **Tests.** Unlabelled input gets a synthesised name from nearby text; `diff` detects
  no-progress; `evaluate` covers each `Condition` variant.

### `locators`
- **Purpose.** Compile element identity at record time; resolve it at replay time. The
  determinism seam.
- **Interface.** `Strategy` = `RoleName | LabelAnchored | VisibleText | Structural |
  CssOrTestId` · `TargetSpec` · `compile_target(node, obs) → TargetSpec` ·
  `resolve(spec, surface, timeout_s) → Resolution` where `Resolution = Resolved(handle,
  strategy_used, candidate_count) | Unresolved(tried, reason)`.
- **Depends on.** `perception`, `surface` (types), `config.replay`.
- **Must not.** Silently fall through to brittle XPath — every attempt is recorded.
- **Tests.** Priority order honoured; ambiguous match resolved by captured context; `candidate_count`
  reported; unresolved after timeout → typed `Unresolved`.

### `llm`
- **Purpose.** The only model client. Hand-rolled tool-call loop constrained to `actions`.
- **Interface.** `Decision` = `Act(action, rationale) | GoalMet(evidence) | DeadEnd(reason)` ·
  `decide(goal, obs, history, allowed) → Decision` · `LlmConfig`.
- **Depends on.** `anthropic`, `actions`, `config`.
- **Must not.** Enforce policy. Touch a `Surface`. Be importable from `replay`.
- **Tests.** Tool schema generated from the `Action` union; malformed tool call repaired or
  surfaced; history is bounded.

### `agent`
- **Purpose.** The discovery loop — the one place a model decides. Stopping conditions.
- **Interface.** `DiscoveryRequest {goal, surface, tenant}` · `DiscoveryResult =
  Completed(steps, observations, run_id) | Stopped(reason, run_id)` · `StopReason(Enum)` ·
  `run_discovery(req) → DiscoveryResult`.
- **Depends on.** `perception`, `llm`, `actions`, `policy`, `surface`, `tracing`, `escalation`,
  `evidence`, `config`.
- **Must not.** Write the artifact. Bypass `policy`.
- **Tests.** Each `StopReason` reachable; policy `Block` halts the loop; no-progress detection
  fires at the configured limit.

### `recorder`
- **Purpose.** Distill a successful `DiscoveryResult` into a `Capability`.
- **Interface.** `distill(result, goal, hints: RecorderHints) → Capability` ·
  `propose_params(steps, observations) → [ParamSpec]`.
- **Depends on.** `agent` (types), `artifact`, `locators`, `actions`, `redaction`, `config`.
- **Must not.** Call the LLM. Keep the transcript.
- **Tests.** Retries/dead-ends dropped; concrete member id lifted to a `ParamSpec`; a
  `ReadValue` step becomes an `OutputSpec`; checkpoint chosen from goal-completion assertion.

### `outcomes`
- **Purpose.** The result taxonomy + detectors. "No such member" is an answer.
- **Interface.** `Result = Success(outputs) | BusinessOutcome(code, detail, step) |
  HardFailure(step, expected, observed, evidence_ref, kind)` · `HardFailureKind(Enum)` ·
  `classify(ctx: StepContext, cfg) → Result | None` · `RecoverableHandler` set.
- **Depends on.** `perception.Observation`, `config`, `actions`, `redaction`.
- **Must not.** Contain surface selectors. Decide to escalate.
- **Tests.** Detector ordering (first match wins); 503 → `Recoverable(wait_retry)` → success;
  unknown dialog → `HardFailure(UNEXPECTED_DIALOG)`; not-found text → `BusinessOutcome`.

### `replay`
- **Purpose.** Deterministic executor — the production path. No LLM.
- **Interface.** `ReplayRequest {capability, params, tenant}` · `replay(req) → Result` (from
  `outcomes`).
- **Depends on.** `artifact`, `locators`, `actions`, `surface`, `outcomes`, `policy`,
  `redaction`, `session`, `escalation`, `evidence`, `tracing`.
- **Must not.** Import `llm`/`agent`. Proceed past an unclassified anomaly.
- **Tests.** Import-graph test forbids `llm`; checkpoint asserted before `Success`; typed
  outputs match `OutputSpec`; `--inject` faults produce the right `Result`.

### `session`
- **Purpose.** Own the live `Surface` as an addressable object; arbitrate a single-writer
  control lease.
- **Interface.** `ControlLease {owner, holder_id, since, reason}` · `SessionHost` (FastAPI:
  `POST /sessions`, `GET /sessions/{id}`, `POST|DELETE /sessions/{id}/lease`,
  `POST /sessions/{id}/lease/force`) · `SessionClient` (httpx) · `perform_guard(session_id,
  action)`.
- **Depends on.** `surface`, `fastapi`/`uvicorn`, `httpx`, `config.session`, `tracing`.
- **Must not.** Make automation decisions. Allow two concurrent writers.
- **Tests.** Acquire→409 when held; `force` overrides; `perform` rejected for non-owner; lease
  state survives a client reconnect.

### `escalation`
- **Purpose.** Detect an enumerated stuck state; route an intervention with full context.
- **Interface.** `StuckCondition(Enum)` (6+) · `InterventionRequest` (→
  `interventions/<id>.json`) · `raise_intervention(ctx, condition) → InterventionRequest` ·
  `wait_for_resume(id, poll_s) → ResumeSignal`.
- **Depends on.** `session`, `evidence`, `tracing`, `redaction`, `config`.
- **Must not.** Decide the fix. Resume without an operator signal.
- **Tests.** Each condition serialises with screenshot + a11y refs; `wait_for_resume`
  unblocks on the resume file; bundle is scrubbed.

### `operator`
- **Purpose.** Minimal real handoff — a CLI, not a console (mocked on purpose).
- **Interface.** `operator_list() → [InterventionSummary]` · `operator_take(id)` (acquire
  HUMAN lease, browser to front, start recorder) · `operator_resume(id, note)` (stop recorder,
  persist log, release) · `HumanActionRecorder`.
- **Depends on.** `session`, `surface` (event subscription), `escalation`, `evidence`,
  `tracing`.
- **Must not.** Pretend to be a full UI. Let automation act while HUMAN holds the lease.
- **Tests.** `take` flips lease to HUMAN and blocks automation `perform`; recorder captures a
  scripted nav+type; `resume` writes `human-actions.jsonl` and returns control.

### `catalog`
- **Purpose.** Name-addressable capability invocation — thin dispatch over `replay`.
- **Interface.** `list_capabilities() → [CapabilityCard]` · `show(id) → CapabilityCard` ·
  `invoke(id, params, tenant) → Result`.
- **Depends on.** `artifact`, `replay`, `config`.
- **Must not.** Re-implement replay. Run an unapproved capability unattended if config demands
  approval.
- **Tests.** Card exposes typed inputs/outputs; `invoke` == `replay`; unknown id → clear
  error.

### `evidence`
- **Purpose.** Assemble a run's richer-signal artefacts into one bundle dir.
- **Interface.** `open_bundle(run_id, kind) → RunEvidence` · `RunEvidence.add_screenshot /
  add_snapshot / attach / write_result` · `finalize() → Path`.
- **Depends on.** `tracing`, `redaction`, `config`.
- **Must not.** Store secrets/PII. Grow unbounded (downsample + cap screenshots).
- **Tests.** Failure bundle contains trace + screenshot + snapshot + result; everything
  scrubbed; size cap respected.

### `cli`
- **Purpose.** Typer entry points; thin orchestration only.
- **Interface.** `cua discover | replay | operator | catalog | stability | session`.
- **Depends on.** `typer` + each feature module.
- **Must not.** Hold business logic.
- **Tests.** Arg parsing; exit codes (`BusinessOutcome` → 0, `HardFailure` → non-zero);
  `--help` for each verb.

---

## Build order

Each phase ends with a milestone you can run. Do not start a phase until the prior milestone
is green.

### Phase 0 — Pure types & config
**Modules.** `config`, `redaction`, `tracing`, `actions`, `artifact`.
**Milestone.** Hand-write `artifacts/sample_lookup.json`; `python -c "from cua.artifact import
load; load('artifacts/sample_lookup.json')"` validates it; `pytest` green for redaction +
schema round-trip + config overlay merge.
**Covers.** R3 (schema), R8 (redaction core).

### Phase 1 — Surface & perception
**Modules.** `surface` (`WebSurface`), `perception`, `locators`.
**Milestone.** A dev script opens ParaBank headed, prints an `Observation` (roles + names, no
HTML), then `compile_target` + `resolve` the username field and click Login. No LLM.
**Covers.** R2, R13 (seam exists).

### Phase 2 — Policy
**Modules.** `policy`.
**Milestone.** Unit tests: off-allowlist `Navigate` → `Block`; `Click "Transfer"` under
`confirm` → `NeedsHuman`. `WebSurface.perform` honours a `Block`.
**Covers.** R6, R7.

### Phase 3 — Discovery agent  ← the non-negotiable real run
**Modules.** `llm`, `agent`; wire `evidence`.
**Milestone.** `cua discover --goal "look up account for customer <fixture> and read the
savings balance" --target parabank` completes against the **live** site with a **real** model
call; `evidence/discovery-<id>/` has `trace.jsonl` + screenshots + `result.json`. Each
`StopReason` demonstrated in tests with a fake surface/LLM.
**Covers.** R1, R2, R9 (discovery side).

### Phase 4 — Recorder
**Modules.** `recorder`.
**Milestone.** `cua discover` now also writes `artifacts/<id>.json`. A reviewer reads it and
states inputs/outputs/steps/checkpoint without the code. Distillation tests pass (param
lifting, output inference, retry drop).
**Covers.** R3 (end-to-end).

### Phase 5 — Replay & outcomes
**Modules.** `replay`, `outcomes`.
**Milestone.** `cua replay lookup_account_balance --param customer=<fixture>` → typed
`Success{savings_balance: ...}`. `--param customer=<bad>` → `BusinessOutcome(MEMBER_NOT_FOUND)`
exit 0. `cua replay ... --inject transient_5xx` → `Recoverable` → `Success`;
`--inject unknown_dialog` → `HardFailure` with a failure bundle. Import test forbids `llm` in
`replay`.
**Covers.** R4, R5, R9 (failure signal), R15 (incl. error-path).

### Phase 6 — Session & handoff
**Modules.** `session`, `escalation`, `operator`.
**Milestone.** `cua session start`; run a replay rigged to hit `LOCATOR_UNRESOLVED`;
`interventions/<id>.json` appears with context; `cua operator take <id>` (automation `perform`
now rejected), do the step by hand in the headed window, `cua operator resume <id>` → run
finishes; `human-actions.jsonl` in the evidence bundle.
**Covers.** R10, R11, R12.

### Phase 7 — Catalog, stability, tenant overlay
**Modules.** `catalog`; `stability` verb; wire `artifact.merge` + `config/tenants/parabank.yaml`.
**Milestone.** `cua catalog list` / `cua catalog run lookup_account_balance --param ...`;
`cua stability lookup_account_balance --runs 5` prints per-step `strategy_used` /
`candidate_count` and a flakiness summary; a test applies the tenant overlay and shows one
overridden locator taking effect.
**Covers.** R13 (multi-tenant, in code), stretch: capability catalog + multi-run stability.

### Phase 8 — Second adapter + write-ups
**Modules.** SauceDemo `Surface` config; `README.md`; `REPORT.md`; curate `evidence/`.
**Milestone.** The same `Capability` schema drives a SauceDemo flow (search → detail → add to
cart → checkout review) via `discover` + `replay`. `REPORT.md` has the seven exact headings
filled. `README.md` demo path runs clean. `evidence/` holds the four required artefacts.
**Covers.** R2, R13, R14, R15 (final).

---

## Dependency sketch (build-time)

```
config ── redaction ── tracing
   │          │           │
 actions ──── artifact ───┤
   │            │         │
 surface ◀─ policy        │
   │  │        │          │
perception  locators      │
   │  │        │          │
   ▼  ▼        ▼          ▼
  llm ─▶ agent ─▶ recorder ─▶ (artifacts/)
                    │
        outcomes ─▶ replay ◀─ session ◀─ escalation ◀─ operator
                     │            ▲
                  evidence ───────┘
                     │
                  catalog · cli
```
