"""Score the signal `omegaclaw_lang-002` is handed for free, as its own head.

Both notes that commissioned the language-conditioned models attach the same
condition to supplying language as ground truth: *a supplied signal must still
be measured as its own head with its own floor, or a subproblem has been assumed
away rather than factored out.* This is that measurement.

    uv run python scripts/language_id_head.py

Fitted on the training seeds and scored on the evaluation seeds (which start at
one million, so the two cannot meet), against the majority-class floor. The
classifier is deliberately the dullest thing that could work — nearest centroid
over character trigram profiles — because the question is *how much is there to
know*, not how well anything knows it. A dull method scoring near 1.0 is the
strong form of the answer: the oracle was nearly free, and factoring it out cost
almost nothing.

The pair to watch is `english` against `english_synonym`. They are the same
language rendered with held-out near-synonyms in the question, and only 26 of
537 prompts differ between them, so a head that separates the seven packs may
still be unable to separate those two — in which case the "language" the models
condition on is, for that pair, not recoverable from the surface at all.
"""

from __future__ import annotations

import argparse
import collections
import math
from typing import Sequence

PACKS = ["english", "spanish", "chinese", "turkish", "swahili",
         "english_synonym", "symbols"]


def profile(texts: Sequence[str], n: int = 3) -> dict[str, float]:
    """L2-normalised character n-gram counts. One vector per language."""
    counts: collections.Counter[str] = collections.Counter()
    for text in texts:
        counts.update(text[i:i + n] for i in range(len(text) - n + 1))
    norm = math.sqrt(sum(v * v for v in counts.values())) or 1.0
    return {k: v / norm for k, v in counts.items()}


def classify(text: str, profiles: dict[str, dict[str, float]], n: int = 3) -> str:
    counts: collections.Counter[str] = collections.Counter(
        text[i:i + n] for i in range(len(text) - n + 1))
    norm = math.sqrt(sum(v * v for v in counts.values())) or 1.0
    best, best_score = None, -math.inf
    for lang, prof in profiles.items():
        score = sum(v * prof.get(k, 0.0) for k, v in counts.items()) / norm
        if score > best_score:
            best, best_score = lang, score
    return best                                            # type: ignore[return-value]


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lessons", default="all")
    ap.add_argument("--n-train", dest="n_train", type=int, default=4)
    ap.add_argument("--n-eval", dest="n_eval", type=int, default=2)
    args = ap.parse_args(argv)

    from symbolic_ai_core.data.curriculum import generate, resolve_lessons
    lessons = resolve_lessons(args.lessons)

    train = {lang: [ep.prompt for ep in generate(lessons, n=args.n_train, seed0=0,
                                                 language=lang, max_nodes=128)]
             for lang in PACKS}
    evaluation = {lang: [ep.prompt for ep in generate(lessons, n=args.n_eval,
                                                      seed0=1_000_000,
                                                      language=lang, max_nodes=128)]
                  for lang in PACKS}
    profiles = {lang: profile(texts) for lang, texts in train.items()}

    confusion: dict[tuple[str, str], int] = collections.Counter()
    for lang, texts in evaluation.items():
        for text in texts:
            confusion[(lang, classify(text, profiles))] += 1

    total = sum(confusion.values())
    correct = sum(v for (a, b), v in confusion.items() if a == b)
    per_class = {lang: sum(v for (a, _), v in confusion.items() if a == lang)
                 for lang in PACKS}
    floor = max(per_class.values()) / total

    print(f"language-ID head: character-trigram nearest centroid")
    print(f"  fitted on {sum(len(v) for v in train.values())} training prompts, "
          f"scored on {total} evaluation prompts (seeds from 1,000,000)")
    print(f"  accuracy       {correct / total:.4f}")
    print(f"  majority floor {floor:.4f}")
    print(f"  lift           {(correct / total - floor) / (1 - floor):+.4f}")
    print("\n  per language: recall, and where the errors went")
    for lang in PACKS:
        n = per_class[lang]
        hit = confusion.get((lang, lang), 0)
        wrong = sorted(((v, b) for (a, b), v in confusion.items()
                        if a == lang and b != lang), reverse=True)
        where = ", ".join(f"{b} {v}" for v, b in wrong[:3]) or "-"
        print(f"    {lang:<18} {hit / max(n, 1):.4f}   -> {where}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
