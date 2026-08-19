"""Remove the two structural giveaways from a rendered observation.

``render_observation`` emits five paragraphs in a fixed order, each opening with
a section heading naming what it contains. ``read_signature`` -- the arm that
scores 1.000 and is quoted as having zero reader loss -- branches on ``pi == 0``,
``pi == 1``, ``pi == 2``, ``pi == 3``. It knows the template by **index**. So the
headline measures the harness at least as much as it measures reading, which is
what ``state.yml`` means by the surface being *saturated*.

This transforms an :class:`Observation` into one with the headings dropped and
the paragraphs in a seeded random order, remapping every span offset so the
alignment survives. Everything else is untouched: the same sentences, the same
claims, the same distractors.

**Paragraph level, deliberately, not sentence level.** Every pronoun in this
surface resolves within its own paragraph -- the capacity pronoun to the naming
sentence before it, the load-limit pronoun to the superseded rating, the demand
pronoun to the needs sentence. Reordering paragraphs therefore keeps every
sentence *true*. Interleaving sentences would strand those pronouns and make the
ground truth wrong rather than the reader, which is a mistake this repo has
already made once and paid for.
"""

from __future__ import annotations

import random

from symbolic_ai_generators.flood.surface import Observation, Span

#: The section labels ``render_observation`` writes. Two shapes: standalone
#: spans ("ROAD NETWORK.") and, for the first paragraph, a label glued to the
#: front of a sentence that also carries content.
HEADINGS = ("SITUATION REPORT.", "ROAD NETWORK.", "OVERNIGHT.",
            "LOADING AND LIMITS.", "TASKING.")


def _strip_heading(para: str) -> int:
    """Characters to cut from the front of ``para``, including trailing space."""
    for h in HEADINGS:
        if para.startswith(h):
            cut = len(h)
            while cut < len(para) and para[cut] in " \t":
                cut += 1
            return cut
    return 0


def unsaturate(obs: Observation, *, seed: int | None = None,
               drop_headings: bool = True, shuffle: bool = True) -> Observation:
    """A copy of ``obs`` without the section labels and the fixed order.

    Both knobs are separate so the two giveaways can be priced independently --
    a reader may be leaning on the heading, on the order, or on both.
    """
    text = obs.text
    bounds: list[tuple[int, int]] = []
    at = 0
    for para in obs.paragraphs:
        bounds.append((at, at + len(para)))
        at += len(para) + 2                       # the "\n\n" separator

    # Spans never straddle a paragraph: the separator is glue and realises
    # nothing, so every span sits wholly inside one of these ranges.
    per_para: list[list[Span]] = [[] for _ in obs.paragraphs]
    for s in obs.spans:
        for pi, (lo, hi) in enumerate(bounds):
            if s.start >= lo and s.end <= hi:
                per_para[pi].append(s)
                break

    pieces: list[tuple[str, list[Span]]] = []
    for pi, para in enumerate(obs.paragraphs):
        cut = _strip_heading(para) if drop_headings else 0
        body = para[cut:]
        local: list[Span] = []
        for s in per_para[pi]:
            start = s.start - bounds[pi][0] - cut
            end = s.end - bounds[pi][0] - cut
            if end <= 0:
                continue          # a heading span, gone with the heading
            local.append(Span(max(start, 0), end, s.claim, s.kind, s.entities,
                              s.reference))
        pieces.append((body, local))

    order = list(range(len(pieces)))
    if shuffle:
        random.Random(obs.seed if seed is None else seed).shuffle(order)

    out_paras: list[str] = []
    out_spans: list[Span] = []
    at = 0
    for pi in order:
        body, local = pieces[pi]
        out_paras.append(body)
        for s in local:
            out_spans.append(Span(s.start + at, s.end + at, s.claim, s.kind,
                                  s.entities, s.reference))
        at += len(body) + 2

    out_spans.sort(key=lambda s: (s.start, s.end))
    by_claim: dict[int, list[int]] = {}
    for si, s in enumerate(out_spans):
        if s.claim is not None:
            by_claim.setdefault(s.claim, []).append(si)
    return Observation(text="\n\n".join(out_paras),
                       paragraphs=tuple(out_paras), spans=tuple(out_spans),
                       seed=obs.seed,
                       by_claim={k: tuple(v) for k, v in by_claim.items()})
