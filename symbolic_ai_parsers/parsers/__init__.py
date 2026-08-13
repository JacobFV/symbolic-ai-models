"""Every parser, one package each. Importing this registers all of them.

The layout mirrors ``symbolic_ai_models/models/``: a directory per approach,
**named for the row it produces, version suffix and all**, so the tree cannot
drift away from the registry. A family that shares machinery gets an unversioned
skeleton package beside its variants — ``template/`` here, as ``omegaclaw/``
there — and the skeleton registers nothing.

The parsers, by what they actually do:

*Controls, which is most of the value of having them*::

    prior_001       one fixed training graph; the floor, as a row
    bracket_001     document layout as a record; written down, nothing learned
    legacy_001      symbolic_ai_models.parsers' facts, lifted into this codomain
    retrieve_001    nearest training prompt, graph copied; no parsing at all

*Template induction — recognise the lesson, refill its slots*::

    template_001    layout lookup      (the refuted one; kept, not edited)
    template_002    shape lookup       (the correction)
    template_lex    layout lookup, seeded lexicon
    template_seeded word lookup, seeded lexicon

*Classical, compositional — build the graph rather than retrieve one*::

    cky_001         CKY over a PCFG induced from an aligned treebank
    lr_001          SLR(1) shift-reduce over the same grammar
    shiftreduce_001 greedy transition-based, averaged-perceptron oracle

The last three are the only parsers here that *compose* an answer, and they all
read one grammar out of :mod:`symbolic_ai_parsers.grammar`, so the comparison
between them is a comparison of parsing strategies rather than of grammars.
"""

from . import bracket_001, legacy_001, prior_001, retrieve_001  # noqa: F401
from . import template_001, template_002, template_lex, template_seeded  # noqa: F401
from . import cky_001, lr_001, shiftreduce_001  # noqa: F401

__all__ = [
    "bracket_001", "legacy_001", "prior_001", "retrieve_001",
    "template_001", "template_002", "template_lex", "template_seeded",
    "cky_001", "lr_001", "shiftreduce_001",
]
