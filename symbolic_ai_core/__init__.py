"""The shared harness: episode types, the versioned registry, floors, calibration.

Three packages in this repo evaluate different things against the same
curriculum — ``symbolic_ai_models`` (models), ``symbolic_ai_parsers``
(``str -> TermGraph``), and ``symbolic_ai_agents`` on the ``omegaclaw`` branch — and
they were sharing that machinery by importing it out of ``symbolic_ai_models``.
That made the models package three things wearing one name, and it made the
sibling packages depend on the models package for types that have nothing to do
with models: 24 of the 25 cross-package imports were ``Episode``, ``TermGraph`` and
``SymbolTokenizer``.

Why not fold this into ``symbolic_ai_data``
-------------------------------------------

``symbolic_ai_data`` is ``langcurriculum`` **vendored byte for byte**, and
:mod:`symbolic_ai_data._vendor` states that it is the only file in that package
written here. ``tests/test_vendored_generator.py`` enforces that claim: it walks
every ``.py`` under the package, subtracts ``_vendor.ADDED``, and asserts the
remainder is upstream's. Putting the harness-side ``data/`` in there would mean
either growing ``ADDED`` until "is this still upstream?" stops being answerable,
or having the vendoring tests audit our own code as though it were upstream.

So the split is by *authorship and direction*, not by subject matter:
``symbolic_ai_data`` generates and is upstream's; ``symbolic_ai_core`` reads what
it generates and is ours. ``symbolic_ai_core.data`` depends on
``symbolic_ai_data``; nothing depends the other way.

What belongs here
-----------------

Something earns a place here when it has more than one consumer, or when it is
plainly not about models. ``report.py``'s comparison table is about model rows
and stayed behind; so did the ``Task`` protocol, which is typed in terms of
``ModelOutput``.
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.1.0"
