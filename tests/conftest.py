"""Shared pytest fixtures.

Populated during the build phases (MODULES.md). Planned fixtures:
    settings()            -- Settings loaded from config/default.yaml
    fake_surface()        -- in-memory Surface for deterministic locator/replay tests
    sample_capability()   -- a hand-written Capability fixture for schema + replay tests
    recorded_run()        -- a canned DiscoveryResult for recorder tests
"""
