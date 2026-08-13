"""Deprecated. Moved to :mod:`symbolic_ai_core.asymptotics`.

Kept as a re-export so that code written against the old path keeps working, and
because `RESEARCH_LOG.md` cites this path for the mutual-information and
effective-rank numbers. Import from :mod:`symbolic_ai_core.asymptotics` in
anything new; this shim re-exports the module's ``__all__`` and nothing private.
"""

from __future__ import annotations

from symbolic_ai_core.asymptotics import *          # noqa: F401,F403
from symbolic_ai_core.asymptotics import __all__    # noqa: F401
