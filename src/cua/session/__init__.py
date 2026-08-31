"""session — Session Host + control lease (R11/R12 seam, ADR-012).

Purpose
    Own the live Surface as an independent, addressable object that outlives any single
    runner, and arbitrate a single-writer control lease over it. "Who is in control" is
    queryable state, not an implicit assumption.

Public interface (to be implemented)
    ControlLease       -- { owner: AUTOMATION | HUMAN, holder_id: str, since: dt, reason: str | None }
    SessionHost        -- long-lived process; owns one Surface; exposes a localhost control API:
        POST /sessions                 -> create (launch Surface)
        GET  /sessions/{id}            -> state + current lease
        POST /sessions/{id}/lease      -> acquire (owner, holder, reason); 409 if held
        DELETE /sessions/{id}/lease    -> release
        POST /sessions/{id}/lease/force-> operator override
    SessionClient      -- httpx wrapper used by agent / replay / operator
    perform_guard(session_id, action) -- rejects if caller is not the lease owner

Depends on
    surface, fastapi + uvicorn (host), httpx (client), config.session, tracing.

Must not
    Make automation decisions. Let two holders write concurrently.
"""
