"""The north star, computed for the first time with a LEARNED language boundary.

`$ / solved episode above floor` is what this programme says it is optimising,
and every previous computation of it had a hand-written pattern set at the front.
That priced a component nobody could deploy: the patterns were written while
looking at the surface they read. This prices the pipeline that was fitted from
examples instead — one reader implementation, no domain lexicon in its source,
plus the kernels it feeds.

The system is priced **whole**, which is the rule this ledger exists to enforce:
if a reasoner only works because something upstream produced a graph, that
upstream component is in the ledger. Two CPU components per domain — the reader
and the kernels — measured on the same documents that produce the accuracy.

The reader is the **union fit** (original documents plus a per-document renaming
of every entity), because that is the only configuration measured to survive
renaming, and a reader that collapses to 0.000 when the names change is not a
component anyone can deploy at any price.

Also computed, and it is the number worth arguing about: **the accuracy a priced
API would need in order to match this pipeline's cost per solved episode.** That
needs no LLM run and makes no claim about any model's capability — it is
arithmetic on a published price sheet and it is falsifiable by anyone who
measures the accuracy.

Predicted before running:

- The **reader dominates the wall clock and the kernels dominate nothing**, or
  the reverse in flood where ASP and SMT both run. Reading was 96.1% of
  solvency's wall clock when it was regexes; a perceptron over sparse features
  should be the same order.
- `$ / solved above floor` lands between 1e-8 and 1e-5 for all three domains.
- The break-even API accuracy comes out **above 1.0** — i.e. unreachable — which
  would say the comparison is not close enough to be about accuracy at all.

Run: uv run python -u scripts/learned_pipeline_cost.py
"""

from __future__ import annotations

import json
import statistics
import time
from collections import Counter
from pathlib import Path

from symbolic_ai_core.cost import (Capability, Price, System, api_component,
                                   cpu_component, ledger)
from symbolic_ai_core.reader.learned import LearnedSpanReader, supervise

from scripts.learned_reader import induce_schema, world_from_claims
from scripts.reader_survives import build, domains

OUT = Path("runs/learned_pipeline_cost.json")
N_TRAIN = 400
N_EVAL = 120
#: A frontier API's published input price, for the reference row only. No
#: capability claim is attached to it and none is implied.
API_USD_PER_MTOK = 3.0


def floor_of(dom, cases) -> tuple[float, str]:
    """The best a system can do while ignoring the document entirely.

    For a boolean domain that is the majority class. For flood, whose answer is
    a set, it is the commonest answer -- which is usually the empty set, and
    quoting an above-floor number without it has been this repo's most repeated
    mistake.
    """
    answers = [dom["answer"](c.world, c) for c, _, _ in cases]
    common = Counter(map(repr, answers)).most_common(1)[0]
    return common[1] / len(answers), f"constant {common[0][:40]}"


