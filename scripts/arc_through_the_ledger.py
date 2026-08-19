"""Six arms priced determinacy. None of them measured whether the answer is right.

`HANDOVER.md` §7 item 10 has stood unaddressed since it was written:

> **Put this session's work through `symbolic_ai_core/cost.py`.** Everything here
> was priced with hand-rolled arithmetic in scripts while the repo's own ledger
> sat unused... a number on a different basis from the published ones is not
> comparable with them, which is most of what a ledger is for.

This session then published six arms on a hand-rolled
`advantage(f) = M / (f*M + (1-f)*O)` and never opened the module. That formula is
a **cost ratio at assumed equal accuracy**, and §6 records that exactly this
assumption put four earlier rows out of quotation.

`Capability` refuses to carry a rate without a floor, and
`usd_per_solved_episode_above_floor` divides by `rate - floor`. So running the
arc through it forces the measurement the arc never made: **is the answer
right?** Every number from `f` 14.66% down to 8.17% is a *determinacy* rate —
the system settled — and settling was silently read as being correct.

**The answer key.** The wikidata CIK->LEI bridge resolves 1,015 matched filers
by identifier at both ends. It is therefore usable as ground truth for the name
join — provided it is **excluded from the system being scored**, or the
measurement is circular. It is excluded here, which is why the systems below are
name-join and closure only.

**Two levels, because the arc answers at two.** Entity level asks which LEI;
group level asks which corporate group, which is what closure actually settles.
Each gets its own floor: **pick uniformly at random among the name candidates**,
which already gets every unambiguous filer right and is therefore a strong floor,
as a floor should be.

Run: uv run python -u scripts/arc_through_the_ledger.py
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from scripts.alignment_bounds import SEC, gleif_candidates
from scripts.manufactured_reach import CONSOLIDATION, FUNDS, roots_from
from scripts.wikidata_bridge_cik_lei import load_bridge
from symbolic_ai_core.cost import (Capability, Price, System, api_component,
                                   cpu_component, ledger, ledger_table)
from symbolic_ai_tasks.company_key import (fit_strip_set, load_task,
                                           predict_fitted)
from symbolic_ai_tasks.cross_source_alignment import AlignmentResult

OUT = Path("runs/arc_through_the_ledger.json")
SEED = 20260818
#: HANDOVER §3: necessary context for one GLEIF point query, mean over 117,129.
DEP_TOKENS = 41.0
#: 2.8 us per scoped point query -> tokens/sec for a cpu component of that cost.
SYMBOLIC_TOKENS_PER_SEC = DEP_TOKENS / 2.8e-6
FRONTIER_USD_PER_MTOK = 15.0


def main() -> None:
    rng = random.Random(SEED)
    task = load_task(SEC)
    strip = fit_strip_set(task, task.ids)
    keys = predict_fitted(task, strip)
    index = gleif_candidates(strip, set(keys.values()))
    results = {f: AlignmentResult(filer=f, key=k, candidates=tuple(index[k]))
               for f, k in keys.items() if k in index}
    bridge = load_bridge()

    truth = {f: "kg:lei:" + bridge[f.split(":")[-1].lstrip("0")]
             for f in results if f.split(":")[-1].lstrip("0") in bridge}
    scored = {f: results[f] for f in truth}
    amb = {f for f, r in scored.items() if r.ambiguous}
    print(f"{len(results):,} matched filers; {len(scored):,} have a "
          f"ground-truth LEI from the bridge")
    print(f"  of those, {len(amb):,} = {len(amb)/len(scored):.1%} are "
          f"ambiguous under the name join\n", flush=True)

    # --- the honest first number, which no arm in this session computed:
    # is the right LEI even IN the candidate set? Everything downstream is
    # bounded by this, and a resolver cannot beat it.
    recall = sum(1 for f, r in scored.items()
                 if truth[f] in {c.entity for c in r.candidates})
    print(f"CEILING: the true LEI is among the name candidates for "
          f"{recall:,}/{len(scored):,} = {recall/len(scored):.1%} of filers.")
    print(f"  No policy over these candidates can score above that.\n")

    root = roots_from(CONSOLIDATION + FUNDS)

    def group(e: str) -> str:
        return root.get(e, e)

    # --- FLOOR: pick uniformly at random among the candidates. Strong by
    # construction, because an unambiguous filer has one candidate and the
    # floor takes it for free. That is what makes it the right floor.
    def floor_rate(level) -> float:
        hits = 0
        for f, r in scored.items():
            pick = rng.choice([c.entity for c in r.candidates])
            hits += level(pick) == level(truth[f])
        return hits / len(scored)

    # --- SYSTEM: name join, plus closure at group level. Scored TWO ways,
    # because the difference between them is the single largest harness effect
    # in this repo's history (CLAUDE.md: "abstention falling back to the
    # structural prior").
    #
    #   ABSTAIN   an unsettled case scores zero.
    #   FALLBACK  an unsettled case falls back to the floor's own policy,
    #             which is what any deployed system would do.
    #
    # Scoring only the first compares a system that refuses to guess against a
    # floor that always guesses, and the floor wins for that reason alone. The
    # first version of this script did exactly that and reported the symbolic
    # layer at -7.5% below floor.
    def system_rate(level) -> tuple[float, float, float]:
        hits = settled = fallback_hits = 0
        for f, r in scored.items():
            vals = {level(c.entity) for c in r.candidates}
            if len(vals) == 1:
                settled += 1
                ok = vals.pop() == level(truth[f])
                hits += ok
                fallback_hits += ok
            else:
                pick = rng.choice([c.entity for c in r.candidates])
                fallback_hits += level(pick) == level(truth[f])
        n = len(scored)
        return hits / n, fallback_hits / n, settled / n

    rows = {}
    for name, level in (("entity", lambda e: e), ("group", group)):
        fl = floor_rate(level)
        abstain, fallback, settled = system_rate(level)
        rows[name] = {"floor": fl, "rate_abstain": abstain,
                      "rate": fallback, "settled": settled,
                      "above_floor": fallback - fl,
                      "above_floor_abstain": abstain - fl}
        print(f"{name.upper()} level")
        print(f"  system settles                    {settled:>7.1%}")
        print(f"  correct, ABSTAINING on the rest   {abstain:>7.1%}   "
              f"({abstain-fl:+.1%} vs floor)")
        print(f"  correct, FALLING BACK on the rest {fallback:>7.1%}   "
              f"({fallback-fl:+.1%} vs floor)   <- what a deployed system does")
        print(f"  random-candidate floor            {fl:>7.1%}\n")

    # --- the ledger. Symbolic-only, hybrid at the measured f, model-only.
    price = Price()
    sym = System(name="federated symbolic resolver", components=(
        cpu_component("scoped point query", SYMBOLIC_TOKENS_PER_SEC,
                      source="HANDOVER §3: 2.8 us per scoped point query"),))
    api = System(name="frontier model only", components=(
        api_component("frontier model", FRONTIER_USD_PER_MTOK,
                      source="list price, input tokens only"),))
    lvl = rows["group"]
    f_esc = 1.0 - lvl["settled"]
    hybrid = System(name=f"hybrid, escalating {f_esc:.1%}", components=(
        cpu_component("scoped point query", SYMBOLIC_TOKENS_PER_SEC,
                      source="HANDOVER §3"),
        api_component("frontier model on the escalated share",
                      FRONTIER_USD_PER_MTOK * f_esc,
                      source=f"list price x measured escalation share {f_esc:.3f}"),))

    def cap(rate: float, floor: float) -> Capability:
        return Capability(unit="aligned filer", rate=rate, floor=floor,
                          n=len(scored), tokens_per_attempt=DEP_TOKENS,
                          source="scripts/arc_through_the_ledger.py")

    # The hybrid's escalated share is assumed answered PERFECTLY -- the same
    # generous assumption every cost row in this repo uses, and for the same
    # reason: the comparison is blocked on credentials (§6) and a bound that
    # assumes the opponent is perfect needs none.
    # the escalated share is the part the system does not settle; it is
    # assumed answered perfectly, so it replaces the fallback guess there.
    hybrid_rate = lvl["rate_abstain"] + f_esc * 1.0
    ledgers = [
        ledger(sym, cap(lvl["rate"], lvl["floor"]), price=price,
               basis="measured"),
        ledger(hybrid, cap(min(1.0, hybrid_rate), lvl["floor"]), price=price,
               basis="measured"),
        ledger(api, cap(1.0, lvl["floor"]), price=price, basis="measured"),
    ]
    print(ledger_table(ledgers))

    print("\nThe column that matters is the LAST one. $/answer is a cost ratio "
          "at assumed\nequal accuracy -- the assumption §6 says put four "
          "earlier rows out of quotation.\n$/answer ABOVE FLOOR divides by what "
          "the system bought that the floor did not.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {"seed": SEED, "n_scored": len(scored), "ceiling_recall": recall / len(scored),
         "levels": rows, "escalated_share": f_esc,
         "ledgers": [x.as_dict() for x in ledgers]}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
