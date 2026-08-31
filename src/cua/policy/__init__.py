"""policy — safety guardrails (ADR-010). Enforcement, not prompting.

Purpose
    Decide whether a proposed Action is permitted, and with what disposition. Two
    concerns: (1) the allowlist — origins, routes, action types; (2) the risk class —
    safe/reversible proceed freely; risky/irreversible are blocked, gated on
    confirmation, or flagged per config.

Public interface (to be implemented)
    PolicyDecision     -- Allow | Flag(reason) | Block(reason) | NeedsHuman(reason)
    check(action: Action, obs: Observation, cfg: Settings) -> PolicyDecision
    classify_risk(action: Action, obs: Observation, cfg: Settings) -> RiskClass

Depends on
    actions, perception.Observation, config. Called from cua.surface.perform() AND from
    cua.agent before it acts (defence in depth).

Must not
    Live in the prompt. Be advisory only — a Block must actually stop the action.
"""
