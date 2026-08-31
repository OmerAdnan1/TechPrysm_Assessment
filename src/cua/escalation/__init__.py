"""escalation — stuck detection + intervention routing (ADR-013).

Purpose
    Recognise an enumerated stuck state, release the automation lease, and write an
    intervention request carrying enough context for a human to act: capability/goal,
    current step, state summary, screenshot ref, a11y snapshot ref, reason.

Public interface (to be implemented)
    StuckCondition     -- Enum: LOCATOR_UNRESOLVED | CHECKPOINT_FAILED_TERMINAL | UNKNOWN_DIALOG
                          | POLICY_BLOCK_NEEDS_HUMAN | NO_PROGRESS_N_STEPS | AUTH_EXPIRED
    InterventionRequest-- serialized to interventions/<id>.json (+ referenced evidence files)
    raise_intervention(ctx, condition) -> InterventionRequest
    wait_for_resume(intervention_id, poll_s) -> ResumeSignal   # blocks until operator resume

Depends on
    session (lease release), evidence (bundle), tracing, redaction, config.

Must not
    Decide *how* to fix the problem. Resume automatically without an operator signal.
"""
