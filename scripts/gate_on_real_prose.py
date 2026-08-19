"""The one domain-independent component, on English nobody here wrote.

`symbolic_ai_generators/staleness.py` is the first component in this repo meant
to transfer across domains unchanged, and every number for it comes from surfaces
this repo generated with distractors the author wrote. Its whole claim is that
its cue list is **closed-class**, so adding a domain does not add words. That is
an argument about how the risk *grows*, not a measurement that it is small.

`data/sources/openalex-prose` holds 5,000 real scientific abstracts. This scores
every sentence in them and reports **which cue fires how often**, because the
aggregate rate is not the interesting number -- whether the fires are genuine
cancellations is.

Run: uv run python -u scripts/gate_on_real_prose.py
"""

from __future__ import annotations

import json
import random
import re
from collections import Counter
from pathlib import Path

from symbolic_ai_generators.staleness import (CANCELLING, TENSE,
                                              stale_by_cancellation,
                                              stale_by_tense)

SRC = Path("data/sources/openalex-prose/openalex-prose-2026-08-18/works_p0.jsonl")
OUT = Path("runs/gate_on_real_prose.json")


def sentences() -> list[str]:
    out = []
    for line in SRC.read_text(errors="ignore").splitlines():
        try:
            rec = json.loads(line)
        except Exception:
            continue
        if rec.get("language") != "en":
            continue
        text = (rec.get("abstract") or "").strip()
        if not text:
            continue
        out += [s.strip() for s in re.split(r"(?<=[.?!])\s+", text)
                if len(s.strip()) > 20]
    return out


def _fires(sentence: str, cues) -> list[str]:
    low = sentence.lower()
    tokens = set(re.findall(r"[a-z]+", low))
    return [c for c in cues
            if (c in low if " " in c else c in tokens)]


def main() -> None:
    sents = sentences()
    n = len(sents)
    print(f"{n} sentences from {SRC.name}\n")

    canc = sum(stale_by_cancellation(s) for s in sents)
    tense = sum(stale_by_tense(s) for s in sents)
    print(f"cancellation gate fires on {canc / n:.4f} of real sentences "
          f"({canc})")
    print(f"tense gate        fires on {tense / n:.4f} of real sentences "
          f"({tense})\n")

    per = Counter()
    alone = Counter()
    for s in sents:
        hits = _fires(s, CANCELLING)
        for h in hits:
            per[h] += 1
        if len(hits) == 1:
            alone[hits[0]] += 1
    print(f"{'cue':<16} {'fires':>8} {'share of fires':>15} {'ONLY cue':>10}")
    print("-" * 54)
    for cue, k in per.most_common():
        print(f"{cue:<16} {k:>8} {k / canc:>15.3f} {alone[cue]:>10}")

    rng = random.Random(0)
    print("\nSamples, for the cues that dominate:")
    for cue, _ in per.most_common(4):
        hits = [s for s in sents if cue in _fires(s, CANCELLING)]
        for s in rng.sample(hits, min(3, len(hits))):
            print(f"  [{cue}] {s[:150]}")
        print()

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({
        "n_sentences": n,
        "cancellation_rate": canc / n,
        "tense_rate": tense / n,
        "per_cue": dict(per), "only_cue": dict(alone)}, indent=2))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
