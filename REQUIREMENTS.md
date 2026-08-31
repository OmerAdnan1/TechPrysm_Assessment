# Requirements

Source of truth for *what must be true* before this project is done. Derived from the
interface.ai brief §3 and the R1–R15 extraction. Each row has a concrete acceptance check
and the module that owns it. ADR references point to the rationale in `ARCHITECTURE.md`.

## Legend

- **Acceptance** — the observable condition that closes the requirement. Written so it can
  become a test or a `evidence/` artifact, not a vibe.
- **Owner** — the module(s) in `src/cua/` responsible. Full contracts in `MODULES.md`.

---

## Traceability

| # | Requirement | Acceptance (done when) | Owner | ADR |
|---|---|---|---|---|
| **R1** | Goal + target as input; LLM observe→decide→act on a live UI; stopping conditions (max steps, timeout, dead-end) | One **real** LLM run against ParaBank, fully logged in `evidence/discovery-*/`, completes a multi-step goal and emits an artifact. Each stop reason is reachable and logged. | `agent`, `llm`, `perception`, `cli` | 003, 004 |
| **R2** | Perception survives a bad DOM | No code path puts raw HTML into a prompt or artifact. `Observation` is a11y-tree + screenshot only. Same `agent` runs unchanged against SauceDemo. | `perception`, `surface` | 003, 005 |
| **R3** | Typed, versioned, serializable artifact: ordered steps, element identification, typed inputs/outputs, checkpoint | `artifact.load()` validates `schema_version` + shape and rejects a malformed file. A reviewer can read `artifacts/*.json` and state what it does, needs, returns — without the code. Round-trips `dump→load` byte-stable. | `artifact`, `recorder`, `locators` | 006, 007 |
| **R4** | Replay with no LLM in the decision loop; stable targeting; checkpoint verified; outputs returned | `cua replay lookup_member_balance --param member_id=12345` returns typed outputs. Import graph proves `replay` cannot reach `llm`/`agent`. Checkpoint asserted before `Success`. | `replay`, `locators`, `outcomes` | 006, 009 |
| **R5** | Three-way result taxonomy: business outcome / recoverable / hard failure | `outcomes.Result` is a discriminated union. A not-found input yields `BusinessOutcome(MEMBER_NOT_FOUND)` (exit 0, not a crash); an injected 503 is absorbed as `Recoverable` then `Success`; an unresolved locator yields `HardFailure` with step/expected/observed. | `outcomes`, `replay` | 008 |
| **R6** | Allowlist of origins, routes, action types — enforced | `policy.check()` is invoked inside `surface.perform()`. A test drives the agent at an off-allowlist origin and the action is `Block`ed with the attempt logged. Not enforced anywhere in the prompt. | `policy`, `surface`, `config` | 010 |
| **R7** | Risky vs. reversible action handling | Every `Action` has a `RiskClass`; `policy.classify_risk()` upgrades per `config` rules. A risky action (`click "Transfer"`) under `confirm` mode does not execute and raises `POLICY_BLOCK_NEEDS_HUMAN`. | `policy`, `actions` | 010 |
| **R8** | No secrets or raw PII in artifacts or logs | Redaction is driven by declared `sensitivity`; a `secret` param never appears in any file; a `pii` value is masked to last-4. Grep of `evidence/` + `artifacts/` for known fixture secrets returns nothing. | `redaction`, all sinks | 011 |
| **R9** | Structured logs + richer signal on failure | Every run writes `trace.jsonl`. Every failed step also writes a screenshot + a11y snapshot into the run's evidence bundle. | `tracing`, `evidence` | 009 |
| **R10** | Detect stuck; raise intervention with context | `escalation.StuckCondition` is an enum (≥6 members), not "max steps hit". Each raises an `InterventionRequest` carrying capability/goal, step, state summary, screenshot ref, a11y ref, reason. | `escalation`, `agent`, `replay` | 013 |
| **R11** | Human takes control of the same live session, hands back | `cua operator take <id>` acquires the `HUMAN` lease on the **existing** Session Host session; automation `perform()` is rejected meanwhile; `cua operator resume <id>` returns the lease and the run continues. | `session`, `operator` | 012, 013 |
| **R12** | Human actions recorded across handoff | While `HUMAN` holds the lease, `HumanActionRecorder` captures nav + input events; on resume they are written to the run's evidence bundle as `human-actions.jsonl`. | `operator`, `evidence` | 012, 013 |
| **R13** | Design story for legacy web, desktop, multi-tenant — backed by an abstraction that exists in code | `Surface` protocol + `DesktopSurface` stub exist. `TenantOverlay` + `artifact.merge()` exist and a `config/tenants/parabank.yaml` overlay is applied in a test. REPORT §4 written. | `surface`, `artifact` | 005, 014 |
| **R14** | Deliverables at exact paths; `REPORT.md` with the seven exact headings verbatim | `/README.md`, `/REPORT.md`, `/evidence/` present; REPORT headings match the brief character-for-character. | repo root | — |
| **R15** | `/evidence/` with artifact, discovery log, replay log, and one **error-path** replay | Four things under `evidence/`: a saved artifact, a discovery `trace.jsonl`, a happy-path replay `trace.jsonl`, and an error-path replay showing detection + typed report. | `evidence`, `cli` | 008, 009 |

