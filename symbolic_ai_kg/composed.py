"""Two knowledge sources behind one accessor set, without merging their identities.

WordNet populates the essay generator's ``qualities`` and ``behaviour`` sections
**nowhere**; CSKG populates them and loses composition and substance in exchange.
They are complementary, so a composed source is worth having — and composing them
is where three of this repo's standing rules stop being abstract at once:

**Identity is a claim, not a merge.** ``dog`` in WordNet is a *synset* and ``dog``
in this CSKG projection is a lemma-collapsed concept that already merges senses.
Joining them on an equal lemma is an :class:`~symbolic_ai_core.world.Alignment`
with relation ``possibly_same`` and a stated confidence, and this class records
every join it makes so the claim is inspectable rather than implied.

**CSKG contains WordNet 3.0.** It is a consolidation of seven upstreams and
WordNet is one of them, so an edge present in both sources is **one observation
seen twice**. Every accessor here deduplicates by target lemma and counts what it
dropped; ``duplicate_rate`` is the number that says how much of the composition
was double counting.

**A composed source is an artifact, not a source.** Its licence is the closure
over its parents, which for these two is `share_alike` — CSKG is CC-BY-SA-4.0 and
WordNet is not, and nothing derived from this may be published on WordNet's terms
alone.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

__all__ = ["ComposedGraph", "compose", "ALIGNMENT_RELATION", "ALIGNMENT_METHOD"]

#: What a lemma-equality join is entitled to assert. Not ``exact_match``: a
#: polysemous lemma is one CSKG node and several WordNet synsets, so the two are
#: demonstrably not the same thing for exactly the words that matter most.
ALIGNMENT_RELATION = "possibly_same"
ALIGNMENT_METHOD = "exact lemma equality across a synset source and a "\
                   "lemma-collapsed source"

#: Accessors the composition supplements. Structural ones (``word``, ``pos``)
#: come from the primary alone -- a composed source that took its vocabulary
#: from both would have two node spaces and no way to say which id it meant.
_SUPPLEMENTED = ("hypernyms", "hyponyms", "parts_of", "substances_of",
                 "members_of", "properties_of", "abilities_of", "siblings")


@dataclass
class ComposedGraph:
    """``primary`` supplemented by ``secondary``, joined on lemma.

    Node ids are the **primary's**, always. The secondary is consulted by lemma
    and its results are translated back to primary ids where a lemma matches, so
    nothing downstream ever sees an id from two different spaces.
    """

    primary: Any
    secondary: Any
    name: str = "composed"
    #: primary node -> secondary node, for lemmas present in both
    alignment: dict[int, int] = field(default_factory=dict, repr=False)
    #: lemma -> primary node, for translating the secondary's results back
    _by_word: dict[str, int] = field(default_factory=dict, repr=False)
    #: per accessor, (kept, dropped-as-duplicate)
    _counts: dict[str, list[int]] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        self._by_word = {self.primary.word(i): i for i in range(len(self.primary))}
        sec = {self.secondary.word(i): i for i in range(len(self.secondary))}
        self.alignment = {self._by_word[w]: sec[w]
                          for w in self._by_word.keys() & sec.keys()}
        for acc in _SUPPLEMENTED:
            self._counts[acc] = [0, 0]

    # ---- the primary's own surface -----------------------------------
    def __len__(self) -> int:
        return len(self.primary)

    def word(self, n: int) -> str:
        return self.primary.word(n)

    @property
    def pos(self):
        return self.primary.pos

    # ---- the supplemented accessors ----------------------------------
    def __getattr__(self, name: str) -> Any:
        """Anything not supplemented comes from the primary, unchanged.

        A composed source *is* the primary plus supplements, so `ancestors`,
        `is_a`, `dimension_of` and the rest must behave identically rather than
        raising -- a composed source that supports fewer operations than the one
        it composes is a downgrade wearing a composition's name.
        """
        return getattr(self.primary, name)

    def _accepts(self, accessor: str, key: str) -> bool:
        """Whether the primary's accessor takes this keyword.

        Checked against the **primary**, so the composed source forwards exactly
        what the primary would accept and no more. `hypernyms(n)` takes no
        `inherited`; `parts_of(n, *, inherited)` does, and blanket-forwarding to
        both is a TypeError -- which `essay.gather` swallows, which is how the
        mismatch stayed invisible in the first place.
        """
        import inspect

        cache = self.__dict__.setdefault("_sig_cache", {})
        got = cache.get((accessor, key))
        if got is None:
            try:
                params = inspect.signature(
                    getattr(self.primary, accessor)).parameters
                got = key in params
            except (TypeError, ValueError):            # pragma: no cover
                got = False
            cache[(accessor, key)] = got
        return got

    def _supplement(self, accessor: str, n: int, **kw: Any) -> tuple[int, ...]:
        """Forward **every** keyword through to both sources.

        The first version took only ``(self, n)``. ``essay.gather`` calls its
        accessors as ``acc(topic, inherited=False)`` and swallows a
        ``TypeError`` by retrying without it, so the composed source silently
        returned the **inherited** closure where WordNet returned directly
        stated facts -- and composition coverage read 0.988 against WordNet's
        0.088, which is a bug wearing a result's clothes. A composed source that
        answers a different question from the source it stands beside is worse
        than no composed source.
        """
        kw = {k: v for k, v in kw.items() if self._accepts(accessor, k)}
        own = tuple(getattr(self.primary, accessor)(n, **kw))
        sec_node = self.alignment.get(n)
        if sec_node is None:
            self._counts[accessor][0] += len(own)
            return own
        seen = {self.primary.word(i) for i in own}
        extra: list[int] = []
        dropped = 0
        for i in getattr(self.secondary, accessor)(sec_node, **kw):
            w = self.secondary.word(i)
            if w in seen:
                # The same assertion, reached through two sources. Counting it
                # twice is the composite double-count this whole layer refuses.
                dropped += 1
                continue
            mapped = self._by_word.get(w)
            if mapped is None:
                continue          # the secondary knows a word the primary lacks
            seen.add(w)
            extra.append(mapped)
        self._counts[accessor][0] += len(own) + len(extra)
        self._counts[accessor][1] += dropped
        return own + tuple(extra)

    def duplicate_rate(self, accessor: str | None = None) -> float:
        """Share of reachable assertions that were the same fact seen twice.

        Accumulated over the accessor calls actually made, so it reports what
        the composition *did*, not what it could have done on a full traversal.
        """
        pairs = (self._counts.values() if accessor is None
                 else [self._counts[accessor]])
        kept = sum(k for k, _ in pairs)
        dropped = sum(d for _, d in pairs)
        total = kept + dropped
        return dropped / total if total else 0.0

    def census(self) -> dict[str, Any]:
        return {"name": self.name, "primary": len(self.primary),
                "secondary": len(self.secondary),
                "aligned": len(self.alignment),
                "aligned_share": len(self.alignment) / max(len(self.primary), 1),
                "duplicate_rate": self.duplicate_rate(),
                "per_accessor": {k: {"kept": v[0], "duplicates": v[1]}
                                 for k, v in sorted(self._counts.items())}}

    def alignments(self) -> tuple:
        """The joins, as claims. Not merges, and each one may be wrong."""
        from symbolic_ai_core.world import Alignment

        return tuple(
            Alignment(left=f"wn:{self.primary.word(p)}",
                      right=f"cn:{self.secondary.word(s)}",
                      relation=ALIGNMENT_RELATION, confidence=0.6,
                      method=ALIGNMENT_METHOD)
            for p, s in sorted(self.alignment.items()))


def _bind(accessor: str) -> Callable[..., tuple[int, ...]]:
    def call(self: ComposedGraph, n: int, **kw: Any) -> tuple[int, ...]:
        return self._supplement(accessor, n, **kw)
    call.__name__ = accessor
    call.__doc__ = (f"``{accessor}`` from the primary, supplemented by the "
                    f"secondary through the lemma alignment, deduplicated.")
    return call


for _acc in _SUPPLEMENTED:
    setattr(ComposedGraph, _acc, _bind(_acc))


def compose(primary: str = "wordnet", secondary: str = "cskg") -> ComposedGraph:
    """Compose two registered graphs by name."""
    from . import load

    return ComposedGraph(primary=load(primary), secondary=load(secondary),
                         name=f"{primary}+{secondary}")
