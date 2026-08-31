"""tracing — structured JSONL event stream.

Purpose
    One append-only JSONL file per run. Every meaningful event (observation summary,
    decision, action, policy check, outcome classification, lease change, intervention)
    is one line. This is the primary evidence surface (R9) and what a human reads to
    understand a run without the code.

Public interface (to be implemented)
    Tracer.event(kind: str, **fields) -> None
    Tracer.span(kind: str, **fields) -> ContextManager
    new_run_tracer(run_id: str, sink_dir: Path) -> Tracer

Depends on
    structlog. redaction (every field passes through the scrubber before write).

Must not
    Write anything that has not gone through cua.redaction. Hold large blobs inline —
    screenshots/snapshots are files on disk, referenced by path.
"""