---

## Detail on the load-bearing requirements

### R3 — Artifact schema (evaluation focal point)

A `Capability` must express, as typed fields:

- `schema_version`, `id`, `version`, `title`, `description`
- `surface`: kind + tenant-neutral entry point
- `inputs`: `[ParamSpec]` — name, type, required, **sensitivity**, validation, example
- `outputs`: `[OutputSpec]` — name, type, source step, description
- `steps`: `[Step]` — index, human `intent`, typed `Action`, `TargetSpec`, `expectation` (`Condition`)
- `checkpoint`: the success `Condition` asserted on replay
- `provenance`: discovery run id, model, timestamp, git sha — **not** the transcript

Acceptance: JSON Schema exported from the pydantic model; a hand-written malformed artifact is
rejected with a precise error; a reviewer unfamiliar with the code can answer "what does this
need and return?" from the file alone.

### R4 / R5 — Deterministic replay + outcome contract

Replay loop per step: `resolve(TargetSpec) → perform(Action) → verify(expectation)`, then
`classify()` any anomaly. Terminal `Result` is one of:

- `Success{outputs}` — checkpoint verified, declared outputs extracted.
- `BusinessOutcome{code, detail, observed_at_step}` — a legitimate answer (`MEMBER_NOT_FOUND`,
  `INSUFFICIENT_FUNDS`). Caller gets a clean typed value; process exits 0.
- `HardFailure{step, expected, observed, evidence_ref, kind}` — stop, surface a debuggable error.

`Recoverable` (dismiss known interstitial, wait/retry transient load, re-auth) is handled
*inside* replay with bounded retries and rolled up into the terminal `Success`/`HardFailure`,
but every recovery is logged.

### R6 / R7 — Safety

Allowlist (`origins`, `routes`, `action_types`) and risk rules live in `config/default.yaml`
and are enforced by `policy` at the `surface.perform()` boundary. Risk disposition per config:
`block` (stop), `confirm` (stop + escalate to human), `flag` (proceed + mark trace).

### R11 / R12 — Escalation & handoff

The Session Host owns the browser as an addressable object with a single-writer
`ControlLease`. Stuck → automation releases the lease → `interventions/<id>.json` written →
operator CLI claims the `HUMAN` lease → human acts in the same headed window (recorded) →
`operator resume` → lease returns to `AUTOMATION` → run continues on the same session.

---

## Deliberately deferred / mocked (with justification)

| Item | Decision | Why it's safe |
|---|---|---|
| No-clean-DOM legacy surface | **Designed, not built.** `Surface` seam + REPORT §4. | The `Observation` is already a11y-tree-only, so the agent/replay code doesn't change; only a new `Surface` impl is needed. Building a hostile app is surface work, not system work. |
| Desktop surface | `DesktopSurface` stub raising `NotImplementedError`. | Same seam. The role+name perception model is exactly what OS a11y APIs expose. |
| Operator console | **CLI, mocked on purpose** (brief §3.6 allows this). | The *handoff mechanism* (lease, event capture, resume) is real; only the UI chrome is absent. |
| Multi-tenant plumbing | One example overlay + `merge()`; no tenant registry/DB. | Brief §7: "prematurely building that infrastructure is not [rewarded]." The abstraction is what's assessed. |
| Queues / services / horizontal scale | Single package + one long-lived Session Host process. | Brief §5/§7 explicitly de-value this. |
| Assisted LLM fallback on replay failure | Out (stretch goal only). | Keeps the "no model in replay" invariant clean for the core submission. |

## Explicitly out of scope (per brief §4)

Real bank systems; obtaining production access; anything requiring real credentials or real
PII; API-based integration (that's the preferred path when an API exists — not this project).
