"""locators — element identification (record time) and resolution (replay time).

The determinism seam (ADR-006). A TargetSpec is an ordered list of strategies stored
as data in the artifact, so a human reviewer can read how each control is found and a
tenant overlay can override one strategy without re-recording.

Public interface (to be implemented)
    Strategy           -- union: RoleName | LabelAnchored | VisibleText | Structural | CssOrTestId
    TargetSpec         -- { strategies: [Strategy], notes: str, recorded_from: NodeFingerprint }
    compile_target(node: Node, obs: Observation) -> TargetSpec
        # build the ordered strategy list + robustness notes from a picked node
    resolve(spec: TargetSpec, surface: Surface, timeout_s: float) -> Resolution
        # try strategies in order, with waiting; report which matched + candidate count
    Resolution         -- Resolved(handle, strategy_used, candidates) | Unresolved(tried, reason)

Depends on
    perception.Node/Observation, surface (types), actions (no), config.replay timeouts.

Must not
    Fall back to raw XPath brittleness silently — every attempt is recorded in Resolution
    for the drift signal (ADR-014).
"""
