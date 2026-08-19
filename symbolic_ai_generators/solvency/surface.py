"""A multi-paragraph observation surface for the covenant task, exactly aligned.

The flood surface answered *does a reader work*. This one answers a different
question: **does the machinery transfer to a structurally opposite task?**

Flood is routing over a network with a subset answer and expensive kernels.
Solvency is one boolean per group, a trivial kernel, and its whole difficulty is
**bitemporal**: `valid_time` is the quarter a figure is about, `transaction_time`
is when it could have been known, and a figure filed after the decision date must
not be used however current it is.

That inverts a rule the flood reader learned. There, a superseded value was a
**distractor** and the right move was *take the latest number in the sentence*.
Here the revision is the substance and *take the latest* is exactly wrong -- the
question is what was knowable at the decision date. **The same surface feature is
a trap in one domain and the answer in the other**, which is what makes this a
transfer test rather than a second implementation.

Four paragraphs, every claim aligned to at least one span:

    1  group structure -- who owns whom, plus a divested former subsidiary
    2  filings as first reported, with publication dates
    3  revisions, with their own later dates
    4  the covenant threshold, the decision date, and the question

Dates appear in two formats across variants (`2026-05-02` and `2 May 2026`), so
temporal normalisation is a step the reader has to take rather than a string
match.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from symbolic_ai_core.world import Quantity

__all__ = ["Span", "Observation", "render_observation"]

_MONTHS = ("January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December")

_VARIANTS = {
    "owns": (
        "{p} owns {c} outright.",
        "{c} is a wholly owned subsidiary of {p}.",
        "{p} holds all of the equity in {c}.",
        "{c} sits inside {p}.",
    ),
    "filed": (
        "{m} reported {n:.2f} USD, filed {d}.",
        "On {d}, {m} put its figure at {n:.2f} USD.",
        "{m}'s return of {n:.2f} USD was lodged {d}.",
        "A statement from {m} dated {d} gives {n:.2f} USD.",
    ),
    "revised": (
        "{m} restated that figure to {n:.2f} USD in a filing dated {d}.",
        "A correction from {m}, dated {d}, puts the number at {n:.2f} USD.",
        "{m} revised to {n:.2f} USD; the revision is dated {d}.",
        "The {d} amendment from {m} reads {n:.2f} USD.",
    ),
}


def _date(iso: str, style: int) -> str:
    if style == 0:
        return iso
    y, m, d = iso.split("-")
    return f"{int(d)} {_MONTHS[int(m) - 1]} {y}"


@dataclass(frozen=True)
class Span:
    start: int
    end: int
    claim: int | None
    kind: str
    entities: tuple[str, ...] = ()


@dataclass
class Observation:
    text: str = ""
    paragraphs: tuple[str, ...] = ()
    spans: tuple[Span, ...] = ()
    seed: int = 0

    def covered(self) -> set[int]:
        return {s.claim for s in self.spans if s.claim is not None}

    def distractors(self) -> tuple[Span, ...]:
        return tuple(s for s in self.spans if s.claim is None)


class _Doc:
    def __init__(self) -> None:
        self.parts: list[str] = []
        self.spans: list[Span] = []
        self._n = 0

    def add(self, text: str, *, claim: int | None = None,
            kind: str = "distractor", entities: tuple[str, ...] = ()) -> None:
        start = self._n
        self.parts.append(text)
        self._n += len(text)
        self.spans.append(Span(start, self._n, claim, kind, entities))

    def glue(self, text: str) -> None:
        self.parts.append(text)
        self._n += len(text)

    def text(self) -> str:
        return "".join(self.parts)


#: A divested subsidiary that **does** file, and a withdrawn figure. Both are
#: written twice: a ``cued`` form carrying a declared cancellation word, and an
#: ``uncued`` form carrying none. The uncued pair is the honest floor for
#: `symbolic_ai_generators.staleness` -- writing only cued distractors would
#: decide the experiment, which is the trap
#: `notes/lessons/2026-08-19-a-verification-that-uses-the-mechanisms-own-predicate-decides-the-experiment.md`
#: is about.
HARD_OWNS = {
    "cued": "sub_98 is a former subsidiary of {g}, divested before the period.",
    "uncued": "sub_98 left the {g} in April.",
}
HARD_FILING = {
    "cued": "{m}'s earlier draft of {n:.2f} USD, dated {d}, was withdrawn.",
    "uncued": "An unaudited memorandum from {m} on {d} shows {n:.2f} USD.",
}


def render_observation(case: Any, *, seed: int | None = None,
                       variants: int = 1,
                       hard_distractors: bool | str = False,
                       cue: str = "cued", hard_scale: float = 0.5,
                       hard_relative: float | None = None,
                       packed: bool = False,
                       stale_clause: bool = False) -> Observation:
    """Render a :class:`SolvencyCase` as four aligned paragraphs.

    ``hard_distractors`` points the distractors at entities that **matter**. The
    default one is inert twice over: ``sub_99`` names one entity so it matches no
    reader branch, and it has no filings, so admitting it would sum to nothing.
    That is the third instance of the same defect -- flood's disused track drew
    its endpoints from outside the network, scheduling's withdrawn machine
    carried no capability.

    Pass ``True`` for both hard forms, or ``"owns"`` / ``"filing"`` for one.
    ``cue`` selects the phrasing: ``"cued"`` carries a declared cancellation
    word, ``"uncued"`` carries none and is the floor for the staleness gate.

    ``stale_clause`` prefixes a **real** member's filing with a former-parent
    clause -- *"sub_0, formerly a subsidiary of sub_97, reported 105.87 USD,
    filed 29 May 2026"*. The clause is irrelevant and the filing is needed, so a
    sentence-level staleness gate deletes both and a clause-level one deletes
    only the first. That is the Wikipedia *Miramax* failure in miniature, made
    reproducible without leaving the repo; see
    ``notes/findings/2026-08-19-on-real-prose-the-sentence-is-the-wrong-unit.md``.

    ``packed`` renders **two claims in one sentence** -- the ownership and the
    child's first filing -- with a span for each over the same text. Real prose
    does this constantly and none of the generated surfaces did, which is why a
    sentence-level staleness gate reads as free here and loses the answer on
    Wikipedia. Default ``False`` so published numbers keep their meaning.

    ``hard_relative`` sets the spurious figure as a **relative perturbation of
    the filer's own latest figure** instead, which is the only way to make the
    perturbation small. Under ``hard_scale`` the injected value REPLACES the real
    one, so the perturbation is ``injected - real`` and is *largest* when the
    injection is smallest -- the U-shaped dose-response. With ``hard_relative``
    the perturbation is ``d`` by construction.

    ``hard_scale`` is the spurious figure as a fraction of the threshold, and it
    sets how much damage the distractor does. **Quote it with any number taken
    from this surface** -- at 0.5 the sum clears the covenant on every case, so
    the accuracy that produces is a property of the injection, not of the
    reader. A realistic size is one member's share, roughly 1/len(members).
    """
    world = case.world
    rng = random.Random(case.seed if seed is None else seed)

    def pick(kind: str) -> str:
        forms = _VARIANTS[kind]
        return forms[rng.randrange(min(variants, len(forms)))]

    style = rng.randrange(min(variants, 2))
    doc = _Doc()

    # index revenue claims by (member, value) so alignment is exact
    rev_index: dict[tuple[str, float], int] = {}
    owns_index: dict[tuple[str, str], int] = {}
    for i, c in enumerate(world.claims):
        if c.predicate == "revenue":
            v = c.roles["value"]
            key = (c.roles["of"].id, round(float(v.value), 2))
            rev_index[key] = i
        elif c.predicate == "owns":
            owns_index[(c.roles["parent"].id, c.roles["child"].id)] = i

    # ---- 1. group structure -------------------------------------------
    doc.add("COVENANT REVIEW. The obligor group is assessed on a consolidated "
            "basis.")
    packed_children = set()
    for (p, c), ci in sorted(owns_index.items()):
        doc.glue(" ")
        if packed:
            # One sentence, two claims. Real prose does this constantly and the
            # generated surfaces never did, which is why a sentence-level
            # staleness gate looked free here and lost the answer on Wikipedia.
            # See notes/findings/2026-08-19-on-real-prose-the-sentence-is-the-
            # wrong-unit.md.
            first = next(((m, v, k) for m, v, k in sorted(case.filings,
                                                          key=lambda f: (f[0],
                                                                         f[2]))
                          if m == c), None)
            if first is not None:
                _, v, k = first
                ri = rev_index.get((c, round(v, 2)))
                start = doc._n + 0
                doc.add(f"{p} owns {c}, which reported {v:.2f} USD, filed "
                        f"{_date(k, style)}.", claim=ci, kind="owns",
                        entities=(p, c))
                # a SECOND span over the SAME text: the sentence realises two
                # claim kinds with one signature, which is exactly what the
                # audit is built to count.
                doc.spans.append(Span(start, doc._n, ri, "revenue", (c,)))
                packed_children.add(c)
                continue
        doc.add(pick("owns").format(p=p, c=c), claim=ci, kind="owns",
                entities=(p, c))
    doc.glue(" ")
    doc.add("A former subsidiary, sub_99, was divested before the period and "
            "does not consolidate.")
    _sides = ({"owns", "filing"} if hard_distractors is True
              else {hard_distractors} if hard_distractors else set())
    if "owns" in _sides:
        doc.glue(" ")
        doc.add(HARD_OWNS[cue].format(g=case.group))

    # ---- 2. filings as first reported ---------------------------------
    first: dict[str, tuple[float, str]] = {}
    later: list[tuple[str, float, str]] = []
    for m, v, k in sorted(case.filings, key=lambda f: (f[0], f[2])):
        if m not in first:
            first[m] = (v, k)
        else:
            later.append((m, v, k))

    doc.glue("\n\n")
    doc.add("AS FIRST REPORTED.")
    stale_target = sorted(first)[0] if (stale_clause and first) else None
    for m, (v, k) in sorted(first.items()):
        if m in packed_children:
            continue                      # already stated inside its owns line
        doc.glue(" ")
        ci = rev_index.get((m, round(v, 2)))
        if m == stale_target:
            # sub_97 rather than a bare name, so the clause really does put a
            # SECOND entity in the sentence -- with an unmatched word the reader
            # sees one entity and the case is not packed at all.
            doc.add(f"{m}, formerly a subsidiary of sub_97, reported {v:.2f} "
                    f"USD, filed {_date(k, style)}.", claim=ci, kind="revenue",
                    entities=(m,))
            continue
        doc.add(pick("filed").format(m=m, n=v, d=_date(k, style)),
                claim=ci, kind="revenue", entities=(m,))

    if "owns" in _sides:
        # sub_98 must FILE, or admitting the ownership claim costs nothing --
        # which is exactly what makes sub_99 inert. Dated inside the window and
        # large enough to move a threshold.
        doc.glue(" ")
        doc.add(pick("filed").format(m="sub_98",
                                     n=case.threshold * hard_scale,
                                     d=_date(case.decision_date, style)))
    if "filing" in _sides:
        doc.glue(" ")
        # The filer has to be a member with a figure already usable at the
        # determination date, or a "relative" perturbation is not relative to
        # anything -- an empty fallback to the threshold silently turns a 0.1%
        # perturbation into a 100% one, which is exactly what it did.
        usable = sorted((k, v, m) for m, v, k in case.filings
                        if m in case.members and k <= case.decision_date)
        filer = usable[-1][2] if usable else "sub_0"
        if hard_relative is None:
            value = case.threshold * hard_scale
        else:
            own = [v for k, v, m in usable if m == filer]
            if not own:
                raise ValueError("hard_relative needs a usable filing to "
                                 "perturb; none found")
            value = own[-1] * (1 + hard_relative)
        doc.add(HARD_FILING[cue].format(m=filer, n=value,
                                        d=_date(case.decision_date, style)))

    # ---- 3. revisions --------------------------------------------------
    doc.glue("\n\n")
    doc.add("SUBSEQUENT REVISIONS.")
    if not later:
        doc.glue(" ")
        doc.add("No figures were restated.")
    for m, v, k in later:
        doc.glue(" ")
        ci = rev_index.get((m, round(v, 2)))
        doc.add(pick("revised").format(m=m, n=v, d=_date(k, style)),
                claim=ci, kind="revenue", entities=(m,))

    # ---- 4. the covenant ----------------------------------------------
    doc.glue("\n\n")
    doc.add("THE TEST.")
    doc.glue(" ")
    doc.add(f"The covenant requires consolidated revenue of at least "
            f"{case.threshold:.2f} USD.")
    doc.glue(" ")
    doc.add(f"The determination is made as at {_date(case.decision_date, style)}"
            f", on the information available on that date.")
    doc.glue(" ")
    doc.add("Was the covenant met?")

    text = doc.text()
    return Observation(text=text, paragraphs=tuple(text.split("\n\n")),
                       spans=tuple(doc.spans), seed=case.seed)
