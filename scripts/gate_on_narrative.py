"""The second genre, and the one that tests the corrections hardest.

`scripts/gate_on_real_prose.py` measures the staleness gate on scientific
abstracts, where the dominant error was the **passive of use** and narrative past
barely occurs. Narrative is the opposite draw: habitual *used to* genuinely
appears, *once* is a staple, and the past tense is the default. If the two
corrections made against abstracts survive here, they are about English rather
than about one corpus.

It also measures the thing the abstract corpus could not: the **false-negative**
cost of the three-token lookback, which suppresses a habitual *used to* sitting
near a form of *be*.

Project Gutenberg, public domain, fetched at under one request per second.

Run: uv run python -u scripts/gate_on_narrative.py
"""

from __future__ import annotations

import json
import random
import re
import time
import urllib.request
from collections import Counter
from pathlib import Path

from symbolic_ai_generators.staleness import (CANCELLING, CANCELLING_V1,
                                              stale_by_cancellation,
                                              stale_by_tense)

CACHE = Path("data/artifacts/gutenberg")
OUT = Path("runs/gate_on_narrative.json")
UA = "symbolic-ai-models research bot"

#: Public-domain novels, a spread of authors and decades so the sample is not
#: one writer's habits.
BOOKS = {1342: "Pride and Prejudice", 84: "Frankenstein",
         1400: "Great Expectations", 2701: "Moby Dick",
         345: "Dracula", 76: "Huckleberry Finn",
         158: "Emma", 174: "Dorian Gray",
         1260: "Jane Eyre", 2600: "War and Peace",
         98: "A Tale of Two Cities", 768: "Wuthering Heights"}


def fetch(pid: int) -> str:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{pid}.txt"
    if path.exists():
        return path.read_text(errors="ignore")
    url = f"https://www.gutenberg.org/cache/epub/{pid}/pg{pid}.txt"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read().decode("utf-8", errors="ignore")
    path.write_text(body)
    time.sleep(1.1)
    return body


def sentences(text: str) -> list[str]:
    # drop the licence header and footer, which are boilerplate in every file
    start = text.find("*** START")
    end = text.find("*** END")
    body = text[start:end] if start != -1 and end != -1 else text
    body = re.sub(r"\s+", " ", body)
    return [s.strip() for s in re.split(r"(?<=[.?!])\s+", body)
            if 40 < len(s.strip()) < 600 and len(s.split()) >= 8]


def _fires(sentence: str, cues) -> list[str]:
    low = sentence.lower()
    tokens = set(re.findall(r"[a-z]+", low))
    return [c for c in cues if (c in low if " " in c else c in tokens)]


def main() -> None:
    sents: list[str] = []
    for pid, title in BOOKS.items():
        try:
            sents += sentences(fetch(pid))
        except Exception as e:
            print(f"{title}: {type(e).__name__} {e}")
    n = len(sents)
    print(f"{n} sentences from {len(BOOKS)} novels\n")

    canc = sum(stale_by_cancellation(s) for s in sents)
    v1 = sum(stale_by_cancellation(s, cues=CANCELLING_V1) for s in sents)
    tense = sum(stale_by_tense(s) for s in sents)
    print(f"cancellation gate (corrected) fires on {canc / n:.4f}  ({canc})")
    print(f"cancellation gate (V1 list)   fires on {v1 / n:.4f}  ({v1})")
    print(f"tense gate                    fires on {tense / n:.4f}  ({tense})\n")

    per = Counter()
    for s in sents:
        for h in _fires(s, CANCELLING):
            per[h] += 1
    print(f"{'cue':<16} {'fires':>8} {'share':>8}")
    print("-" * 34)
    for cue, k in per.most_common():
        print(f"{cue:<16} {k:>8} {k / max(canc, 1):>8.3f}")

    # The measurement the abstract corpus could not make: how often does the
    # three-token lookback SUPPRESS a `used to` in a genre where the passive of
    # `use` is rare and the habitual is common?
    from symbolic_ai_generators.staleness import _habitual_past
    used_to = [s for s in sents if re.search(r"\bused to\b", s.lower())]
    suppressed = [s for s in used_to if not _habitual_past(s.lower())]
    print(f"\n'used to' occurs in {len(used_to)} sentences; the clause-bounded "
          f"lookback suppresses {len(suppressed)} "
          f"({len(suppressed) / max(len(used_to), 1):.3f}).")
    rng = random.Random(0)
    for s in rng.sample(suppressed, min(4, len(suppressed))):
        print(f"  [suppressed] {s[:150]}")

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({
        "n_sentences": n, "cancellation_rate": canc / n,
        "cancellation_rate_v1": v1 / n, "tense_rate": tense / n,
        "per_cue": dict(per), "used_to_total": len(used_to),
        "used_to_suppressed": len(suppressed)}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
