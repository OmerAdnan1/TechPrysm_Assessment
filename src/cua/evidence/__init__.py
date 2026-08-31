"""evidence — evidence bundle assembly (R9, R15).

Purpose
    Collect the richer-signal artefacts for a run into one directory: the JSONL trace,
    per-step screenshots, a11y snapshots on failure, the discovery/replay result, the
    human-action log if a handoff happened. What ends up under /evidence/ for the
    deliverable.

Public interface (to be implemented)
    RunEvidence        -- handle for one run's bundle dir
    open_bundle(run_id, kind: "discovery" | "replay") -> RunEvidence
    RunEvidence.add_screenshot / add_snapshot / attach(path) / write_result(obj)
    finalize() -> Path

Depends on
    tracing, redaction (everything written is scrubbed), config.

Must not
    Store secrets/PII. Grow unbounded — screenshots are downsampled, capped per run.
"""
