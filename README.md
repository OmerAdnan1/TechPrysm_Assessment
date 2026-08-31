# cua — Computer-Use Automation

An LLM discovers how to accomplish a natural-language goal on a live UI once
(observe → decide → act). The successful run is distilled into a **typed, versioned Capability
artifact**. That artifact is then **replayed deterministically with no model in the decision
loop**, returning typed outputs or a typed outcome. When the system gets stuck, a human takes
single-writer control of the *same* live session and hands it back.

Built for the interface.ai take-home. Target surface: **ParaBank** (`parabank.parasoft.com`,
a public Parasoft test site — no real credentials, no real PII). A second adapter runs the
same artifact schema against **SauceDemo** to demonstrate portability.

> **Status:** planning + scaffolding complete; implementation proceeds phase-by-phase per
> [`MODULES.md`](MODULES.md). Commands below are the target interface and light up as each
> phase lands. See [`ARCHITECTURE.md`](ARCHITECTURE.md) for design + every decision (ADRs),
> [`REQUIREMENTS.md`](REQUIREMENTS.md) for the acceptance checklist.

## Setup

Requires Python 3.12+ and [`uv`](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/OmerAdnan1/TechPrysm_Assessment.git
cd TechPrysm_Assessment

uv venv                       # create .venv
uv sync --extra dev           # install runtime + dev deps
uv run playwright install chromium

cp .env.example .env          # then edit: ANTHROPIC_API_KEY is required for `discover`
```

Config lives in [`config/default.yaml`](config/default.yaml) (allowlist, risk policy,
redaction rules, timeouts). Secrets come only from `.env` (gitignored).

## Demo path

```bash
# 0. start the session host (owns the live browser; enables human handoff)
uv run cua session start

# 1. DISCOVERY — one real LLM-driven run against the live site
uv run cua discover \
  --goal "look up the account for customer <fixture> and read the savings balance" \
  --target parabank
#   → writes artifacts/lookup_account_balance.json
#   → writes evidence/discovery-<id>/  (trace.jsonl, screenshots, result.json)

# 2. REPLAY — deterministic, no LLM
uv run cua replay lookup_account_balance --param customer=<fixture>
#   → prints a typed Result: Success{ savings_balance: ... }
#   → writes evidence/replay-<id>/

# 3. REPLAY, error path — show detection + typed reporting
uv run cua replay lookup_account_balance --param customer=<nonexistent>
#   → BusinessOutcome(MEMBER_NOT_FOUND)   (exit 0 — a legitimate answer)
uv run cua replay lookup_account_balance --param customer=<fixture> --inject unknown_dialog
#   → HardFailure{ step, expected, observed, evidence_ref }  + failure bundle

# 4. HUMAN-IN-THE-LOOP — take over the live session and hand back
uv run cua operator list
uv run cua operator take <intervention-id>      # you drive the same headed window
uv run cua operator resume <intervention-id>    # automation continues; your actions are recorded

# extras
uv run cua catalog list
uv run cua catalog run lookup_account_balance --param customer=<fixture>
uv run cua stability lookup_account_balance --runs 5   # flakiness / drift signal
```

### Running without live services

- No `ANTHROPIC_API_KEY` → `discover` is unavailable; everything else (replay against a
  recorded artifact, operator handoff, catalog) works.
- Tests use an in-memory fake `Surface` and a stub LLM — `uv run pytest` needs no network.

## Repo layout

| Path | |
|---|---|
| `src/cua/` | the package — one module per directory, contract in each `__init__.py` |
| `config/` | `default.yaml` + `tenants/*.yaml` overlays |
| `artifacts/` | saved Capability JSON (tracked, reviewable) |
| `evidence/` | discovery + replay + error-path logs (deliverable) |
| `ARCHITECTURE.md` · `REQUIREMENTS.md` · `MODULES.md` | design, acceptance, build order |
| `REPORT.md` | the design write-up (seven headings) |

## Development

```bash
uv run ruff check .
uv run pyright
uv run pytest
```

See [`CLAUDE.md`](CLAUDE.md) for the invariants that must hold across the codebase.
