"""Readouts: what a model's graph-valued output is read *as*.

Importing this module is what registers them, exactly as importing
:mod:`symbolic_ai_models.models` registers the models. The protocol, the
registry and the reasoning live in :mod:`symbolic_ai_core.readout`; this package
holds the ones that consume a
:class:`~symbolic_ai_models.models.base.ModelOutput`, and
:mod:`symbolic_ai_agents.readouts` holds the one that reads the same output as
an action.
"""

from __future__ import annotations

from symbolic_ai_core.readout import (CHANNELS, NODE, REGISTRY, SITE, SYMBOL,
                                      TYPE, Readout, build, readout_names,
                                      register)

from . import site as _site        # noqa: F401  (registration side effect)
from . import symbol as _symbol    # noqa: F401

__all__ = ["Readout", "REGISTRY", "build", "readout_names", "register",
           "CHANNELS", "SYMBOL", "TYPE", "NODE", "SITE", "default_readouts"]


def default_readouts(**kwargs) -> dict[str, Readout]:
    """The readouts a run scores unless it says otherwise.

    All three, always. A run that scored only the readout its model was written
    for would be an experiment designed by the model — which is how "one readout
    is an assumption" stops being visible. A model emitting nothing on a channel
    is simply absent from that column, so the cost of asking is a missing cell
    rather than a wrong number.
    """
    from symbolic_ai_core.readout import REGISTRY as R
    out: dict[str, Readout] = {}
    for name in ("symbol", "node", "site"):
        cls = R.get(name)
        try:
            out[name] = cls(**kwargs)     # type: ignore[call-arg]
        except TypeError:
            out[name] = cls()
    return out
