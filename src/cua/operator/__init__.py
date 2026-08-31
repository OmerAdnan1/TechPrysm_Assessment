"""operator — mock operator surface + human-action recorder (deliberately mocked, ADR-013).

Purpose
    A minimal-but-real handoff. Not a co-browsing console (explicitly out of scope) — a
    CLI. It lists pending interventions, lets a human claim the HUMAN lease on the same
    live session, brings the already-headed browser to the front, records what the human
    does, and signals resume so automation continues on the same session.

Public interface (to be implemented)
    operator_list() -> list[InterventionSummary]
    operator_take(intervention_id) -> None      # acquire HUMAN lease, start HumanActionRecorder
    operator_resume(intervention_id, note) -> None  # stop recorder, persist human-action log, release
    HumanActionRecorder -- subscribes to Surface input/nav events while HUMAN holds the lease

Depends on
    session (lease), surface (event subscription), escalation (resume signal),
    evidence (human-action log lands in the run bundle), tracing.

Must not
    Pretend to be a full operator UI. Let automation act while HUMAN holds the lease.
"""
