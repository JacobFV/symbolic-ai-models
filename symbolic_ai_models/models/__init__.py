"""The architectures under comparison — two families, one interface.

**Neural**, trained by gradient descent::

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

from .base import Model, ModelConfig, ModelOutput, NeuralModel, SymbolicModel
from .registry import REGISTRY, build, get, model_names, register
from .symbolic import ABSTAIN, GraphView, RuleBasedModel, Votes

# Registration happens at import; the noqa keeps a linter from tidying away the
# only thing these imports are for.
from . import gru, hrr, ndr, rgt, tpr, transformer            # noqa: F401
from . import evidence, ngram, ruleinduce, syllogism, symbolalg, synth  # noqa: F401
from . import analogy, brill, ctw, grammar, ilp, routes_model, workspace  # noqa: F401

__all__ = ["Model", "NeuralModel", "RuleBasedModel", "SymbolicModel",
           "ModelConfig", "ModelOutput", "GraphView", "Votes", "ABSTAIN",
           "REGISTRY", "build", "get", "model_names", "register"]
