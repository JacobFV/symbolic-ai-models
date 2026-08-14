"""Induced word classes: the repair the cross-language finding asks for.

``cky-001`` keeps 0.06 of its English bracket F1 in Chinese, and the cause is
one line — :meth:`ClauseSample.categories` puts **the literal word** at every
non-argument position, so ``PRED[outranks] -> ARG "outranks" ARG`` is a rule
about the string ``outranks`` and translating the frame invalidates it. A
lookup keyed on punctuation (``template-002``) keeps 0.46, which is the
embarrassing part: the chart's extra machinery is more language-bound than no
machinery at all.

What a class has to be here
---------------------------

Not "words with similar distributions" in general — the corpus makes something
sharper available. Every episode renders from a term, the term is identical in
every language, and the treebank already recovers *which clause realises which
predicate*. So the frame words of a clause are, by construction, the words that
language uses to say that predicate. A class is therefore countable rather than
clustered:

    class(w) = the predicate w most often frames, if it frames one in
               particular; otherwise the generic frame class.

which makes ``outranks``, ``排名高于`` and ``üstündedir`` one symbol, and makes
one production cover all three languages. No similarity threshold, no embedding,
no free parameter beyond the two below.

Two tiers, and why the split is not cosmetic
--------------------------------------------

Some surface material survives translation: punctuation, digits, and the
untranslated frame words this corpus is full of (``opt_b``, ``schemas``). Those
should stay **literal** — they are the one part of the frame a parser can rely
on in a language it has never seen, and abstracting them away throws it out.
The test for "survives translation" is measured, not guessed: a token is
*shared* if it occurs in at least half of the training languages.

Everything else is *translated* material and gets abstracted. So the RHS of a
production is a mixture of ``ARG``, literal shared tokens, and class symbols —
which is exactly the "one rule set, selectively applied" shape, with the
selection done by what the token is rather than by which language the document
is in.

For a **held-out** language, every translated frame word is out of vocabulary.
That is the case the whole design is for: the shared tier still matches
literally, and the unknown tokens are matched against class symbols as
wildcards (see :mod:`symbolic_ai_parsers.polygrammar`). A literal grammar has
nothing to match at all there, which is what the 0.06 was.

The controls that come with it
-------------------------------

:data:`MODES` names three, all registered as parsers so the sweep prints them
against the same floors:

``classes``
    the scheme above.
``one``
    identical, except every abstracted token gets the *same* class symbol. If
    this matches ``classes``, the class identities carry nothing and the result
    is a positional template — ``template-002``'s mechanism wearing a chart
    parser's name — and has to be reported that way.
``literal``
    the old behaviour, so that abstraction is isolated from segmentation,
    mixture training and conditioning, which move at the same time.
"""

from __future__ import annotations

import collections
import math
from dataclasses import dataclass, field
from typing import Sequence

from .treebank import ClauseSample

__all__ = ["ClassMap", "MODES", "SHARED_SHARE", "SPECIFICITY", "GENERIC"]

#: A token is *shared* — kept literal — if it occurs in at least this share of
#: the training languages. Half, chosen because it is the only value with an
#: argument for it ("more languages than not"), and not swept.
SHARED_SHARE = 0.5

#: A translated token gets its own class if that share of its occurrences frame
#: one predicate. Half again, same reasoning: a plurality is not enough, a
#: majority is. Below it the token is generic frame material.
SPECIFICITY = 0.5

#: The class every unspecific translated token falls into.
GENERIC = "C:*"

MODES = ("classes", "one", "literal")


@dataclass
class ClassMap:
    """``token -> category symbol``, plus what a parser needs for a wildcard."""

    of: dict[str, str] = field(default_factory=dict)
    #: log prior of each class symbol among abstracted frame occurrences. Used
    #: to price an unknown token against a class it might belong to.
    class_logp: dict[str, float] = field(default_factory=dict)
    mode: str = "classes"
    n_languages: int = 0

    def category(self, token: str) -> str | None:
        """The symbol ``token`` writes in a right-hand side, or ``None`` if it
        was never seen as frame material."""
        return self.of.get(token)

    def n_classes(self) -> int:
        return len(self.class_logp)

    def n_literal(self) -> int:
        return sum(1 for v in self.of.values() if not v.startswith("C:"))

    @classmethod
    def induce(cls, samples: Sequence[ClauseSample], languages: Sequence[str],
               *, mode: str = "classes") -> "ClassMap":
        if mode not in MODES:
            raise ValueError(f"unknown class mode {mode!r}; expected {MODES}")
        langs = sorted(set(languages)) or ["?"]
        cut = max(2, math.ceil(SHARED_SHARE * len(langs)))
        if len(langs) < 2:
            cut = 1                       # monolingual: everything is "shared"

        heads: dict[str, collections.Counter] = collections.defaultdict(
            collections.Counter)
        seen_in: dict[str, set[str]] = collections.defaultdict(set)
        total: collections.Counter = collections.Counter()
        for s, lang in zip(samples, languages or [""] * len(samples)):
            args = {i for i, _ in s.arg_slots}
            for i, tok in enumerate(s.tokens):
                if i in args:
                    continue
                heads[tok][s.head] += 1
                seen_in[tok].add(lang)
                total[tok] += 1

        out = cls(mode=mode, n_languages=len(langs))
        abstracted: collections.Counter = collections.Counter()
        for tok in sorted(total):
            if mode == "literal" or len(seen_in[tok]) >= cut:
                out.of[tok] = tok
                continue
            if mode == "one":
                sym = GENERIC
            else:
                head, n = max(sorted(heads[tok].items()), key=lambda kv: kv[1])
                sym = (f"C:{head}" if n >= SPECIFICITY * total[tok] else GENERIC)
            out.of[tok] = sym
            abstracted[sym] += total[tok]

        denom = sum(abstracted.values()) or 1
        out.class_logp = {s: math.log(c / denom)
                          for s, c in sorted(abstracted.items())}
        return out
