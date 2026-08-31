"""recorder — distill a successful discovery run into a Capability artifact.

Purpose
    The transcript -> capability compiler. Takes the executed steps + per-step
    Observations and produces a clean, parameterized Capability: drop retries and
    dead-ends, lift concrete values (member id, amounts) into typed inputs, infer
    outputs from ReadValue steps, compile each target via cua.locators, set the
    checkpoint from the goal-completion assertion.

Public interface (to be implemented)
    distill(result: DiscoveryResult, goal: str, hints: RecorderHints) -> Capability
    RecorderHints      -- optional operator guidance: which values are params, output names
    propose_params(steps, observations) -> list[ParamSpec]   # heuristic + confirmable

Depends on
    agent.DiscoveryResult, artifact, locators, actions, redaction, config.

Must not
    Call the LLM. Keep the raw model messages in the artifact (only provenance metadata).
"""
