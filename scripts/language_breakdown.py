"""Split a finished run's evaluation score by the language of the prompt.

The sweep reports one pooled number per model. That is the authority and this
does not replace it — it decomposes it, using the harness's own
:func:`symbolic_ai_core.invariance.label_accuracy` on the run's own fitted model
and the run's own evaluation episodes.

    uv run python scripts/language_breakdown.py runs/full179_multilingual/omegaclaw_text-002 \
                                                runs/full179_multilingual/omegaclaw_textlang-002

Why the comparison across languages is exact rather than approximate
--------------------------------------------------------------------
``TrainConfig.languages`` renders **the same seeds** in each pack and
interleaves them, so filtering the evaluation set to one language leaves the
(lesson, seed) order untouched and identical to every other language's. The
masking RNG is seeded and walks positions in order, so each pack is scored on
the same trees with the same nodes hidden. Everything is held fixed except the
prose, which is the only thing that was ever different.

What to look for
----------------
``omegaclaw_textlang-002`` minus ``omegaclaw_text-002``, per language. If
conditioning on language is doing what it is supposed to, the gain should be
largest where the surface claws are least reliable — the model should be
learning to stop trusting them in Chinese while still trusting them in
``symbols``. A gain that is flat across languages is a gain that has nothing to
do with language.
"""

from __future__ import annotations

import argparse
import collections
from typing import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("runs", nargs="+", help="finished run directories")
    ap.add_argument("--mask-rate", dest="mask_rate", type=float, default=0.15)
    args = ap.parse_args(argv)

    from symbolic_ai_core.invariance import label_accuracy
    from symbolic_ai_models.train import load_data, load_run

    table: dict[str, dict[str, float]] = {}
    order: list[str] = []
    for run in args.runs:
        model, tok, cfg = load_run(run)
        _, eval_eps = load_data(cfg)
        by_language: dict[str, list] = collections.defaultdict(list)
        for ep in eval_eps:
            by_language[ep.language].append(ep)
        order = list(by_language)
        table[model.name] = {
            lang: label_accuracy(model, eps, tok, max_nodes=cfg.max_nodes,
                                 mask_rate=args.mask_rate)
            for lang, eps in by_language.items()}
        counts = {lang: len(eps) for lang, eps in by_language.items()}
        print(f"{model.name}: {counts}", flush=True)

    print(f"\n{'model':<30}" + "".join(f"{l[:10]:>12}" for l in order))
    for name, row in table.items():
        print(f"{name:<30}" + "".join(f"{row[l]:>12.4f}" for l in order))
    if len(table) == 2:
        a, b = table.values()
        names = list(table)
        print(f"{names[1]} - {names[0]}:")
        print(f"{'':<30}" + "".join(f"{b[l] - a[l]:>+12.4f}" for l in order))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
