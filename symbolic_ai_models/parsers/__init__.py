"""Parsers: text in, structure out — decoupled from whatever reasons over it.

A reasoner names the parser it wants and must tolerate any of them, so
``parser x reasoner`` is a matrix rather than a single fused choice. Importing
this package registers every parser.

Parsers are scored against the term the curriculum generated the text from; see
:mod:`symbolic_ai_models.parsers.evaluate`, which is exact because the ground
truth is the generator's own structure rather than anyone's annotation.
"""

from .base import (REGISTRY, Constituent, ParseResult, Parser, build, get,
                   parser_names, register)
from .evaluate import ParserReport, evaluate_parser, true_roles

from . import none  # noqa: F401
from . import categorical, regex_parser  # noqa: F401
from . import chunker, induced  # noqa: F401

__all__ = ["Parser", "ParseResult", "Constituent", "REGISTRY", "build", "get",
           "parser_names", "register", "ParserReport", "evaluate_parser",
           "true_roles"]
