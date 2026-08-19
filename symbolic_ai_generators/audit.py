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

__all__ = ["Signature", "Audit", "audit_surface", "unconsumed"]

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
    #: signatures occupied by text that realises NO claim, and how often
    prose_signatures: dict = field(default_factory=dict)

    @property
    def ambiguity_mass(self) -> float:
        """Share of claim spans a reader cannot type from the signature alone.

        This is the number that predicts structure-dependence. At 0 a
        content-free reader can work from signature alone and arrangement is not
        load-bearing; above 0 the ambiguous group needs arrangement, content, or
        an emitted ambiguity for the kernel to settle.
        """
        return self.ambiguous_spans / self.spans if self.spans else 0.0

    #: predicate -> the role names it carries, when the worlds were supplied
    roles_by_kind: dict = field(default_factory=dict)

    @property
    def collisions(self) -> dict:
        """Signature -> the kinds sharing it, for signatures carrying several."""
        return {s: k for s, k in self.by_signature.items() if len(k) > 1}

    @property
    def real_collisions(self) -> dict:
        """Collisions where the kinds also share a **role signature**.

        A sentence-signature collision is only ambiguity if the colliding kinds
        could be confused once the roles are recovered. flood's largest
        collision by span mass -- ``bridge_on`` (a, b, via) against ``link``
        (a, b), 456 of every thousand claim spans -- is not one: they look
        identical in text and cannot be swapped, because a reader that recovers
        the roles already has them apart. Measured cost of that collision:
        **zero, on zero permutable cases.**

        Needs ``worlds``; without it this returns every collision, which
        over-counts. flood reads 0.617 raw and 0.161 real.
        """
        if not self.roles_by_kind:
            return self.collisions
        out = {}
        for sig, kinds in self.collisions.items():
            sigs = {frozenset(self.roles_by_kind.get(k, ())) for k in kinds}
            if len(sigs) < len(kinds):
                out[sig] = kinds
        return out

    @property
    def prose_collisions(self) -> dict:
        """Signatures a claim kind shares with text realising no claim.

        Not ambiguity between kinds but a **false-positive risk**: a reader
        typing sentences by shape will read that prose as a claim. Flood's
        "Districts X and Y lie outside the affected area" and "A disused track
        once ran from X to Z" both carry the ``link`` signature, and the reader
        is independently known to admit the disused track as a road.

        Only populated when ``audit_surface`` is given ``prose=True``, since it
        needs the full text rather than the spans.
        """
        return {sig: (self.by_signature[sig], n)
                for sig, n in self.prose_signatures.items()
                if sig in self.by_signature}

    @property
    def real_ambiguity_mass(self) -> float:
        """Ambiguity mass counting only collisions the roles cannot settle."""
        if not self.spans:
            return 0.0
        real = sum(self.mass_by_signature.get(s, 0) for s in self.real_collisions)
        return real / self.spans

    def report(self) -> str:
        lines = [f"{self.spans} claim spans, ambiguity mass "
                 f"{self.ambiguity_mass:.3f}"]
        if self.roles_by_kind:
            lines[0] += f" ({self.real_ambiguity_mass:.3f} real)"
        real = self.real_collisions
        if not self.collisions:
            lines.append("  no signature carries more than one claim kind: a "
                         "reader can type every")
            lines.append("  sentence from its shape alone, so arrangement is "
                         "not load-bearing here.")
        for sig, kinds in sorted(
                self.collisions.items(),
                key=lambda kv: -self.mass_by_signature.get(kv[0], 0)):
            n = self.mass_by_signature.get(sig, 0)
            mark = "" if sig in real else "   [roles differ: not ambiguity]"
            lines.append(f"  {n:>5} spans  {sig}  ->  "
                         f"{', '.join(sorted(kinds))}{mark}")
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
                  entity: str | None = None, worlds=None,
                  prose: bool = False) -> Audit:
    """Audit a corpus of rendered observations.

    Each observation supplies ``spans``; a span with a ``claim`` realises a
    claim of a known ``kind``, and its text is the sentence a reader would have
    to type. Distractor spans are skipped -- they are not claims, and counting
    them would inflate the ambiguity with text that realises nothing.
    """
    out = Audit()
    if worlds is not None:
        for w in worlds:
            for c in w.claims:
                out.roles_by_kind.setdefault(c.predicate, frozenset(c.roles))
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

    if prose:
        # Every sentence NOT covered by a claim span. A reader types sentences
        # by shape and cannot see the span table, so prose sharing a claim
        # kind's signature is a false positive waiting to happen -- a different
        # failure from ambiguity between kinds, and invisible to the pass above.
        for obs in observations:
            covered = [(sp.start, sp.end) for sp in obs.spans
                       if sp.claim is not None]
            for sent, lo, hi in _sentences_with_offsets(obs.text):
                if any(lo < e and hi > s0 for s0, e in covered):
                    continue
                sig = signature_of(sent, registries, entity)
                out.prose_signatures[sig] = out.prose_signatures.get(sig, 0) + 1
    return out


def _sentences_with_offsets(text: str):
    """``(sentence, start, end)`` for every sentence in the document."""
    at = 0
    for piece in re.split(r"(?<=[.?])(\s+)", text):
        if piece and not piece.isspace():
            yield piece, at, at + len(piece)
        at += len(piece)


def role_signature(claim) -> frozenset:
    """The role names a claim carries -- ``{"where"}``, ``{"a", "b", "via"}``.

    A sentence-signature collision is only *real* ambiguity if the colliding
    kinds also share this. ``link`` (a, b) and ``bridge_on`` (a, b, via) look
    identical in text -- two regions, no number -- and are the largest collision
    flood has by span mass, yet cost nothing: a reader that recovers the roles
    can still tell them apart, and the flow rebuilds bridges from the crossings
    that carry limits. ``depot``, ``flooded`` and ``needs`` all carry ``where``
    alone, and that collision costs everything.
    """
    return frozenset(claim.roles)


