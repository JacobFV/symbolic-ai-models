"""Flood's binding of the shared surface scrambles.

The transforms live in :mod:`symbolic_ai_generators.scramble` -- all three
domains declare their own structurally identical ``Observation``/``Span``, so
they work by duck typing. This module supplies flood's section labels and keeps
the import path the flood tests and scripts already use.

Why they exist: `read_signature` branches on ``pi == 0``, ``pi == 1``,
``pi == 2``, ``pi == 3``, so the milestone's "signature reader 1.000, zero reader
loss" was a reader that knows the generator's five-paragraph template by
**index**. `unsaturate` takes the headings and the order away; `interleave` takes
grouping too.
"""

from __future__ import annotations

from typing import Any

from symbolic_ai_generators.scramble import interleave as _interleave
from symbolic_ai_generators.scramble import unsaturate as _unsaturate

#: The section labels ``render_observation`` writes. Two shapes: standalone
#: spans ("ROAD NETWORK.") and, for the first paragraph, a label glued to the
#: front of a sentence that also carries content.
HEADINGS = ("SITUATION REPORT.", "ROAD NETWORK.", "OVERNIGHT.",
            "LOADING AND LIMITS.", "TASKING.")

__all__ = ["HEADINGS", "unsaturate", "interleave"]


def unsaturate(obs: Any, *, seed: int | None = None,
               drop_headings: bool = True, shuffle: bool = True) -> Any:
    """No section labels, no fixed paragraph order. Alignment preserved.

    Paragraph level deliberately, not sentence level: every pronoun in this
    surface resolves inside its own paragraph, so reordering paragraphs keeps
    every sentence **true**. See `interleave` for the stronger transform.
    """
    return _unsaturate(obs, headings=HEADINGS, seed=seed,
                       drop_headings=drop_headings, shuffle=shuffle)


def interleave(obs: Any, *, seed: int | None = None) -> Any:
    """Every sentence in one paragraph, seeded order. Grouping destroyed."""
    return _interleave(obs, seed=seed)
