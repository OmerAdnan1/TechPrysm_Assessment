"""actions — the closed, typed action vocabulary.

Purpose
    The finite set of things anything (LLM agent or replay engine) may ask a Surface to
    do. Free-form actions are not representable. Each action carries an intrinsic
    risk_class; cua.policy may upgrade it via rules.

Public interface (to be implemented)
    RiskClass          -- Enum: SAFE_REVERSIBLE | RISKY_IRREVERSIBLE
    Action             -- discriminated union (pydantic) over:
        Navigate(url)
        Click(target)
        TypeText(target, text, sensitivity)
        SelectOption(target, value | label)
        PressKey(target, key)
        ReadValue(target, name)            -- produces a named output
        WaitFor(condition)
        AssertCondition(condition)         -- checkpoint primitive
        DismissDialog(decision)
    Condition          -- typed predicate over an Observation (text_present, url_matches,
                          node_visible, node_value_equals, dialog_open, ...)

Depends on
    pydantic only. locators.TargetSpec for `target` (type-only import).

Must not
    Contain execution logic. Reference Playwright or any Surface implementation.
"""
