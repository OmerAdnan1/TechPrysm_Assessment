# Architecture

How the system is put together and **why** — every non-trivial choice is an ADR below, in
the form *context → options → decision → consequences → revisit-if*, so each can be defended
in isolation.

---

## 1. One-paragraph mental model

A goal and a target go in. A **discovery agent** runs an LLM `observe → decide → act` loop
against a **live surface**, perceiving it through the accessibility tree plus a screenshot,
never raw markup. On success, a **recorder** distills the run — dropping retries, lifting
concrete values into typed parameters — into a **Capability artifact**: a typed, versioned
JSON contract of ordered steps, per-step locator strategies, typed inputs/outputs, and a
checkpoint. In production the **replay engine** loads that artifact and executes it with **no
model in the loop**, resolving each control through an ordered strategy list, classifying
every anomaly into `Success | BusinessOutcome | HardFailure`, and verifying the checkpoint
before returning declared outputs. Throughout, a **policy** layer enforces an allowlist and a
risk classification at the driver boundary, and a **redaction** layer keeps secrets and PII
out of every artifact and log. When the system gets stuck, an **escalation** path hands
single-writer control of the *same live session* to a human via a **control lease**, records
what they do, and resumes.

---

## 2. Component map

```
                       ┌──────────────────────────── cli (typer) ────────────────────────────┐
                       │  discover      replay        operator            catalog   stability │
                       └─────┬───────────┬──────────────┬───────────────────┬─────────────────┘
                             │           │              │                   │
                    ┌────────▼──────┐    │       ┌──────▼───────┐    ┌──────▼───────┐
                    │    agent      │    │       │   operator    │    │   catalog    │
                    │ observe/decide│    │       │ (mock console)│    │ (name→replay)│
                    │  /act loop    │    │       └──────┬───────┘    └──────┬───────┘
                    └──┬────┬────┬──┘    │              │                   │
                       │    │    │       │              │                   │
              ┌────────▼┐ ┌─▼──┐ │  ┌────▼─────┐   ┌────▼──────┐            │
              │perception│ │llm │ │  │  replay  │   │ escalation│            │
              └────┬─────┘ └────┘ │  └──┬───┬───┘   └────┬──────┘            │
                   │              │     │   │            │                   │
                   │        ┌─────▼─────▼┐  │       ┌────▼─────┐             │
                   │        │  policy    │  │       │ session   │◀───────────┘
                   │        │ (allowlist,│  │       │ host +    │
                   │        │  risk)     │  │       │ ControlLease
                   │        └─────┬──────┘  │       └────┬─────┘
                   │              │         │            │
             ┌─────▼──────────────▼─────────▼────────────▼─────┐
             │                  surface  (Protocol)             │
             │   WebSurface (Playwright)   DesktopSurface(stub) │
             └───────────────────────┬─────────────────────────┘
                                     │
        cross-cutting:  actions · locators · artifact · outcomes · recorder
                        redaction · tracing · evidence · config
```

**Layering rule:** `agent`, `perception`, `replay`, `locators` sit *above* `surface` and know
only the `Surface` protocol. `redaction` and `config` are leaves. `llm` is reachable only
from `agent`.

---

## 3. Data flow

### Discovery (LLM in the loop)

```
goal, target ─▶ agent.run_discovery
  loop:
    surface.raw_perception ─▶ perception.build_observation ─▶ Observation (nodes + screenshot)
    llm.decide(goal, Observation, history) ─▶ Decision(Act | GoalMet | DeadEnd)
    policy.check(action, Observation) ─▶ Allow | Flag | Block | NeedsHuman
    surface.perform(action)                (policy re-checked inside)
    tracing.event(...)  ; progress = perception.diff(prev, curr)
    stop if: GoalMet · MAX_STEPS · RUN_TIMEOUT · DEAD_END · NO_PROGRESS · policy NeedsHuman
  on GoalMet ─▶ DiscoveryResult.Completed(steps, observations)
                    │
              recorder.distill ─▶ Capability ─▶ artifact.dump ─▶ artifacts/<id>.json
                    └▶ evidence/discovery-<run>/  (trace.jsonl, screenshots, result.json)
```

### Replay (no LLM)

