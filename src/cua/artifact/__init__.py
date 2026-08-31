"""artifact — the Capability schema (evaluation focal point, ADR-007).

Purpose
    The typed, versioned, serializable contract for a reusable flow. Decoupled from the
    raw model transcript. A human reviewer and a calling agent can both read what the
    capability does, what it needs, and what it returns.

Public interface (to be implemented)
    Capability
        schema_version: int
        id: str                 # e.g. "lookup_member_balance"
        version: int            # bumped on any breaking step/param/output change
        title, description
        surface: SurfaceRef     # kind=web, entry_url, tenant-neutral
        inputs:  list[ParamSpec]     # typed, with sensitivity + validation
        outputs: list[OutputSpec]    # typed shape the caller gets back
        steps:   list[Step]
        checkpoint: Checkpoint       # success condition, asserted on replay
        provenance: Provenance       # discovery run id, model, timestamp, git sha
    Step        -- { index, intent, action: Action, target: TargetSpec, expectation: Condition }
    ParamSpec   -- { name, type, required, sensitivity, validation, example }
    OutputSpec  -- { name, type, source_step, description }
    TenantOverlay -- sparse patch (allowlist delta, recoverable adds, capability_overrides)
    load(path) -> Capability          # validates schema_version + shape, raises on drift
    dump(cap, path) -> None           # canonical JSON, stable key order
    merge(base: Capability, overlay: TenantOverlay) -> Capability

Depends on
    pydantic, actions, locators. No I/O of surfaces, no LLM.

Must not
    Embed the model transcript. Contain tenant-specific concrete values in the base.
"""