def collision_cost(cases, observations, solve, *, registries=None,
                   entity=None, seed=0) -> dict:
    """What each signature collision costs the answer, measured not reasoned.

    For every colliding signature, the predicates of the claims realised by
    spans with that signature are **permuted among claims sharing a role
    signature**, in the *true* world, and the flow is re-solved. That is the cost
    of being unable to tell those kinds apart.

    Crucially this needs no reader. The audit's value is that it speaks before a
    reader exists, and a cost estimate that required one would give that up.

    Returns ``{frozenset(kinds): {"cost": float, "n": int, "permutable": int}}``.
    """
    import random
    from dataclasses import replace

    a = audit_surface(observations, registries=registries, entity=entity)
    groups = {frozenset(k) for k in a.collisions.values()}
    out: dict = {}

    for kinds in groups:
        rng = random.Random(seed)
        ok, permutable = [], 0
        for case, obs in zip(cases, observations):
            world = case.world
            base = solve(world)[0]
            idx = [i for i, c in enumerate(world.claims) if c.predicate in kinds]
            by_roles: dict = defaultdict(list)
            for i in idx:
                by_roles[role_signature(world.claims[i])].append(i)
            claims = list(world.claims)
            moved = False
            for members in by_roles.values():
                if len(members) < 2:
                    continue
                preds = [claims[i].predicate for i in members]
                if len(set(preds)) < 2:
                    continue
                shuffled = preds[:]
                rng.shuffle(shuffled)
                if shuffled == preds:
                    shuffled = preds[1:] + preds[:1]
                for i, p in zip(members, shuffled):
                    claims[i] = replace(claims[i], predicate=p)
                moved = True
            if not moved:
                continue
            permutable += 1
            ok.append(solve(replace(world, claims=tuple(claims)))[0] == base)
        out[kinds] = {"cost": 1.0 - (sum(ok) / len(ok)) if ok else 0.0,
                      "n": len(ok), "permutable": permutable}
    return out


def deletion_dependency(cases, solve, kind: str, *, world_of=None) -> float:
    """P(the answer changes | one claim of ``kind`` is removed).

    The companion to `collision_cost`, and **not the same number**. They answer
    different questions and were once confused for each other:

    - `collision_cost` permutes predicates between kinds that look alike in
      text. It is the cost of not being able to **type** a sentence.
    - this deletes one claim. It is the cost of a claim being **spurious or
      missing**.

    ``bridge_on``/``link`` has collision cost **0.000** -- their role signatures
    differ, so nothing is permutable -- while link *deletion* dependency is
    **0.138**. The two agreed at "low" by accident, and the accident was briefly
    read as a prediction.

    Which one applies depends on the perturbation being carried. A reader that
    may have **invented** a claim is carrying deletions; a reader that cannot
    **type** a sentence is carrying permutations. Measured 2026-08-19: carrying
    deletions of a 0.138-dependency kind gave up nothing, carrying reassignments
    of a 0.467-dependency kind decided 0.067. Solvency's ``owns`` is 0.000 --
    every member is recoverable from its own filing, so ownership is inert.
    """
    from dataclasses import replace

    out = []
    for case in cases:
        world = world_of(case) if world_of else case.world
        base = solve(world)[0]
        idx = [i for i, c in enumerate(world.claims) if c.predicate == kind]
        if not idx:
            continue
        hits = []
        for i in idx:
            trimmed = replace(world, claims=tuple(
                c for j, c in enumerate(world.claims) if j != i))
            hits.append(solve(trimmed)[0] != base)
        out.append(sum(hits) / len(hits))
    return sum(out) / len(out) if out else 0.0


def unconsumed(text: str, reader) -> int:
    """Sentences whose removal leaves the reader's world unchanged.

    The task-drift detector. Every other check in this repo inspects the **read
    world**, so a claim kind the reader has no branch for is invisible to all of
    them -- it never enters the world to be checked. The text still contains the
    sentence.

    Measured 2026-08-19 on flood, against a weight restriction the world cannot
    express (it admits light vehicles and refuses heavy ones, where flooding
    refuses everything): answers wrong **22 of 22**, caught by
    ``role_assignment_forced`` 0/22, by the role-independent certificate 0/22, by
    ``omits_load_bearing`` 0/22, and by this **22/22**.

    Two things this is not:

    - **Not entity familiarity.** A first version asked whether a sentence's
      entities were known and caught nothing: the restricted region appears in
      the link claims, so the sentence looked read while contributing nothing.
      Consumption is not familiarity.
    - **Not a presence test.** Clean text already contains distractors that
      consume to nothing, so the signal is an **increase** over the document's
      own baseline, not a non-zero count.

    Costs ``len(sentences)`` reads. A read is 0.2 ms against a 9 ms answer, so
    the whole check is cheaper than solving once.
    """
    sents = [s for s in re.split(r"(?<=[.?])\s+", text.replace("\n\n", " "))
             if s.strip()]
    if not sents:
        return 0

    def world_of(t: str):
        try:
            w = reader(t)
        except Exception:
            return None
        return {(c.predicate, tuple(sorted(c.entities()))) for c in w.claims}

    # Compare like with like: reading the paragraph-structured original against
    # sentence-joined variants makes every world differ for an unrelated reason,
    # and nothing ever looks unconsumed.
    base = world_of(" ".join(sents))
    if base is None:
        return 0
    out = 0
    for i in range(len(sents)):
        got = world_of(" ".join(s for j, s in enumerate(sents) if j != i))
        if got == base:
            out += 1
    return out
