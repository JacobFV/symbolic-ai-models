"""What accuracy would a language model need to match us on cost?

``state.yml`` records the neural comparison as blocked on paid credentials. That
blocks measuring a model's **accuracy**; it does not block its **price**, which is
published, and ``cost.py`` has ``api_component`` for exactly that.

So ask the question that needs no credentials. Our system costs
``usd_per_attempt / accuracy`` per solved episode. A model at a published rate
costs ``usd_per_attempt_llm / a`` for its accuracy ``a``. Setting them equal:

    a* = usd_per_attempt_llm * our_accuracy / our_usd_per_attempt

**Accuracy is bounded above by 1.** If ``a*`` exceeds 1, no accuracy closes the
gap and the comparison is decided without measuring anything about the model.

Run: uv run python -u scripts/break_even_accuracy.py
"""

from __future__ import annotations

import json
import statistics
import time
from pathlib import Path

from symbolic_ai_core.cost import (Capability, System, api_component,
                                   cpu_component, ledger)

OUT = Path("runs/break_even_accuracy.json")

#: Published list prices, USD per million input tokens. Not measured, not
#: negotiated, and deliberately spanning the range rather than naming a vendor:
#: a small hosted model and a frontier one bracket what anyone would pay.
PRICES = {"small hosted model": 0.15, "frontier model": 3.00}


def _tokens(text: str) -> int:
    return max(1, len(text.split()))


def flood():
    from symbolic_ai_generators.flood import generate
    from symbolic_ai_generators.flood.flow import solve
    from symbolic_ai_generators.flood.read_surface import read_content_roles
    from symbolic_ai_generators.flood.surface import render_observation
    cases = [generate(s) for s in range(40)]
    texts = [render_observation(c, variants=4).text for c in cases]
    truth = [solve(c.world)[0] for c in cases]
    t0 = time.perf_counter()
    worlds = [read_content_roles(t) for t in texts]
    read = time.perf_counter() - t0
    t0 = time.perf_counter()
    got = [solve(w)[0] for w in worlds]
    slv = time.perf_counter() - t0
    ne = [i for i, t in enumerate(truth) if t]
    return (texts, read, slv,
            statistics.mean(got[i] == truth[i] for i in ne),
            1 - len(ne) / len(cases), len(ne))


def scheduling():
    import sys
    sys.path.insert(0, "scripts")
    from hard_regime_milestone import solve_world
    from symbolic_ai_generators.scheduling import generate_hard
    from symbolic_ai_generators.scheduling.read_surface import read_signature
    from symbolic_ai_generators.scheduling.surface import render_observation
    cases = [generate_hard(s) for s in range(20)]
    texts = [render_observation(c, variants=4).text for c in cases]
    truth = [c.feasible for c in cases]
    t0 = time.perf_counter()
    worlds = [read_signature(t) for t in texts]
    read = time.perf_counter() - t0
    t0 = time.perf_counter()
    got = [solve_world(w)[0] for w in worlds]
    slv = time.perf_counter() - t0
    rate = statistics.mean(g == w for g, w in zip(got, truth))
    floor = max(sum(truth), len(truth) - sum(truth)) / len(truth)
    return texts, read, slv, rate, floor, len(cases)


def solvency():
    from symbolic_ai_generators.solvency import decide, generate
    from symbolic_ai_generators.solvency.read_surface import (decide_reading,
                                                              read_signature)
    from symbolic_ai_generators.solvency.surface import render_observation
    cases = [generate(s) for s in range(200)]
    texts = [render_observation(c, variants=4).text for c in cases]
    truth = [decide(c, as_of=c.decision_date)[0] for c in cases]
    t0 = time.perf_counter()
    readings = [read_signature(t) for t in texts]
    read = time.perf_counter() - t0
    t0 = time.perf_counter()
    got = [decide_reading(r) for r in readings]
    slv = time.perf_counter() - t0
    rate = statistics.mean(g == w for g, w in zip(got, truth))
    floor = max(sum(truth), len(truth) - sum(truth)) / len(truth)
    return texts, read, slv, rate, floor, len(cases)


def main() -> None:
    print(f"{'domain':<12} {'tok/ans':>8} {'our $/attempt':>14} "
          f"{'our acc':>8} " + " ".join(f"{k:>22}" for k in PRICES))
    print("-" * 100)
    rows = {}
    for name, probe in (("flood", flood), ("scheduling", scheduling),
                        ("solvency", solvency)):
        texts, read, slv, rate, floor, n = probe()
        toks = sum(_tokens(t) for t in texts)
        per_answer = toks / len(texts)
        system = System(name=name, components=(
            cpu_component(f"{name}.reader", toks / read, stage="read",
                          source="measured"),
            cpu_component(f"{name}.kernel", toks / slv, stage="solve",
                          source="measured")))
        cap = Capability(unit="answer", rate=rate, floor=floor, n=n,
                         tokens_per_attempt=per_answer)
        ours = ledger(system, cap)
        cells, row = [], {"tokens": per_answer, "rate": rate,
                          "usd_per_attempt": ours.usd_per_attempt,
                          "break_even": {}}
        for label, price in PRICES.items():
            llm = ledger(System(name=label, components=(
                api_component(label, price, stage="solve",
                              source="published list price"),)), cap)
            a_star = llm.usd_per_attempt * rate / ours.usd_per_attempt
            row["break_even"][label] = a_star
            cells.append(f"{a_star:>22.0f}")
        rows[name] = row
        print(f"{name:<12} {per_answer:>8.0f} {ours.usd_per_attempt:>14.3e} "
              f"{rate:>8.3f} " + " ".join(cells))

    print(f"\n  break-even accuracy: what a model would need to MATCH us on "
          f"$/solved.")
    print(f"  accuracy cannot exceed 1.")

    worst = min(min(r["break_even"].values()) for r in rows.values())
    print()
    if worst > 1:
        print(f"-> NO ACCURACY CLOSES THE GAP. The smallest break-even "
              f"across three domains and two\n   price points is "
              f"{worst:,.0f} -- an accuracy of {worst:,.0f}, where 1 is "
              f"answering every case\n   correctly. On price per answer the "
              f"comparison is decided without measuring the\n   model at all.")
        print(f"\n   Insensitive to our accuracy, which is quoted here on the "
              f"PUBLISHED surface. On the\n   honest one flood scores 0.500, "
              f"which halves its break-even to about "
              f"{rows['flood']['break_even']['small hosted model'] / 2:,.0f} "
              f"and\n   changes nothing.")
    else:
        print(f"-> break-even below 1 somewhere ({worst:.2f}), so the symbolic "
              f"pipeline does not win on\n   price alone there.")

    print(f"\n   WHAT THIS DOES NOT ESTABLISH, and it matters more than the "
          f"number: our systems\n   work because a reader was HAND-WRITTEN for "
          f"each surface, and the model needs no\n   such engineering. The "
          f"ledger charges the reader's RUNTIME, which is not its\n   "
          f"DEVELOPMENT. A per-answer figure that ignores the engineering is a "
          f"true number\n   answering a narrower question than it appears to -- "
          f"and this repo's own rule is\n   that cost is charged to the system.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"prices_usd_per_mtok_in": PRICES,
                               "rows": rows}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
