"""perception — normalized Observation builder.

Purpose
    Turn a Surface's RawPerception into a compact, model-friendly Observation: the list
    of interactive nodes as {ref, role, accessible_name, value, state, bbox}, a screenshot
    reference, page meta (url, title), and dialog state. This is where "the agent never
    reasons over raw HTML" (R2) is enforced — HTML never appears in an Observation.

Public interface (to be implemented)
    Observation        -- model handed to the LLM and to replay's checkpoint checks
    Node               -- one interactive element with a per-observation `ref` id
    build_observation(raw: RawPerception) -> Observation
    diff(prev: Observation, curr: Observation) -> ObservationDelta   # progress detection

Depends on
    surface (types only), actions.Condition (for evaluate()), tracing.

Must not
    Include raw markup or full DOM. Persist anything (that's tracing/evidence).
"""
