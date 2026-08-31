"""llm — Anthropic client wrapper for the discovery loop (ADR-004).

Purpose
    The only place that talks to a model. Hand-rolled tool-calling; no agent framework.
    Turns an Observation + goal + history into the next typed Action (or a "goal met" /
    "dead end" signal), with the model constrained to the closed action vocabulary via
    tool schemas.

Public interface (to be implemented)
    Decision           -- Act(action, rationale) | GoalMet(evidence) | DeadEnd(reason)
    decide(goal: str, obs: Observation, history: list[Turn], allowed: AllowedActions) -> Decision
    LlmConfig          -- model id, max tokens, temperature, retry policy

Depends on
    anthropic, actions (tool schemas generated from the Action union), config.

Must not
    Enforce policy (that is cua.policy). Touch a Surface. Be reachable from cua.replay.
"""
