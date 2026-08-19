"""Which claim kinds share a sentence signature, before any reader is built.

Three measurements converged on one instrument. Structure is load-bearing
exactly where a sentence's **signature** does not determine its **predicate**
(2026-08-19, flood vs scheduling, confirmed by renaming manipulation). The
residual no content-free observable can settle is exactly the group the
signature leaves open (2026-08-19 closure). And the content a reader needs is
only for the many-valued role inside that group.

So the useful thing to compute for a **new** domain is not a reader but this: for
each claim kind, what sentence signatures realise it, and which signatures carry
more than one kind. That predicts where the reader will break, and it costs one
pass over a generated corpus.

The signature is what a reader sees before it knows anything: how many entity
mentions a sentence contains, how many numbers, how many dates. Entity mentions
are counted by the ``name_number`` convention all three generators share, and
split by **prefix**, because a prefix that fixes the type is one route to a
determinate signature -- scheduling's ``job_``/``machine_`` being the case that
made this visible.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

__all__ = ["Signature", "Audit", "audit_surface"]

_ENTITY = re.compile(r"\b([a-z][a-z_]*?)_(\d+)\b")
_NUMBER = re.compile(r"(?<![\d-])\d+(?:\.\d+)?(?![\d-])")
#: Both styles the generators emit. Solvency renders half its corpus as
#: "1 June 2026" rather than "2026-06-01", and a date regex that saw only the
#: ISO form would count the day and the year as two bare NUMBERS -- silently
#: changing every signature in half the corpus. Caught before it mattered, but
#: it is the shape of measurement bug this repo has paid for before.
_MONTHS = ("January|February|March|April|May|June|July|August|September|"
           "October|November|December")
_DATE = re.compile(rf"\b\d{{4}}-\d{{2}}-\d{{2}}\b|\b\d{{1,2}} (?:{_MONTHS}) \d{{4}}\b")


@dataclass(frozen=True)
class Signature:
    """What a reader can see about a sentence before it knows any words."""

    #: (prefix, count) pairs, sorted -- e.g. (("region", 2),)
    entities: tuple[tuple[str, int], ...]
    numbers: int
    dates: int
    #: which declared value vocabularies this sentence's numbers fall in
    vocabularies: tuple[str, ...] = ()

    def __str__(self) -> str:
        ents = ", ".join(f"{n}x {p}" for p, n in self.entities) or "no entities"
        vocab = f"; in {'+'.join(self.vocabularies)}" if self.vocabularies else ""
        return f"({ents}; {self.numbers} num; {self.dates} date{vocab})"


@dataclass
class Audit:
    """The result: which signatures carry which claim kinds."""

    by_kind: dict[str, set] = field(default_factory=lambda: defaultdict(set))
    by_signature: dict[Signature, set] = field(
        default_factory=lambda: defaultdict(set))
    spans: int = 0
    #: claim spans whose signature is shared with another kind
    ambiguous_spans: int = 0
    #: how many spans each colliding signature accounts for
    mass_by_signature: dict = field(default_factory=dict)

    @property
    def ambiguity_mass(self) -> float:
        """Share of claim spans a reader cannot type from the signature alone.

        This is the number that predicts structure-dependence. At 0 a
        content-free reader can work from signature alone and arrangement is not
        load-bearing; above 0 the ambiguous group needs arrangement, content, or
        an emitted ambiguity for the kernel to settle.
        """
        return self.ambiguous_spans / self.spans if self.spans else 0.0

    @property
    def collisions(self) -> dict:
        """Signature -> the kinds sharing it, for signatures carrying several."""
        return {s: k for s, k in self.by_signature.items() if len(k) > 1}

    def report(self) -> str:
        lines = [f"{self.spans} claim spans, ambiguity mass "
                 f"{self.ambiguity_mass:.3f}"]
        if not self.collisions:
            lines.append("  no signature carries more than one claim kind: a "
                         "reader can type every")
            lines.append("  sentence from its shape alone, so arrangement is "
                         "not load-bearing here.")
        for sig, kinds in sorted(
                self.collisions.items(),
                key=lambda kv: -self.mass_by_signature.get(kv[0], 0)):
            n = self.mass_by_signature.get(sig, 0)
            lines.append(f"  {n:>5} spans  {sig}  ->  {', '.join(sorted(kinds))}")
        return "\n".join(lines)


def signature_of(text: str, registries: dict | None = None,
                 entity: str | None = None) -> Signature:
    """The signature of one sentence.

    ``registries`` is the reader's **declared value knowledge**, mapping a name
    to the set of values that name covers -- flood's ``VALUE_REGISTRY`` is the
    worked example. Supplying it refines the signature by which vocabularies the
    sentence's numbers fall in, which is what a reader holding that knowledge
    actually sees. Without it the audit counts collisions the reader can already
    settle, and overstates the ambiguity: flood reads 0.860 raw and far less once
    its registry is supplied.
    """
    dates = _DATE.findall(text)
    without_dates = _DATE.sub(" ", text)
    # ``entity`` overrides the ``name_number`` convention. Solvency names its
    # parent ``group``, with no number, and the generic pattern misses it --
    # which would audit a domain with one of its entities invisible.
    pattern = re.compile(entity) if entity else _ENTITY
    counts: dict[str, int] = defaultdict(int)
    for match in pattern.finditer(without_dates):
        # An alternation carries one group per branch and all but the matching
        # one are None, so take the first that fired rather than group(1).
        named = next((g for g in match.groups() if g), None)
        counts[named or match.group(0)] += 1
    numbers = _NUMBER.findall(pattern.sub(" ", without_dates))
    vocab: tuple[str, ...] = ()
    if registries:
        hit = {name for n in numbers for name, values in registries.items()
               if float(n) in values}
        vocab = tuple(sorted(hit))
    return Signature(tuple(sorted(counts.items())), len(numbers), len(dates),
                     vocab)


def audit_surface(observations, registries: dict | None = None,
                  entity: str | None = None) -> Audit:
    """Audit a corpus of rendered observations.

    Each observation supplies ``spans``; a span with a ``claim`` realises a
    claim of a known ``kind``, and its text is the sentence a reader would have
    to type. Distractor spans are skipped -- they are not claims, and counting
    them would inflate the ambiguity with text that realises nothing.
    """
    out = Audit()
    seen: list[tuple] = []
    for obs in observations:
        for span in obs.spans:
            if span.claim is None:
                continue
            sig = signature_of(obs.text[span.start:span.end], registries,
                               entity)
            out.by_kind[span.kind].add(sig)
            out.by_signature[sig].add(span.kind)
            out.spans += 1
            seen.append((sig, span.kind))
    for sig, _ in seen:
        if len(out.by_signature[sig]) > 1:
            out.ambiguous_spans += 1
            out.mass_by_signature[sig] = out.mass_by_signature.get(sig, 0) + 1
    return out
