"""How far does a reader written for one phrasing carry to another?

`scripts/reader_arms.py` put the rules arm at **1.000** on the five-paragraph
surface. That proves the surface is *fair* and nothing about reading: the
patterns were written for that exact phrasing, so the arm is arm zero for a
different template -- the artefact `read.py`'s own docstring warns about,
reproduced one level up.

The discriminating measurement is a **generalisation curve**. Each claim kind now
has four alternative phrasings, varying lexicon rather than word order
(*weighs* / *kerb weight* / *unladen* / *tare*), drawn per case deterministically.
The readers are unchanged -- their patterns and cue words were written against
variant 0 only. Sweeping the number of variants in play asks the only question
that matters here:

> **Does any hand-authored reader survive the words changing?**

If both the pattern arm and the lexical arm collapse, the argument for a learned
or retrieval-based reader is made by measurement rather than by assertion.

Run: uv run python -u scripts/reader_generalisation.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from reader_arms import claim_key, dependency_set, score_arm  # noqa: E402
from symbolic_ai_generators.flood import generate  # noqa: E402
from symbolic_ai_generators.flood.flow import solve  # noqa: E402
from symbolic_ai_generators.flood.read_surface import (  # noqa: E402
    read_lexical, read_surface)
from symbolic_ai_generators.flood.surface import render_observation  # noqa: E402

OUT = Path("runs/reader_generalisation.json")
N_CASES = 40
VARIANTS = (1, 2, 3, 4)


def main() -> None:
    cases = [generate(s) for s in range(N_CASES)]
    truths = [solve(c.world)[0] for c in cases]
    deps = [dependency_set(c) for c in cases]
    print(f"{N_CASES} cases; readers unchanged, patterns written for variant 0 "
          f"only\n", flush=True)

    hdr = (f"{'reader':<22} {'V':>3} {'claim R':>9} {'dep R':>7} "
           f"{'non-empty':>10} {'alignment':>10}")
    print(hdr)
    print("-" * len(hdr))
    rows = []
    for name, fn in (("rules, full", read_surface),
                     ("lexical cue routing", read_lexical)):
        for v in VARIANTS:
            # the alignment must stay complete however the words change, or the
            # curve is measuring a broken ground truth rather than a reader
            covered = all(
                set(range(len(c.world.claims)))
                <= render_observation(c, variants=v).covered() for c in cases)
            r = score_arm(
                f"{name} V={v}",
                lambda c, v=v, fn=fn: fn(render_observation(c, variants=v).text),
                cases, truths, deps)
            r["variants"], r["reader"] = v, name
            r["alignment_complete"] = covered
            rows.append(r)
            print(f"{name:<22} {v:>3} {r['claim_recall']:>9.3f} "
                  f"{r['dependency_recall']:>7.3f} "
                  f"{r['accuracy_non_empty']:>10.3f} "
                  f"{'ok' if covered else 'BROKEN':>10}", flush=True)

    print()
    for name in ("rules, full", "lexical cue routing"):
        a = next(r for r in rows if r["reader"] == name and r["variants"] == 1)
        b = next(r for r in rows if r["reader"] == name and r["variants"] == 4)
        print(f"  {name:<22} V=1 -> V=4:  recall {a['claim_recall']:.3f} -> "
              f"{b['claim_recall']:.3f}   accuracy "
              f"{a['accuracy_non_empty']:.3f} -> {b['accuracy_non_empty']:.3f}")

    worst = max(r["accuracy_non_empty"] for r in rows if r["variants"] == 4)
    print(f"\n  best non-empty accuracy at V=4, over both readers: {worst:.3f}")
    if worst < 0.15:
        print(f"\n-> NO HAND-AUTHORED READER SURVIVES THE WORDS CHANGING. Both "
              f"a pattern set and\n   a cue-word router are written against a "
              f"phrasing, and four phrasings per\n   kind is enough to take "
              f"both to the floor. The argument for a learned or\n   "
              f"retrieval-based reader is now a measurement.")
    else:
        print(f"\n-> something survives: {worst:.3f} at V=4.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"n_cases": N_CASES, "rows": rows}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
