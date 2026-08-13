"""Deprecated. Moved to :mod:`symbolic_ai_core.shortcuts`.

Kept as a re-export so that code written against the old path keeps working —
``symbolic_ai_agents`` on the ``omegaclaw`` branch imports ``SHORTCUTS``,
``Shortcut`` and ``shortcut_table`` from here. Import from
:mod:`symbolic_ai_core.shortcuts` in anything new; this shim re-exports the
module's ``__all__`` and nothing private.
"""

from __future__ import annotations

from symbolic_ai_core.shortcuts import *          # noqa: F401,F403
from symbolic_ai_core.shortcuts import __all__    # noqa: F401
