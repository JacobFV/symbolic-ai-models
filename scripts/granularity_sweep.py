"""Is a clause the right unit, or just a smaller one?

*"The unit of staleness is a clause, not a sentence"* answers which of **two**
units, not whether there is an optimum. If the rule were simply *cut as small as
possible*, the clause result would be a way-station and the finest split would
win.

Five granularities, on the corpus where the failure was found and on the
generated surface built to reproduce it:

- **document** -- no filtering at all, the naive arm;
- **sentence** -- the shipped default;
- **clause** -- commas, semicolons, colons, contrastive conjunctions;
- **fine** -- also coordinators and relative pronouns;
- **finest** -- also prepositional heads, which cut *through* the patterns
  themselves.

Run: uv run python -u scripts/granularity_sweep.py
"""

from __future__ import annotations

import json
import re
import statistics
import sys
from pathlib import Path

from symbolic_ai_generators.solvency import decide, generate
from symbolic_ai_generators.solvency import surface as VS
from symbolic_ai_generators.solvency.read_surface import (
    decide_reading, read_signature_accumulating)
from symbolic_ai_generators.staleness import stale_by_cancellation

sys.path.insert(0, str(Path(__file__).parent))
from wikipedia_parents import SRC, _names, candidates, hit  # noqa: E402

OUT = Path("runs/granularity_sweep.json")

SPLITTERS = {
    "document": None,
    "sentence": re.compile(r"(?!x)x"),                 # never matches
    "clause": re.compile(r"[,;:]|\s+(?:but|although|though)\s+"),
    "fine": re.compile(r"[,;:()]|\s+(?:but|although|though|and|or|which|"
                       r"that|while|where|when)\s+"),
    "finest": re.compile(r"[,;:()]|\s+(?:but|although|though|and|or|which|"
                         r"that|while|where|when|of|in|for|by|from|to)\s+"),
}


def sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text)
    return [s.strip() for s in re.split(r"(?<=[.?!])\s+(?=[A-Z(])", text)
            if s.strip()]


def filter_at(text: str, unit: str) -> str:
    split = SPLITTERS[unit]
    if split is None:
        return text
    kept = []
    for sent in sentences(text):
        if not stale_by_cancellation(sent):
            kept.append(sent)
            continue
        parts = [p.strip().rstrip(".") for p in split.split(sent) if p.strip()]
        live = [p for p in parts if not stale_by_cancellation(p)]
        if live:
            kept.append(" ".join(live) + ".")
    return " ".join(kept)


def wikipedia() -> dict:
    rows = [json.loads(x) for x in SRC.read_text().splitlines() if x.strip()]
    out = {}
    for unit in SPLITTERS:
        guesses = [(r, (candidates(filter_at(r["intro"], unit)) or [""])[0])
                   for r in rows]
        answered = [(r, g) for r, g in guesses if g]
        correct = [1 for r, g in answered
                   if _names(g, r.get("current") or [r["parent"]])
                   or hit(g, r["parent"])]
        former = [1 for r, g in answered
                  if r.get("former") and _names(g, r["former"])
                  and not hit(g, r["parent"])]
        out[unit] = {"answers": len(answered) / len(rows),
                     "accuracy": len(correct) / len(rows),
                     "picks_former": len(former) / len(rows)}
    return out


def solvency(n: int = 120) -> dict:
    out = {}
    for unit in SPLITTERS:
        ok = []
        for s in range(n):
            case = generate(s)
            want = decide(case, as_of=case.decision_date)[0]
            text = VS.render_observation(case, variants=4,
                                         stale_clause=True).text
            text = "\n\n".join(filter_at(p, unit)
                               for p in text.split("\n\n"))
            ok.append(decide_reading(read_signature_accumulating(text)) == want)
        out[unit] = {"accuracy": statistics.mean(ok)}
    return out


def main() -> None:
    w = wikipedia()
    print(f"WIKIPEDIA, 168 company intros")
    print(f"{'granularity':<12} {'answers':>9} {'accuracy':>10} "
          f"{'picks former':>14}")
    print("-" * 50)
    for unit, r in w.items():
        print(f"{unit:<12} {r['answers']:>9.3f} {r['accuracy']:>10.3f} "
              f"{r['picks_former']:>14.3f}")

    s = solvency()
    print(f"\nSOLVENCY stale_clause, accumulating reader, 120 seeds")
    print(f"{'granularity':<12} {'accuracy':>10}")
    print("-" * 26)
    for unit, r in s.items():
        print(f"{unit:<12} {r['accuracy']:>10.3f}")

    best_w = max(w, key=lambda u: w[u]["accuracy"])
    best_s = max(s, key=lambda u: s[u]["accuracy"])
    print(f"\nbest on real prose: {best_w}; best on the generated case: "
          f"{best_s}.")
    print("A monotone curve would say 'cut as fine as you can'. A peak says the")
    print("unit is a real linguistic object, and the finest split cuts THROUGH")
    print("the patterns the reader is looking for.")

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({"wikipedia": w, "solvency": s}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
