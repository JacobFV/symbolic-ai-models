"""How parser quality moves with the amount of data — a curve that is free here.

Almost every parser evaluation in the literature is run on a fixed treebank, so
"how much data would this need" is answered by subsampling a corpus that was
expensive to annotate and is exhausted at the top end. Here episodes are a pure
function of a seed, so training sets of any size can be drawn on demand and the
evaluation set is always disjoint by construction.

That makes the learning curve the natural way to compare a *learned* parser
against a *written* one. A hand-written parser is a flat line: it does not
improve with data, and whatever it scores at ten episodes it scores at ten
thousand. An induced parser is a curve. Where the two cross — if they cross —
is the honest answer to whether writing the grammar down was worth it.
"""

from __future__ import annotations

from typing import Sequence

from ..data.curriculum import Episode, generate, resolve_lessons
from ..data.tokenizer import SymbolTokenizer
from .base import build, parser_names
from .evaluate import ParserReport, evaluate_parser

__all__ = ["scaling_curve", "curve_table"]


def scaling_curve(names: Sequence[str], lessons: Sequence[str], *,
                  sizes: Sequence[int] = (4, 16, 64, 256),
                  n_eval: int = 20, language: str = "english",
                  vocab_size: int = 4096) -> dict[str, list[ParserReport]]:
    """Fit each parser at each training size; score all of them on one eval set.

    The evaluation episodes are drawn once, from seeds a million away, and
    reused across every size and every parser — so the curve moves because the
    parser changed and not because the test moved under it.
    """
    from ..train import TrainConfig, build_tokenizer

    evaluation = list(generate(lessons, n=n_eval, seed0=1_000_000,
                               language=language))
    out: dict[str, list[ParserReport]] = {name: [] for name in names}
    for size in sizes:
        training = list(generate(lessons, n=size, seed0=0, language=language))
        tok = build_tokenizer(TrainConfig(vocab_size=vocab_size), training)
        for name in names:
            parser = build(name)
            parser.fit(training, tok)
            report = evaluate_parser(parser, evaluation, tok)
            report.n_episodes = len(training)      # record what it was fitted on
            out[name].append(report)
    return out


def curve_table(curves: dict[str, list[ParserReport]]) -> str:
    """F1 by training size, one row per parser."""
    if not curves:
        return "no parsers evaluated"
    sizes = [r.n_episodes for r in next(iter(curves.values()))]
    head = f"{'parser':<14}{'kind':<9}" + "".join(f"{s:>9}" for s in sizes)
    lines = [head + f"{'floor':>9}", "-" * (len(head) + 9)]
    for name, reports in sorted(curves.items(),
                                key=lambda kv: -(kv[1][-1].f1 if kv[1] else 0)):
        if not reports:
            continue
        kind = "learned" if reports[0].learned else "written"
        row = f"{name:<14}{kind:<9}" + "".join(f"{r.f1:>9.3f}" for r in reports)
        lines.append(row + f"{reports[-1].floor_f1:>9.3f}")
    lines.append("-" * (len(head) + 9))
    lines.append("F1 against the roles the generator actually used; columns are "
                 "training episodes per lesson.")
    lines.append("A written parser is flat by construction — it does not read "
                 "the training set at all.")
    return "\n".join(lines)
