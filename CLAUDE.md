# CLAUDE.md

Working agreement for AI-assisted development on this repo. Read this first every session.

## What this is

`cua` — a small, real **computer-use automation** system for the interface.ai take-home.
An LLM discovers how to accomplish a natural-language goal on a live UI (observe → decide →
act). The successful run is distilled into a **typed, versioned Capability artifact**. That
artifact is then **replayed deterministically with no model in the decision loop**, returning
typed outputs or a typed outcome. A human can take control of the same live session when the
system is stuck.

Primary target surface: **ParaBank** (`parabank.parasoft.com`, public Parasoft test site).
Second adapter for portability proof: **SauceDemo**. A no-DOM legacy surface is designed for
but not built (REPORT §7).

This is an assessment. **Every decision must be defensible.** If you make an architectural
choice, record it as an ADR in `ARCHITECTURE.md` (context → options → decision → consequences).

## Invariants — do not violate without an ADR that says why

1. **The LLM is in exactly one place: `cua.agent` discovery.** `cua.replay` must never import
   `cua.llm` or `cua.agent`. Replay decisions are data-driven only.
2. **The agent never reasons over raw HTML.** Perception yields an accessibility-tree-based
   `Observation` (roles, names, states) + a screenshot. No markup in prompts or artifacts.
3. **Safety is enforced at the driver, not the prompt.** `cua.policy.check()` is called inside
   `cua.surface.perform()` and again in `cua.agent` before acting. A `Block` actually stops.
4. **No secrets or raw PII are persisted — anywhere.** Every write path (traces, artifacts,
   intervention bundles, evidence) goes through `cua.redaction`, driven by declared
   `sensitivity`. Regex is only a backstop. Never log the pre-scrub value.
5. **Actions are a closed, typed set** (`cua.actions`). No free-form action strings.
6. **The `Surface` protocol is the only seam to a concrete UI tech.** `agent`, `perception`,
   `replay`, `locators` are surface-agnostic and never touch Playwright directly.
7. **Element identity is data, not code.** A `TargetSpec` is an ordered list of locator
   strategies stored in the artifact — reviewable and tenant-overridable.
8. **Result is a typed union, never a status string** (`cua.outcomes.Result`):
   `Success | BusinessOutcome | HardFailure`. "No such member" is a `BusinessOutcome`.
9. **One writer at a time.** Live-session control is a lease held by `cua.session`; automation
   `perform()` is rejected while `owner == HUMAN`.

## Stack & tooling

- Python **3.12**, **`uv`** for everything: `uv venv` → `uv sync --extra dev` → `uv run ...`
- `pydantic` v2 for all models · `typer` CLI · `playwright` (sync) for `WebSurface` ·
  `anthropic` SDK (hand-rolled tool-call loop, **no agent framework**) · `structlog` JSONL ·
  `fastapi`/`uvicorn` for the Session Host control plane.
- Lint/type/test: `uv run ruff check .` · `uv run pyright` (strict) · `uv run pytest`
- Model id: `claude-sonnet-5` (via `CUA_MODEL`). Keys only in `.env` (gitignored).

## Repo map

| Path | What |
|---|---|
| `src/cua/` | the package — one dir per module, contract docstring in each `__init__.py` |
| `config/default.yaml` | allowlist, risk policy, redaction rules, timeouts, detectors |
| `config/tenants/*.yaml` | sparse tenant overlays (ADR-014) |
| `artifacts/` | saved Capability JSON — **tracked**, reviewable |
| `interventions/` | runtime intervention bundles — **gitignored** |
| `evidence/` | deliverable: discovery + replay + error-path logs |
| `REQUIREMENTS.md` | R1–R15 → acceptance criteria → owning module |
| `ARCHITECTURE.md` | component map + every ADR |
| `MODULES.md` | per-module contract + the phased build order |

## How we work here

- **Plan the module before coding it.** We go module-by-module in build-order (see
  `MODULES.md`). Discuss the contract, agree, then implement.
- **TDD where it carries weight**: the artifact schema, locator resolution, the outcome
  taxonomy/detectors, policy checks, redaction, the control lease. Pure-logic modules get
  real tests; thin glue gets a smoke test.
- **Small files, one purpose.** If a module file grows past ~300 lines, it's doing too much.
- **Keep the vertical slice alive.** Prefer a thin-but-working path through every requirement
  over a polished subset. Stub at a clean seam and write down what's stubbed.
- Conventional-ish commits; don't commit unless asked. Never commit `.env` or run output.

## Current status

Scaffolding + planning docs only. No implementation yet. Next: walk `MODULES.md` build order,
Phase 0 first (`config`, `tracing`, `actions`, `artifact`).
