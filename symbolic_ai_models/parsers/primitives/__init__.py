"""Parsing primitives, shared by the parsers and by the reasoners built on them.

These four modules — a symbol algebra, a clause splitter, a morphological
lexicon and a categorical fragment — arrived welded to the models that first
used them, which put them in ``models/``. That was the wrong layer and it showed
up as a cycle: ``parsers`` imported ``models`` for the parsing code while
``models`` imported ``parsers`` for its parser, and only a function-local import
kept it working.

They live here now because turning text into structure is what a parser does.
The dependency runs one way — ``data`` -> ``parsers.primitives`` -> ``parsers``
-> ``models`` — and the model-side import is an ordinary top-level one again,
which is the check that the layering is real rather than asserted.
"""

from . import clauses, lexicon, symbols, syllogistic  # noqa: F401

__all__ = ["clauses", "lexicon", "symbols", "syllogistic"]
