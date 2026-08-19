"""Take the structural crutches off any domain's observation surface.

Written for flood and generalised when the same question came up for the other
two domains. All three define their own ``Observation``/``Span`` -- structurally
identical, separately declared -- so these work by duck typing and rebuild
results with whatever classes the observation was made from. Nothing is moved.

Two transforms, in increasing strength:

- `unsaturate` drops the section headings and shuffles paragraph **order**.
- `interleave` additionally destroys paragraph **grouping**: every sentence in
  one paragraph, seeded order.

Both keep a pronoun with its antecedent where the spans record one. A stranded
pronoun makes the document **false** rather than merely hard, so the ground truth
would be wrong and not the reader -- a mistake this repo has made once already.
Domains whose spans carry no ``reference`` field have no pronouns to strand.
"""

from __future__ import annotations

import random
import re
from typing import Any, Sequence


def _rebuild(obs: Any, paragraphs: Sequence[str], spans: Sequence[Any]) -> Any:
    """A new observation of the same class, joined the way it was split."""
    text = "\n\n".join(paragraphs)
    kwargs: dict[str, Any] = {"text": text, "paragraphs": tuple(paragraphs),
                              "spans": tuple(spans), "seed": obs.seed}
    if hasattr(obs, "by_claim"):
        by_claim: dict[int, list[int]] = {}
        for si, s in enumerate(spans):
            if s.claim is not None:
                by_claim.setdefault(s.claim, []).append(si)
        kwargs["by_claim"] = {k: tuple(v) for k, v in by_claim.items()}
    return type(obs)(**kwargs)


def _respan(span: Any, delta: int) -> Any:
    from dataclasses import replace
    return replace(span, start=span.start + delta, end=span.end + delta)


def strip_heading(para: str, headings: Sequence[str]) -> int:
    """Characters to cut from the front of ``para``, trailing space included."""
    for h in headings:
        if para.startswith(h):
            cut = len(h)
            while cut < len(para) and para[cut] in " \t":
                cut += 1
            return cut
    return 0


def _paragraph_bounds(obs: Any) -> list[tuple[int, int]]:
    out, at = [], 0
    for para in obs.paragraphs:
        out.append((at, at + len(para)))
        at += len(para) + 2
    return out


def unsaturate(obs: Any, *, headings: Sequence[str] = (),
               seed: int | None = None, drop_headings: bool = True,
               shuffle: bool = True) -> Any:
    """No section labels, no fixed paragraph order. Alignment preserved.

    The knobs are separate so the two giveaways can be priced independently: a
    reader may be leaning on the heading, on the order, or on both. Measured on
    flood, the headings were worth **nothing** and the order was worth
    everything.
    """
    bounds = _paragraph_bounds(obs)
    per_para: list[list[Any]] = [[] for _ in obs.paragraphs]
    for s in obs.spans:
        for pi, (lo, hi) in enumerate(bounds):
            if s.start >= lo and s.end <= hi:
                per_para[pi].append(s)
                break

    pieces: list[tuple[str, list[Any]]] = []
    for pi, para in enumerate(obs.paragraphs):
        cut = strip_heading(para, headings) if drop_headings else 0
        local = []
        for s in per_para[pi]:
            shifted = _respan(s, -(bounds[pi][0] + cut))
            if shifted.end <= 0:
                continue                    # a heading span, gone with it
            if shifted.start < 0:
                shifted = _respan(shifted, -shifted.start)
            local.append(shifted)
        pieces.append((para[cut:], local))

    order = list(range(len(pieces)))
    if shuffle:
        random.Random(obs.seed if seed is None else seed).shuffle(order)

    paragraphs, spans, at = [], [], 0
    for pi in order:
        body, local = pieces[pi]
        paragraphs.append(body)
        spans.extend(_respan(s, at) for s in local)
        at += len(body) + 2
    spans.sort(key=lambda s: (s.start, s.end))
    return _rebuild(obs, paragraphs, spans)


def atoms(obs: Any) -> list[tuple[int, int]]:
    """Sentence ranges, with a pronoun sentence glued to its antecedent."""
    text, starts, at = obs.text, [], 0
    for para in obs.paragraphs:
        for piece in re.split(r"(?<=\.)(\s+)", para):
            if piece and not piece.isspace():
                starts.append((at, at + len(piece)))
            at += len(piece)
        at += 2

    pronoun = [s for s in obs.spans
               if getattr(s, "reference", "name") == "pronoun"]
    out: list[tuple[int, int]] = []
    for lo, hi in starts:
        if out and any(lo <= s.start and s.end <= hi for s in pronoun):
            out[-1] = (out[-1][0], hi)
        else:
            out.append((lo, hi))
    return out


def interleave(obs: Any, *, seed: int | None = None) -> Any:
    """Every sentence in one paragraph, seeded order. Grouping destroyed.

    `unsaturate` removes headings and paragraph order; a reader can still
    survive it by reading paragraph *roles* off content. This removes the last
    template property -- that the generator puts every road in one paragraph and
    every flood report in another, which a real report does not.
    """
    text = obs.text
    ranges = atoms(obs)
    order = list(range(len(ranges)))
    random.Random(obs.seed if seed is None else seed).shuffle(order)

    parts, spans, at = [], [], 0
    for ai in order:
        lo, hi = ranges[ai]
        parts.append(text[lo:hi])
        spans.extend(_respan(s, at - lo) for s in obs.spans
                     if s.start >= lo and s.end <= hi)
        at += (hi - lo) + 1
    spans.sort(key=lambda s: (s.start, s.end))
    return _rebuild(obs, [" ".join(parts)], spans)
