"""Parsers, in the only sense that admits an exact score: ``str -> TermGraph``.

``langcurriculum`` renders every episode from a typed term and hands the term
over, so text and structure come out of one seed and the mapping between them is
known exactly. That makes recovering the graph from the text a fully supervised
problem with no annotator, no judge, and an unbounded supply of fresh episodes —
which is a rarer thing than it sounds, and is the reason this package exists
separately from the parser layer in ``symbolic_ai_models`` (whose codomain is
word classes, not structure; see :mod:`symbolic_ai_parsers.base`).

Read :mod:`symbolic_ai_parsers.scoring` before quoting a number from here. There
are ten metrics, they do not agree, and a parser named without one of them is
not a result.

There are two evaluation protocols and they answer different questions.
:mod:`symbolic_ai_parsers.evaluate` fits on English and scores four languages —
"did what it learned in English transfer".
:mod:`symbolic_ai_parsers.polyglot` fits on a mixture of 46 and scores languages
held out of it — "can one rule set be fitted on many languages at once and still
work on one it was never shown". A number from either is meaningless without
saying which.
"""

from .base import REGISTRY, Parser, base_name, build, get, parser_names, register
from .classes import ClassMap
from .evaluate import LANGUAGES, ParserReport, evaluate_parser, run_sweep
from .floors import ConstantFloor, fit_floor
from .grammar import Grammar, Rule
from .lexicon import Lexicon
from .polygrammar import PolyGrammar
from .scoring import METRICS, SHORT, Scores, macro_scores, score_graph
from .treebank import Treebank

from . import parsers  # noqa: F401  (registers them)

__all__ = ["Parser", "REGISTRY", "register", "get", "build", "parser_names",
           "base_name", "METRICS", "SHORT", "Scores", "score_graph",
           "macro_scores", "ConstantFloor", "fit_floor", "Lexicon", "Treebank",
           "Grammar", "Rule", "ParserReport", "evaluate_parser", "run_sweep",
           "LANGUAGES", "ClassMap", "PolyGrammar"]
