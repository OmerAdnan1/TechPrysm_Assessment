"""catalog — name-addressable capability catalog (stretch-goal-adjacent, kept cheap).

Purpose
    Expose the artifacts/ directory as a set of callable capabilities: list them, show a
    capability's typed input/output contract, and invoke one by name with typed args.
    This is the "agent-facing capability interface" — a thin dispatch over cua.replay,
    not a new execution path.

Public interface (to be implemented)
    list_capabilities() -> list[CapabilityCard]     # id, version, title, inputs, outputs, approval_state
    show(capability_id) -> CapabilityCard
    invoke(capability_id, params: dict, tenant: str | None) -> ReplayResult

Depends on
    artifact (load), replay (invoke), config.

Must not
    Re-implement replay. Run an unapproved capability unattended if config requires approval.
"""