```
capability_id, params ─▶ replay.replay
  session: acquire AUTOMATION lease on a Session Host session
  for each Step:
    locators.resolve(step.target, surface) ─▶ Resolved(handle, strategy, candidates) | Unresolved
    policy.check(step.action) ─▶ (Block/NeedsHuman short-circuit)
    surface.perform(step.action)
    verify(step.expectation) against fresh Observation
    outcomes.classify(step_context) ─▶ None | BusinessOutcome | Recoverable | HardFailure
        Recoverable ─▶ bounded retry / dismiss / re-auth, then continue
        BusinessOutcome / HardFailure ─▶ break
  verify(capability.checkpoint)
  extract declared outputs
  ─▶ Result: Success{outputs} | BusinessOutcome{code} | HardFailure{step, expected, observed, evidence_ref}
  always ─▶ evidence/replay-<run>/ ; release lease
```

### Escalation & handoff

```
stuck (enumerated) ─▶ escalation.raise_intervention
   session.release(AUTOMATION)
   write interventions/<id>.json  { capability, goal, step, state summary, screenshot ref, a11y ref, reason }
   escalation.wait_for_resume(poll)          ◀── blocks

operator list ─▶ sees <id>
operator take <id> ─▶ session.acquire(HUMAN) ; browser to front ; HumanActionRecorder.start
   … human clicks/types in the SAME window …
operator resume <id> ─▶ HumanActionRecorder.stop ─▶ evidence/.../human-actions.jsonl
   session.release(HUMAN) ; ResumeSignal ─▶ agent/replay continues from next step
```

---

## 4. Architecture Decision Records

