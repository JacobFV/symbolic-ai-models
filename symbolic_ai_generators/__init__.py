"""World generators: latent worlds that can be rendered into several surfaces.

A generator here produces a :class:`~symbolic_ai_core.world.WorldSnapshot` and
whatever surfaces are asked of it — prose, a term graph, a structured target —
from **one** latent world and one address. That is what makes it possible to
test a reasoner without confounding it with a parser: the oracle reading of the
text is available by construction, so parser quality and reasoner quality can be
measured apart.
"""

from __future__ import annotations

__all__: list[str] = []
