"""Deprecated. Moved to :mod:`symbolic_ai_core.data.fingerprint`.

See this package's ``__init__`` for why the old path is kept. The command-line
entry point is now ``python -m symbolic_ai_core.data.fingerprint``; this shim is
for imports only.
"""

from __future__ import annotations

from symbolic_ai_core.data.fingerprint import *          # noqa: F401,F403
from symbolic_ai_core.data.fingerprint import __all__    # noqa: F401
