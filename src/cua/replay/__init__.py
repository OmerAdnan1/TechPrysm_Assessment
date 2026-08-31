"""replay — deterministic executor (the production path; no LLM).

Purpose
    Given a Capability + typed input params, walk the steps: resolve target -> perform
    action -> verify expectation. Classify every anomaly through cua.outcomes. Verify
    the checkpoint. Return a typed ReplayResult with declared outputs, or a business
    outcome, or a debuggable hard failure. Emit a replay trace; on failure assemble a
    rich evidence bundle.

Public interface (to be implemented)
    ReplayRequest      -- { capability: Capability, params: dict, tenant: str | None }
    ReplayResult       -- see cua.outcomes.Result (Success | BusinessOutcome | Recoverable-rolled-up | HardFailure)
    replay(req: ReplayRequest) -> ReplayResult

Depends on
    artifact, locators, actions, surface, outcomes, policy, redaction, session
    (acquires the automation lease), escalation (on unrecoverable stuck), evidence, tracing.

Must not
    Import cua.llm or cua.agent. Proceed past an unclassified anomaly.
"""
