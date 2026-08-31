"""redaction — sensitivity-driven scrubbing (ADR-011).

Purpose
    Never persist secrets or raw PII into artifacts, traces, intervention bundles, or
    evidence. Redaction is driven first by the *declared* sensitivity of a param/output;
    regex/entropy patterns are only a backstop for undeclared leakage.

Public interface (to be implemented)
    scrub(value: Any, sensitivity: Sensitivity | None) -> Any
    scrub_mapping(d: Mapping, schema: dict[str, Sensitivity]) -> dict
    scrub_text(s: str) -> str                 # backstop patterns only
    Sensitivity        -- Enum: SECRET | PII | FINANCIAL | PUBLIC

Depends on
    config.redaction rules. Nothing else in cua (leaf module).

Must not
    Be optional on any write path. Log the pre-scrub value even at DEBUG.
"""
