# REPORT

Design write-up for the interface.ai computer-use take-home. Target ~1–3 pages.

> **Status: draft skeleton.** Headings are final (they match the brief verbatim). Prose is
> filled in Phase 8 once the implementation exists to describe. Until then, each section
> points to the authoritative detail in [`ARCHITECTURE.md`](ARCHITECTURE.md) (ADRs) and
> [`REQUIREMENTS.md`](REQUIREMENTS.md).

---

## 1. Architecture

*To write in Phase 8.* Cover: the discovery → artifact → replay through-line; the component
map and layering rule; single-package + one long-lived Session Host; sync execution; the key
trade-offs (hand-rolled loop vs. framework, a11y-tree perception vs. DOM/screenshot,
ParaBank vs. hostile local app).
Authoritative detail: ADR-001, ADR-002, ADR-004, ADR-015; ARCHITECTURE §1–§3.

## 2. Artifact schema

*To write in Phase 8.* Cover: the `Capability` fields and why each exists; steps carry
`intent` + typed `Action` + `TargetSpec` + `expectation`; typed `inputs`/`outputs` with
declared `sensitivity`; `checkpoint`; `provenance` without the transcript; `schema_version`
gating; base + sparse `TenantOverlay` instead of per-tenant edits.
Authoritative detail: ADR-006, ADR-007; REQUIREMENTS R3; `src/cua/artifact/`.

## 3. Determinism & error handling

*To write in Phase 8.* Cover: no `llm` import in `replay`; condition-based waits; per-step
`resolve → perform → verify`; checkpoint asserted before `Success`. The result taxonomy
`Success | BusinessOutcome | HardFailure` with an internal `Recoverable` branch; ordered
config-driven detectors; bounded retry/backoff; the `--inject` test seam. Secondarily: UI
drift as a `strategy_used` / `candidate_count` metric surfaced by `cua stability`.
Authoritative detail: ADR-008, ADR-009, ADR-014; REQUIREMENTS R4/R5.

## 4. Heterogeneity & multi-tenant

*To write in Phase 8.* Cover: the `Surface` protocol as the only seam to a UI technology;
`Observation`/`Action`/`TargetSpec` are surface-agnostic, so an artifact is portable; legacy
web = a new `Surface` + the same a11y-first perception; desktop = a `Surface` over OS
accessibility APIs (role+name is the same model); `DesktopSurface` stub. Multi-tenant: one
tenant-neutral base `Capability`, sparse `TenantOverlay` (`merge()`), drift detected by
multi-run stability, fixed by an overlay entry not a re-record.
Authoritative detail: ADR-005, ADR-014; REQUIREMENTS R13; `config/tenants/parabank.yaml`.

## 5. Escalation & handoff

*To write in Phase 8.* Cover: enumerated `StuckCondition`s (not just "max steps"); the
intervention bundle (`interventions/<id>.json` + evidence refs); the Session Host owning the
browser as an addressable object; the single-writer `ControlLease`; `operator take` acquiring
the `HUMAN` lease on the *same* session with automation `perform()` rejected meanwhile;
`HumanActionRecorder`; `operator resume` returning control and persisting `human-actions.jsonl`.
Authoritative detail: ADR-012, ADR-013; REQUIREMENTS R10/R11/R12.

## 6. Safety

*To write in Phase 8.* Cover: allowlist (`origins`, `routes`, `action_types`) enforced by
`policy.check()` inside `surface.perform()` — never in the prompt; risk classification
(intrinsic ∪ config rules) with `block` / `confirm` / `flag` dispositions; risky-action
examples (Transfer/Confirm/Delete, password fields, off-allowlist nav). Redaction driven by
declared `sensitivity` with a regex backstop, applied at every sink. **Limits:** localhost
Session Host has no auth; redaction correctness depends on correct declaration; injected
faults vs. natural ones; rule patterns are target-specific.
Authoritative detail: ADR-010, ADR-011; ARCHITECTURE §5; REQUIREMENTS R6/R7/R8.

## 7. Cuts

*To write in Phase 8.* What was deliberately left out and why (see REQUIREMENTS "Deliberately
deferred / mocked"): the no-clean-DOM local surface (designed, not built), desktop `Surface`,
the co-browsing operator console (CLI instead), multi-tenant plumbing, queues/services,
assisted-LLM replay recovery. **What I'd build next:** the hostile local surface as a concrete
second `Surface`; canonicalisation (`/item/12345 → /item/:id`); a draft→approved gate on
unattended replay; automatic overlay suggestions from the stability report.
Authoritative detail: REQUIREMENTS "Deliberately deferred / mocked"; ADR "revisit-if" notes.