> Status key: **Accepted** (committed), **Provisional** (revisit during that module's deep-dive).

### ADR-001 — Language, runtime, package manager
**Context.** Need fast scaffolding, strong typing for the schema, good browser-automation and
LLM libraries.
**Options.** (a) Python 3.12 + uv; (b) TypeScript/Node; (c) Go.
**Decision.** **Python 3.12, `uv`** for env/deps/run. `pydantic` v2 for models, `pyright`
strict, `ruff`, `pytest`.
**Consequences.** + Best-in-class `pydantic` for the artifact schema; first-class Playwright
and Anthropic SDKs; least ceremony. + `uv` gives reproducible, fast envs. − Python's structural
typing is weaker than TS for discriminated unions (mitigated: pydantic tagged unions +
`pyright` strict). − Async story is messier; we use **sync Playwright** to keep the loop
readable.
**Revisit if.** We need to embed in a Node agent runtime.

### ADR-002 — Proxy target
**Context.** Brief forbids real bank systems; wants a non-trivial multi-step flow and the
ability to produce an error-path replay.
**Options.** (a) Local intentionally-hostile legacy web app; (b) ParaBank public test site;
(c) hybrid: local primary + public second adapter.
**Decision.** **ParaBank primary** (`/parabank`), **SauceDemo as the second adapter** to prove
schema portability, **local hostile app deferred** to REPORT §7. Goals: "look up member/account
X and read the savings balance" (search→detail→read) and "open a new account and reach the
confirmation screen" (multi-step form + confirmation).
**Consequences.** + Real login/session/timeout semantics; realistic business errors
(insufficient funds, bad login, internal-error page) available *without* mocking. + Two live
surfaces exercise the `Surface`/locator seams for real. + No ToS risk — it is a purpose-built
test site; we register throwaway customers, no real PII. − ParaBank *has* a usable DOM, so
the "no clean DOM" claim is carried by *design discipline* (ADR-003), not forced by the
target. − Some exceptional states (hard session timeout mid-flow, transient 5xx, unexpected
dialog) must be **injected at the driver** (`--inject`) rather than triggered naturally; this
is a documented test seam, not production behaviour.
**Revisit if.** We get time to build the hostile surface — it slots in as a new `Surface`.

### ADR-003 — Perception model: accessibility tree + screenshot, never raw HTML
**Context.** R2 — must survive a bad DOM; the common real case has no stable selectors.
**Options.** (a) trimmed DOM + CSS/XPath from the model; (b) pure screenshot + pixel
coordinates; (c) accessibility tree as the reasoning substrate + screenshot for
disambiguation.
**Decision.** **(c).** Perception emits an `Observation` = list of interactive nodes
`{ref, role, accessible_name, value, state, bbox}` + a screenshot + page meta + dialog state.
The model picks a `ref` and a typed action. CSS/test-id, when present, is captured only as a
*low-priority fallback strategy* inside the `TargetSpec`, never surfaced to the model.
**Consequences.** + Same code runs on ParaBank and SauceDemo unchanged. + Role+name is exactly
the model OS accessibility APIs expose → desktop is a new `Surface`, not a redesign. + Smaller,
more stable prompts than DOM dumps; cheaper. − The a11y tree can be incomplete on legacy
markup (unlabelled inputs); mitigation: `perception` synthesises names from nearby text/labels,
and the screenshot covers the rest. − Coordinates from the screenshot are a last resort and
never persisted as a primary locator.
**Revisit if.** A target renders to `<canvas>`/Citrix with no a11y tree → fall back to
screenshot+coords as a dedicated `Surface` mode.

### ADR-004 — LLM orchestration: hand-rolled tool-call loop, no framework
**Context.** Need a controllable `observe→decide→act` loop whose output maps cleanly to the
artifact.
**Options.** (a) LangGraph / an agent SDK; (b) provider-native "computer use" beta tool;
(c) hand-rolled loop on the Anthropic SDK with our own tool schemas for the closed action set.
**Decision.** **(c).** `cua.llm.decide()` sends goal + `Observation` + bounded history and
constrains the model to `cua.actions` via generated tool schemas; returns `Act | GoalMet |
DeadEnd`.
**Consequences.** + Full control of the transcript→artifact boundary and of stopping logic.
+ Nothing to explain except our own ~200 lines. + Trivial to swap models. − We implement
ret/parse/repair ourselves. − No free multi-agent features (not needed).
**Revisit if.** We adopt provider computer-use as a distinct `Surface` mode.

### ADR-005 — `Surface` protocol is the only seam to a UI technology
**Context.** R13 — the design must extend to legacy web and desktop without a rewrite.
**Decision.** A `Surface` `Protocol`: `raw_perception()`, `perform(Action)`, `current_url()`,
`snapshot()`, lifecycle. `WebSurface` (Playwright sync) is the only implementation;
`DesktopSurface` is a stub raising `NotImplementedError`. `agent`, `perception`, `replay`,
`locators` import **only** the protocol.
**Consequences.** + The recorded flow (`Capability`) is defined over surface-agnostic
`Observation`/`Action`/`TargetSpec`, so an artifact is portable across `Surface` impls that
can satisfy its strategies. + Clean place to enforce the allowlist (every `perform()`). −
Some Playwright power (network interception, tracing) must be exposed through deliberate
protocol methods rather than used ad hoc.
**Revisit if.** Two surfaces need materially different `Observation` shapes → introduce a
capability-negotiation field.

### ADR-006 — Element identity is an ordered list of strategies, stored as data
**Context.** R4 determinism + R13 tenant reuse. Selectors break; the fix must not be a
re-record.
**Decision.** `TargetSpec = { strategies: [Strategy], notes, recorded_from: fingerprint }`
where `Strategy` ∈ `RoleName | LabelAnchored | VisibleText | Structural | CssOrTestId`, tried
in that priority order. `locators.compile_target(node, obs)` builds it at record time;
`locators.resolve(spec, surface)` returns `Resolution(handle, strategy_used, candidate_count)`
or `Unresolved(tried, reason)`. The list lives in the artifact JSON; a tenant overlay can
replace one entry.
**Consequences.** + Human-reviewable ("found by role=button name=Transfer, else label-anchored
… "). + Drift is observable: `candidate_count`/`strategy_used` per step is the signal
(ADR-014). + Overridable per tenant without touching the base. − Resolution is more code than
a single selector. − Ambiguous matches must be disambiguated by `LabelAnchored`/`Structural`
context captured at record time.
**Revisit if.** We need visual/screenshot-anchored matching → add a `VisualAnchor` strategy.

### ADR-007 — Artifact schema: typed, versioned, transcript-decoupled, base + overlay
**Context.** The brief's focal point. Must serve both a human reviewer and a calling agent.
**Decision.** A `pydantic` `Capability` (see `MODULES.md` / `REQUIREMENTS.md` R3 for fields).
Canonical JSON, stable key order, `schema_version` gate on load. `provenance` keeps run id /
model / timestamp / git sha — **never** the raw messages. Tenant specialisation is a separate
sparse `TenantOverlay` merged by `artifact.merge()`, not edits to the base.
**Consequences.** + Reviewable and diffable in git. + A caller reads `inputs`/`outputs` and
knows the contract without the code. + Versioned → replay can refuse an artifact it doesn't
understand. − Distillation (`recorder`) is real work: parameterisation, output inference,
checkpoint selection. − Schema changes need a migration story (handled by `schema_version` +
a small upgraders map).
**Revisit if.** Steps need control flow (branch/loop) → add a typed `ControlStep` variant
rather than scripting.

### ADR-008 — Result is a typed union with pluggable detectors
**Context.** R5 — "no such member" is an answer, not a crash; conflating the two is the
classic mistake.
**Decision.** `Result = Success{outputs} | BusinessOutcome{code, detail, step} |
HardFailure{step, expected, observed, evidence_ref, kind}`. `Recoverable{condition,
action_taken, retried}` is an *internal* branch handled inside replay (bounded retry / dismiss
/ re-auth) and rolled up. Detectors are ordered rules from `config` matched against the
`Observation` / action error / HTTP status; first match wins.
**Consequences.** + Caller pattern-matches; a `BusinessOutcome` is exit-0. + New expected
outcomes are config, not code. + Failure carries debug context by construction. − Detector
ordering matters and must be tested. − Misclassification risk (a real failure read as a
business outcome) → detectors are conservative and everything is traced.
**Revisit if.** Outcomes need per-tenant vocabularies → move the detector table into the
overlay (already possible).

### ADR-009 — Determinism strategy for replay
**Context.** R4 — same inputs, same steps, same outputs; the interesting failures are runtime
conditions, not layout drift.
**Decision.** No LLM import in `replay`. Every step: explicit `resolve` with a bounded wait,
then `perform`, then `verify(expectation)` — no implicit sleeps, no "probably worked".
Waiting is condition-based (`WaitFor`) not time-based. Transient loads get bounded backoff
retry from `config`. The `checkpoint` is asserted before `Success`. Runs are seedless and
side-effect-aware: irreversible steps are gated by `policy` even in replay.
**Consequences.** + Reproducible; failures point at a step with expected/observed. + Retries
are bounded and logged, never infinite. − Slower than fire-and-forget. − Requires good
`expectation`s per step, which `recorder` must synthesise well.
**Revisit if.** We add multi-run stability scoring (ADR-014) surfaces flakiness a single run
hides.

### ADR-010 — Safety enforced at the driver, not the prompt
**Context.** R6/R7 — regulated context; the agent "must not act outside" the allowlist.
**Decision.** `config` holds `allowlist{origins, routes, action_types}` and `risk_policy`.
`policy.check(action, obs, cfg)` runs (1) inside `surface.perform()` — the choke point every
action passes through — and (2) in `agent` before acting (defence in depth). Risk disposition:
`block` stop · `confirm` stop + escalate `POLICY_BLOCK_NEEDS_HUMAN` · `flag` proceed + mark
trace. Risky class = intrinsic (`RISKY_IRREVERSIBLE` on the action) ∪ rule matches
(password fields, "Transfer"/"Confirm"/"Delete" buttons, off-allowlist navigation).
**Consequences.** + A jailbroken prompt still cannot exceed the allowlist — enforcement is
code. + One place to audit. − Legitimate risky steps in a recorded capability need an explicit
`approved` disposition (via overlay/config) or every replay escalates. − Rule patterns are
English-ish and target-specific; they live in config and are tested.
**Revisit if.** We add an approval workflow (draft→approved) — the `flag`/`confirm` hooks are
already the seam.

### ADR-011 — Redaction driven by declared sensitivity, regex as backstop
**Context.** R8 — never persist credentials, tokens, full PII.
**Decision.** `ParamSpec`/`OutputSpec` carry `sensitivity ∈ {SECRET, PII, FINANCIAL,
PUBLIC}`. `redaction.scrub()` applies the per-sensitivity policy from `config`
(`secret→drop`, `pii→mask_last4`, `financial→mask_all`, `public→keep`). `scrub_text()` adds
regex/entropy backstops (SSN, bearer token, card number) for undeclared leakage. Every sink —
`tracing`, `artifact.dump`, `evidence`, `interventions` — routes through it. Pre-scrub values
are never logged, even at DEBUG.
**Consequences.** + Correct-by-declaration for known fields; backstop catches the rest.
+ Centralised and testable. − Depends on the recorder/author declaring sensitivity correctly
→ default for any string param captured from a form is `PII` unless explicitly `PUBLIC`. −
Masking can make debugging harder; the trace keeps *shape* (length, last-4) not content.
**Revisit if.** We need format-preserving tokenisation for cross-step correlation.

### ADR-012 — Session ownership: a Session Host process + single-writer control lease
**Context.** R11/R12 — a human must operate the *same* live session, and there must be a way
to know who is in control.
**Options.** (a) runner owns the browser, flips a `lease.json`; (b) a Session Host process
owns the browser, clients hold a lease; (c) CDP remote-debugging multi-attach.
**Decision.** **(b).** A thin long-lived `SessionHost` (FastAPI on localhost) owns one
`Surface` and a `ControlLease {owner: AUTOMATION|HUMAN, holder_id, since, reason}`. `agent`,
`replay`, and `operator` are `SessionClient`s. `perform` is rejected unless the caller holds
the lease. Acquire is 409 if held; operator has `force`.
**Consequences.** + The session is an addressable object that outlives any single CLI
invocation — the clean seam the brief asks for. + "Who is in control" is a GET. + Scales
conceptually to N sessions / a real operator console without changing clients (the "adapter"
the user asked for: clients depend on `SessionClient`, not on a browser). − One more process
to run (`cua session start`). − localhost HTTP is a real, if small, surface — bound to
127.0.0.1, no auth in-scope (documented limit).
**Revisit if.** We need multi-host or auth → `SessionClient` stays, transport changes.

### ADR-013 — Escalation: enumerated stuck conditions + a real-but-mock operator
**Context.** R10 — "detect stuck" must be more than "max steps hit"; §3.6 allows a mocked
operator UI but wants the mechanism real.
**Decision.** `escalation.StuckCondition` enum: `LOCATOR_UNRESOLVED`,
`CHECKPOINT_FAILED_TERMINAL`, `UNKNOWN_DIALOG`, `POLICY_BLOCK_NEEDS_HUMAN`,
`NO_PROGRESS_N_STEPS`, `AUTH_EXPIRED`. Each writes `interventions/<id>.json` with full context
+ evidence refs and blocks on `wait_for_resume`. The operator is a **CLI**
(`list`/`take`/`resume`) that drives the real lease and a real `HumanActionRecorder`.
**Consequences.** + Each stuck class is testable and carries tailored context. + The
control-transfer model and event capture are real; only the console chrome is mocked, which
the brief permits. − A CLI operator can't *see* the browser except the headed window itself
(acceptable for a take-home). − `wait_for_resume` is a blocking poll (simple; fine at this
scale).
**Revisit if.** We build the co-browsing console — it becomes another `SessionClient`.

### ADR-014 — Multi-tenant reuse: base Capability + sparse overlay, drift via stability runs
**Context.** §3.7 — hundreds of tenants, many on the same vendor product; artifacts must be
reused or safely specialised, not re-recorded; per-tenant/version drift must be detected.
**Decision.** The base `Capability` is tenant-neutral. A `TenantOverlay` is a sparse patch:
allowlist deltas, extra `recoverable` conditions, `capability_overrides[capability@version]
[step] → TargetSpec/param-default`. `artifact.merge(base, overlay)` produces the effective
capability at replay. Drift signal: replay records `strategy_used` + `candidate_count` per
step; `cua stability <cap> --runs N` replays N times and flags steps where the primary
strategy stopped matching or became ambiguous → the fix is an overlay entry, not a re-record.
**Consequences.** + One recording serves many tenants; specialisation is small, reviewable,
and diffable. + Drift is a metric, not a surprise. − Merge semantics must be precise
(documented: overlay wins per leaf; lists are add-only except `capability_overrides` which
replaces). − No automatic overlay generation (manual, informed by the stability report) —
acceptable and honest for scope.
**Revisit if.** We add canonicalisation (`/item/12345 → /item/:id`) as a stretch goal — it
slots into `recorder` + `Strategy`.

### ADR-015 — Process & deployment boundaries: one package, one long-lived process
**Context.** §5/§7 — simplicity is rewarded; building queues/clusters is not.
**Decision.** A single installable package with CLI verbs. The **only** long-lived process is
the Session Host; `discover`/`replay`/`operator`/`catalog` are short-lived clients. No queue,
no DB (artifacts and overlays are files in git; runtime state is the Session Host's memory +
`interventions/` files). Synchronous execution.
**Consequences.** + Trivial to run and reason about; the whole system fits in your head.
+ Every persistent thing is a reviewable file. − No concurrency/durability story beyond the
single host (explicitly out of scope). − `interventions/` as a poor-man's queue is fine at
one-operator scale, not beyond.
**Revisit if.** Real deployment — the `SessionClient` seam and file-based artifacts are the
extension points; swap transport/storage without touching feature modules.

---

## 5. Known limits (carried into REPORT §6/§7)

- Localhost Session Host has no auth (bound to 127.0.0.1).
- Some ParaBank exceptional states are injected via a driver test seam, not naturally
  triggered.
- Redaction correctness depends on sensitivity being declared; the default is conservative
  (`PII`) but a mis-declared `PUBLIC` would leak.
- Locator resolution has no visual/screenshot anchoring yet.
- `wait_for_resume` blocks; one operator, one intervention at a time.
