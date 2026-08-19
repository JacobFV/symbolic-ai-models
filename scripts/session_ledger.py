"""This session's work, priced by the repo's own ledger instead of by hand.

Everything measured this session was priced with hand-rolled arithmetic in
scripts, while `symbolic_ai_core/cost.py` — which exists to compute exactly this
— sat unused. That is not a small thing: the module encodes the conventions a
number has to satisfy to be **comparable with everything already published**,
and the biggest of them is that it divides by ``rate - floor`` rather than by
``rate``. `scripts/query_floors.py` now supplies the floors that makes this
computable, so the numbers can enter the repo's ledger rather than sitting beside
it.

Two systems, one capability each, one price sheet.

**The symbolic system is charged for everything**, which is the module's whole
reason for existing: *"There is no way to express 'our part is free' without also
expressing what the other parts cost."* So the extraction pass that builds the
world is a component of the query system, not a free precondition — the same rule
that produced this session's finding that every published advantage sits
downstream of an unpriced arrow.

**The model opponent is charged as an API row at published rates**, input tokens
only and zero output, and its capability is entered at **1.0 with a floor of 0** —
perfect, free of hallucination, and it still has to beat what a real measured
system does above its own floor. That is deliberately the most generous
assumption available, because the accuracy comparison is blocked on credentials
(`ROADMAP.md` item 0b) and a bound that assumes the opponent is perfect needs no
credentials to stand.

Run: uv run python -u scripts/session_ledger.py
"""

from __future__ import annotations

import json
from pathlib import Path

from symbolic_ai_core.cost import (Capability, Component, Price, System,
                                   api_component, ledger)

OUT = Path("runs/session_ledger.json")

#: Measured this session. Sources are named so a reader can audit each one.
WORKS = 5_000
#: scripts/two_arrows_end_to_end.py — 0.9 s to extract 5,000 works' affiliations
EXTRACT_SECONDS = 0.9
#: the affiliation text the extractor reads, chars/4
EXTRACT_TOKENS = 1_268_408
#: scripts/first_arrow_prose.py — mean necessary context for one query
DEPENDENCY_TOKENS = 302.3

#: scripts/query_floors.py, and the systems they are floors for.
CAPABILITIES = {
    "collaborators(institution)": dict(rate=0.417, floor=0.120, n=1913),
    "works_at(institution)":      dict(rate=0.671, floor=0.027, n=2000),
    "works_at_both(A,B)":         dict(rate=0.465, floor=0.022, n=2000),
    "institutions_of(work)":      dict(rate=0.576, floor=0.034, n=5000),
}


def main() -> None:
    price = Price()

    # The symbolic system: one CPU component doing extraction, priced from its
    # measured throughput. The query itself is microseconds and is dwarfed by
    # the build; it is folded in rather than given a flattering separate row.
    tok_per_sec = EXTRACT_TOKENS / EXTRACT_SECONDS
    symbolic = System(
        name="symbolic (registry extractor + query)",
        components=(Component(
            name="zero-shot ROR extraction",
            kind="cpu",
            tokens_per_sec=tok_per_sec,
            source=("scripts/two_arrows_end_to_end.py: 1,268,408 tokens of "
                    "affiliation text in 0.9 s on one core")),))

    # The opponent: reads the dependency, at published frontier rates, input
    # only, zero output.
    model = System(
        name="frontier model reading the dependency",
        components=(api_component("frontier LM", usd_per_mtok_in=15.0),))

    print(f"price sheet: ${price.usd_per_core_hour}/core-hour, "
          f"frontier $15/Mtok in")
    print(f"symbolic extraction throughput: {tok_per_sec:,.0f} tok/s "
          f"(measured, one core)\n")

    hdr = (f"{'capability':<30} {'rate':>6} {'floor':>7} {'above':>7} "
           f"{'$/answer above floor':>22} {'model $ (perfect)':>19} {'ratio':>12}")
    print(hdr)
    print("-" * len(hdr))

    rows = {}
    for name, c in CAPABILITIES.items():
        cap = Capability(unit="answer", rate=c["rate"], floor=c["floor"],
                         n=c["n"], tokens_per_attempt=DEPENDENCY_TOKENS,
                         source="scripts/query_floors.py + the two-arrows arm")
        ours = ledger(symbolic, cap, price=price)
        # The opponent is entered at perfection: rate 1.0, floor 0.
        theirs = ledger(model,
                        Capability(unit="answer", rate=1.0, floor=0.0,
                                   n=c["n"],
                                   tokens_per_attempt=DEPENDENCY_TOKENS,
                                   source="assumed perfect; see docstring"),
                        price=price)
        o = ours.usd_per_solved_above_floor
        t = theirs.usd_per_solved_above_floor
        rows[name] = {"rate": c["rate"], "floor": c["floor"],
                      "above_floor": cap.above_floor(),
                      "ours_usd_above_floor": o, "theirs_usd_perfect": t,
                      "ratio": (t / o) if o else float("inf")}
        print(f"{name:<30} {c['rate']:>6.3f} {c['floor']:>7.3f} "
              f"{cap.above_floor():>7.3f} {o:>22.3e} {t:>19.3e} "
              f"{rows[name]['ratio']:>11,.0f}x")

    print("\nEvery row charges the symbolic side for BUILDING the world it "
          "answers from,\nand grants the model perfect accuracy for free. The "
          "ratio is therefore a\nlower bound on the advantage and needs no API "
          "credentials to stand.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {"price": {"usd_per_core_hour": price.usd_per_core_hour,
                   "frontier_usd_per_mtok_in": 15.0},
         "symbolic_tokens_per_sec": tok_per_sec,
         "dependency_tokens": DEPENDENCY_TOKENS, "rows": rows}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
