"""The architectures under comparison — two families, one interface.

**Neural**, trained by gradient descent — *off by default*, see
``NEURAL_ENABLED`` below::

    gru  transformer  rgt  tpr  hrr  ndr

**Rule-based**, fitted by counting, parsing, searching and proving::

    ngram  ctw          counting and Bayesian context mixing
    syllogism  symbolalg   parsing into logical form
    synth  ilp          search over programs and over clauses
    ruleinduce  brill    rule induction, by partition and by correction
    evidence  analogy    retrieval, by concept and by structure

Both answer to :class:`~symbolic_ai_models.models.base.Model`: a batch in, logits over
the shared vocabulary out. A decision list and a transformer are therefore
scored by the same cross-entropy against the same floors and appear in the same
table, which is the only way the comparison this repo is for can be made.

Importing this package registers everything, so ``model_names()`` is complete
after ``import symbolic_ai_models.models`` and a new architecture becomes available by
being imported below — there is no separate list to keep in sync.
"""

import os

from .base import Model, ModelConfig, ModelOutput, NeuralModel, SymbolicModel
from .registry import REGISTRY, build, get, model_names, register
from .symbolic import ABSTAIN, GraphView, RuleBasedModel, Votes

# Registration happens at import; the noqa keeps a linter from tidying away the
# only thing these imports are for.
from . import evidence, ngram, ruleinduce, syllogism, symbolalg, synth  # noqa: F401
from . import analogy, brill, ctw, grammar, ilp, routes_model, workspace  # noqa: F401

#: The neural half is **not registered by default**. It is not the subject of
#: this repo — the symbolic models are — and it is the only thing here that
#: wants a GPU, which on a shared machine means competing with whatever real
#: training is running. Nothing is deleted: the six architectures, the shared
#: encoder and their tests are all still here and still work.
#:
#: Set ``SYMBOLIC_AI_MODELS_NEURAL=1`` to register them, for a run where the
#: neural/symbolic comparison is actually the point and the device is free.
NEURAL_ENABLED = os.environ.get("SYMBOLIC_AI_MODELS_NEURAL", "") not in ("", "0")

if NEURAL_ENABLED:  # pragma: no cover - opt-in path
    from . import gru, hrr, ndr, rgt, tpr, transformer        # noqa: F401

__all__ = ["Model", "NeuralModel", "RuleBasedModel", "SymbolicModel",
           "ModelConfig", "ModelOutput", "GraphView", "Votes", "ABSTAIN",
           "REGISTRY", "build", "get", "model_names", "register",
           "NEURAL_ENABLED"]
