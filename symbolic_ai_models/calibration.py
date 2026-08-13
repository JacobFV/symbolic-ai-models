"""Deprecated. Moved to :mod:`symbolic_ai_core.calibration`.

Kept as a re-export so that code written against the old path keeps working —
``symbolic_ai_agents`` on the ``omegaclaw`` branch imports ``CalibrationReport``
and ``calibrate`` from here. Import from :mod:`symbolic_ai_core.calibration` in
anything new; this shim re-exports the module's ``__all__`` and nothing private.
"""

from __future__ import annotations

from symbolic_ai_core.calibration import *          # noqa: F401,F403
from symbolic_ai_core.calibration import __all__    # noqa: F401
