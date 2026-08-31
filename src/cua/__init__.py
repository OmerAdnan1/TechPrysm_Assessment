"""cua — Computer-Use Automation.

An LLM discovers how to accomplish a goal on a live UI once (observe -> decide -> act),
the run is distilled into a typed, versioned Capability artifact, and that artifact is
replayed deterministically with no model in the decision loop.

Package layout mirrors the component map in ARCHITECTURE.md. Nothing here has behaviour
yet: every submodule ships a contract docstring only. Build order is in MODULES.md.
"""

__version__ = "0.1.0"
