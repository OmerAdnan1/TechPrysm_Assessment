"""outcomes — the result taxonomy and its detectors (ADR-008).

Purpose
    Make "no such member" a first-class answer, not a crash. A typed union the caller
    pattern-matches on, plus pluggable detectors that classify an Observation / action
    error / HTTP status into one of the branches.

Public interface (to be implemented)
    Result             -- discriminated union:
        Success(outputs: dict)
        BusinessOutcome(code: str, detail: str, observed_at_step: int)
        Recoverable(condition: str, action_taken: str, retried: int)   # internal; rolled into Success/HardFailure
        HardFailure(step: int, expected: str, observed: str, evidence_ref: str, kind: HardFailureKind)
    HardFailureKind    -- LOCATOR_UNRESOLVED | CHECKPOINT_FAILED | UNEXPECTED_DIALOG | TIMEOUT | POLICY_BLOCK | SURFACE_ERROR
    classify(ctx: StepContext, cfg: Settings) -> Result | None    # None = nothing anomalous
    RecoverableHandler -- reauthenticate | wait_retry | dismiss_known_interstitial | reload_and_retry

Depends on
    perception.Observation, config (detector rules), actions, redaction.

Must not
    Contain surface-specific selectors. Decide to escalate (replay owns that).
"""
