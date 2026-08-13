"""Deprecated. Moved to :mod:`symbolic_ai_core.invariance`.

Kept as a re-export so that code written against the old path keeps working.
Import from :mod:`symbolic_ai_core.invariance` in anything new.

``label_accuracy`` is named explicitly because it is missing from that module's
``__all__`` and always was — ``train.py`` and three test files import it, so a
shim that re-exported only ``__all__`` would be a silently partial one. The
omission is left alone here rather than fixed: adding a name to ``__all__``
changes what ``import *`` means, which is an API change and not this refactor's
business.
"""

from __future__ import annotations

from symbolic_ai_core.invariance import *              # noqa: F401,F403
from symbolic_ai_core.invariance import __all__        # noqa: F401
from symbolic_ai_core.invariance import label_accuracy  # noqa: F401
