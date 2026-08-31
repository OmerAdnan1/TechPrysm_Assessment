"""surface — the perceive/act adapter boundary (the heterogeneity seam, ADR-005).

Purpose
    Everything above this line (agent, perception, replay) is surface-agnostic. A
    Surface knows how to take a raw perception of *some* UI and how to perform a typed
    Action against it. Swapping web -> legacy web -> desktop is a new Surface, not a
    rewrite.

Public interface (to be implemented)
    Surface(Protocol)
        open() / close()
        current_url() -> str
        raw_perception() -> RawPerception     # nodes + screenshot bytes + dialogs + meta
        perform(action: Action) -> ActionResult
        snapshot(reason: str) -> SnapshotRef   # screenshot + serialized a11y tree to disk
    RawPerception, ActionResult, SnapshotRef   -- plain models
    WebSurface(Surface)      -- Playwright sync; accessibility snapshot + CDP screenshot
    DesktopSurface(Surface)  -- documented stub; raises NotImplementedError (REPORT S4)

Depends on
    playwright (WebSurface only), actions, config.allowlist (perform() is gated here).

Must not
    Expose Playwright objects to callers. Make decisions about *what* to do.
"""
