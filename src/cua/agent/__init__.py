"""agent — the discovery loop (LLM in the loop; the one place a model decides).

Purpose
    Run observe -> decide -> act against a live Surface until the goal is met or a
    stopping condition fires (max steps, wall-clock timeout, dead-end, no-progress).
    Emits a discovery trace and, on success, the ordered list of executed steps +
    per-step Observations for the recorder to distill.

Public interface (to be implemented)
    DiscoveryRequest   -- { goal: str, surface: Surface, tenant: str | None }
    DiscoveryResult    -- Completed(steps, observations, run_id) | Stopped(reason, run_id)
    StopReason         -- MAX_STEPS | RUN_TIMEOUT | DEAD_END | NO_PROGRESS | POLICY_BLOCK | ESCALATED
    run_discovery(req: DiscoveryRequest) -> DiscoveryResult

Depends on
    perception, llm, actions, policy, surface, tracing, escalation (on stuck), config.

Must not
    Write the artifact (that is cua.recorder). Bypass cua.policy on any action.
"""
