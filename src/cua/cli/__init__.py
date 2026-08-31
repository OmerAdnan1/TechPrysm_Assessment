"""cli — entry points (Typer app; thin orchestration only).

Verbs
    cua discover  --goal "..." --target parabank [--tenant parabank-demo]
        run the LLM discovery loop; on success write artifacts/<id>.json + evidence/

    cua replay <capability_id> --param member_id=12345 [--tenant ...] [--inject <fault>]
        deterministic replay; prints a typed Result; writes evidence/ (+ failure bundle)

    cua operator {list | take <id> | resume <id> --note "..."}
        human-in-the-loop handoff over the live session

    cua catalog {list | show <id> | run <id> --param k=v}
        name-addressable capability invocation (thin wrapper over replay)

    cua stability <capability_id> --runs N
        replay N times, report a flakiness/drift signal (ADR-014)

    cua session {start | status | stop}
        manage the Session Host process

Depends on
    typer, and each feature module. No business logic lives here.
"""
