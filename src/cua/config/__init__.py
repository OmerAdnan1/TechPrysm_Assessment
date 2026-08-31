"""config — typed settings + tenant overlay loading.

Purpose
    Load config/default.yaml (and an optional config/tenants/<id>.yaml overlay) plus
    environment variables into a single frozen, validated Settings object. One source
    of truth for allowlist, risk policy, redaction rules, timeouts, model id.

Public interface (to be implemented)
    Settings            -- pydantic model: allowlist, risk_policy, redaction, run, replay, session
    load_settings(tenant: str | None = None) -> Settings
    Settings.for_tenant(tenant_id) -> Settings      # merge sparse overlay

Depends on
    pydantic, pydantic-settings, pyyaml. No other cua module.

Must not
    Read secrets from anywhere but the environment. Be imported for its side effects.
"""