def main() -> None:
    rows = []
    price = Price()
    for name, dom in domains().items():
        print(f"\n=== {name}")
        train = build(dom, range(N_TRAIN))
        renamed = build(dom, range(N_TRAIN), rename=True, rng_seed=1)
        schema = induce_schema([(c, o) for c, o, _ in train])
        docs = [supervise(t, o.spans, c.world.claims) for c, o, t in train]
        docs += [supervise(t, o.spans, c.world.claims) for c, o, t in renamed]

        t0 = time.perf_counter()
        reader = LearnedSpanReader().fit(docs)
        fit_s = time.perf_counter() - t0

        cases = build(dom, range(1_000_000, 1_000_000 + N_EVAL))
        floor, floor_note = floor_of(dom, cases)

        read_s = kernel_s = 0.0
        chars = 0
        hits = 0
        for c, o, text in cases:
            chars += len(text)
            t0 = time.perf_counter()
            claims = reader.run(text).delta().claims
            read_s += time.perf_counter() - t0
            t0 = time.perf_counter()
            try:
                mine = dom["answer"](world_from_claims(claims, schema), c)
            except Exception:
                mine = None
            kernel_s += time.perf_counter() - t0
            hits += mine == dom["answer"](c.world, c)

        # Tokens are counted the way an API would bill them: ~4 characters each.
        tok = chars / 4.0
        tok_per_doc = tok / N_EVAL
        system = System(name=f"{name} learned pipeline").with_component(
            cpu_component("learned reader", tok / read_s,
                          source="measured on the eval documents",
                          stage="parse")).with_component(
            cpu_component("kernels", tok / kernel_s,
                          source="measured on the same documents",
                          stage="reason"))
        cap = Capability(unit="episode", rate=hits / N_EVAL, floor=floor,
                         n=N_EVAL, tokens_per_attempt=tok_per_doc,
                         source=f"floor = {floor_note}")
        row = ledger(system, cap, price=price)

        api = System(name=f"{name} priced API").with_component(
            api_component("frontier API input", API_USD_PER_MTOK,
                          source="published list price, input only"))
        usd_api_attempt = (api.usd_per_btok_in(price) * tok_per_doc / 1e9)
        # What accuracy would that API need for its cost per SOLVED episode,
        # above the same floor, to match this pipeline's?
        need = (usd_api_attempt / row.usd_per_solved_above_floor + floor
                if row.usd_per_solved_above_floor else float("inf"))

        print(f"    accuracy {cap.rate:.3f}  floor {floor:.3f} ({floor_note})")
        print(f"    read {1000 * read_s / N_EVAL:.2f} ms/doc, "
              f"kernels {1000 * kernel_s / N_EVAL:.2f} ms/doc, "
              f"fit once {fit_s:.1f} s")
        print(f"    $/attempt {row.usd_per_attempt:.3e}   "
              f"$/solved-above-floor {row.usd_per_solved_above_floor:.3e}")
        print(f"    dominant component: {system.dominant(price).name}")
        print(f"    a ${API_USD_PER_MTOK}/Mtok API costs "
              f"{usd_api_attempt:.3e} per ATTEMPT -- "
              f"{usd_api_attempt / row.usd_per_attempt:,.0f}x this pipeline")
        # Even at a PERFECT rate the API pays its per-attempt price for every
        # episode, so this is the floor of what it could cost per solved one.
        api_best = usd_api_attempt / (1.0 - floor)
        print(f"    even at accuracy 1.000 the API costs {api_best:.3e} per "
              f"solved-above-floor, {api_best / row.usd_per_solved_above_floor:,.0f}x this")

        # The fit is a one-off and belongs in the ledger, not in a footnote.
        fit_usd = fit_s * price.usd_per_core_second()
        break_even = fit_usd / row.usd_per_attempt
        vs_api = fit_usd / max(1e-30, usd_api_attempt - row.usd_per_attempt)
        print(f"    fitting cost ${fit_usd:.2e} once: it is repaid after "
              f"{break_even:,.0f} episodes against a free reader, and after "
              f"{vs_api:.2f} episodes against the API")
        rows.append({"domain": name, "rate": cap.rate, "floor": floor,
                     "floor_note": floor_note,
                     "read_ms": 1000 * read_s / N_EVAL,
                     "kernel_ms": 1000 * kernel_s / N_EVAL,
                     "fit_seconds": fit_s, "tokens_per_doc": tok_per_doc,
                     "usd_per_attempt": row.usd_per_attempt,
                     "usd_per_solved_above_floor":
                         row.usd_per_solved_above_floor,
                     "dominant": system.dominant(price).name,
                     "api_usd_per_attempt": usd_api_attempt,
                     "api_multiple": usd_api_attempt / row.usd_per_attempt,
                     "api_accuracy_needed": need,
                     "api_usd_per_solved_at_perfect": api_best,
                     "fit_usd": fit_usd,
                     "break_even_episodes_vs_free_reader": break_even,
                     "break_even_episodes_vs_api": vs_api})

    print(f"\n    median API cost multiple: "
          f"{statistics.median(r['api_multiple'] for r in rows):,.0f}x")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rows, indent=2))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
