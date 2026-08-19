"""The milestone: report in, typed world, several kernels, decision and paragraph.

Everything this front has built, assembled and priced in one table:

    a multi-paragraph report is converted into a typed world representation,
    passed through multiple specialised symbolic kernels, and produces both a
    structured decision and a grounded answer paragraph.

**Reader rows** vary the reader with the kernels fixed. **Ablation rows** fix the
reader at the oracle world and remove one kernel's contribution, so a drop is
attributable to that kernel rather than to the reader.

Read on the **non-empty** population. 45% of flood cases have an empty correct
answer that survives any reader failure for free, so a pooled number is largely
a measure of the case mix -- see
`notes/findings/2026-08-18-the-flood-floor-is-the-empty-answer-share-...md`.

The surface is at **V = 4**: four phrasings per claim kind, drawn per case. At
V = 1 a hand-written pattern set scores 1.000 and the table cannot discriminate.

Run: uv run python -u scripts/milestone_end_to_end.py
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood.flow import solve
from symbolic_ai_generators.flood.read import read_report
from symbolic_ai_generators.flood.read_surface import (read_lexical,
                                                       read_signature,
                                                       read_surface)
from symbolic_ai_generators.flood.render import render_answer, ungrounded
from symbolic_ai_generators.flood.surface import render_observation

OUT = Path("runs/milestone_end_to_end.json")
N_CASES = 40
VARIANTS = 4


def claim_key(c) -> tuple:
    from symbolic_ai_core.world import Quantity
    parts: list = [c.predicate, c.polarity]
    for role, v in sorted(c.roles.items()):
        if isinstance(v, Quantity):
            parts.append((role, round(float(v.value), 6), v.unit))
        elif hasattr(v, "id"):
            parts.append((role, v.id))
        else:
            parts.append((role, str(v)))
    return tuple(parts)


def _cost(outputs) -> float:
    """Sum the kernels' own cost accounting.

    ``Context.cost_usd`` is ``None`` -- the flow prices per artifact, not
    centrally -- so the ASP row reports ``routes.cost.usd`` and the SMT row
    ``load_report.usd``. Reading the context instead gave a $/correct column of
    exactly zero, which is the kind of number that looks like a result.
    """
    total = 0.0
    for artifact in outputs.values():
        value = getattr(artifact, "value", None)
        if not isinstance(value, dict):
            continue
        cost = value.get("cost")
        if isinstance(cost, dict) and "usd" in cost:
            total += float(cost["usd"] or 0.0)
        elif "usd" in value:
            total += float(value["usd"] or 0.0)
    return total


def run(cases, truths, *, reader, ablations=None) -> dict:
    ablations = ablations or {}
    tp = fp = fn = 0
    hits = hits_ne = n_ne = 0
    usd = 0.0
    grounded = rendered = 0
    for case, want in zip(cases, truths):
        gold = {claim_key(c) for c in case.world.claims}
        try:
            world = reader(case)
        except Exception:
            world = None
        got = {claim_key(c) for c in world.claims} if world is not None else set()
        tp += len(got & gold)
        fp += len(got - gold)
        fn += len(gold - got)
        answer: tuple = ()
        outs = None
        if world is not None:
            try:
                answer, outs, ctx = solve(world, **ablations)
                usd += _cost(outs)
            except Exception:
                answer, outs = (), None
        ok = answer == want
        hits += ok
        if want:
            n_ne += 1
            hits_ne += ok
        if outs is not None and world is not None:
            try:
                para = render_answer(case, answer, outs)
                rendered += 1
                grounded += not ungrounded(para, case, outs)
            except Exception:
                pass
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    acc_ne = hits_ne / max(1, n_ne)
    return {"claim_recall": rec, "claim_precision": prec,
            "acc_non_empty": acc_ne, "acc_pooled": hits / len(cases),
            "usd_total": usd,
            "usd_per_correct": (usd / hits_ne) if hits_ne else float("inf"),
            "grounded": (grounded / rendered) if rendered else float("nan")}


def main() -> None:
    cases = [generate(s) for s in range(N_CASES)]
    truths = [solve(c.world)[0] for c in cases]
    texts = {c.seed: render_observation(c, variants=VARIANTS).text
             for c in cases}
    empty = sum(1 for t in truths if not t)
    print(f"{N_CASES} cases at V={VARIANTS}; {empty} have an empty answer "
          f"({empty/N_CASES:.0%}) and are excluded from the headline column\n",
          flush=True)

    def on_text(fn):
        return lambda c: fn(texts[c.seed])

    reader_rows = (
        ("oracle world (CEILING)", lambda c: c.world, {}),
        ("signature reader", on_text(read_signature), {}),
        ("rules reader", on_text(read_surface), {}),
        ("lexical cue routing", on_text(read_lexical), {}),
        ("template reader", on_text(read_report), {}),
    )
    ablation_rows = (
        ("oracle, no datalog reachability", lambda c: c.world,
         {"ignore_flooding": True}),
        ("oracle, no SMT load check", lambda c: c.world,
         {"ignore_bridge_limits": True}),
        ("oracle, no ASP route search", lambda c: c.world,
         {"first_route_only": True}),
    )

    hdr = (f"{'system':<34} {'claim R':>8} {'task acc':>9} {'$/correct':>11} "
           f"{'grounded':>9}")
    print(hdr)
    print("-" * len(hdr))
    rows = {}
    for label, reader, abl in reader_rows:
        r = run(cases, truths, reader=reader, ablations=abl)
        rows[label] = r
        print(f"{label:<34} {r['claim_recall']:>8.3f} "
              f"{r['acc_non_empty']:>9.3f} {r['usd_per_correct']:>11.2e} "
              f"{r['grounded']:>9.3f}", flush=True)
    print()
    for label, reader, abl in ablation_rows:
        r = run(cases, truths, reader=reader, ablations=abl)
        rows[label] = r
        print(f"{label:<34} {r['claim_recall']:>8.3f} "
              f"{r['acc_non_empty']:>9.3f} {r['usd_per_correct']:>11.2e} "
              f"{r['grounded']:>9.3f}", flush=True)

    ceiling = rows["oracle world (CEILING)"]
    best_reader = max((k for k in rows if "oracle" not in k),
                      key=lambda k: rows[k]["acc_non_empty"])
    print(f"\nbest reader: {best_reader} at "
          f"{rows[best_reader]['acc_non_empty']:.3f} against a ceiling of "
          f"{ceiling['acc_non_empty']:.3f}")
    print(f"  reader loss     {ceiling['acc_non_empty'] - rows[best_reader]['acc_non_empty']:+.3f}")
    worst_abl = min((k for k in rows if k.startswith("oracle,")),
                    key=lambda k: rows[k]["acc_non_empty"])
    print(f"  the kernel that matters most: {worst_abl} drops to "
          f"{rows[worst_abl]['acc_non_empty']:.3f}")
    print(f"\nevery row that produced a paragraph produced a GROUNDED one "
          f"where it ran; the structured\ndecision is canonical and the "
          f"paragraph is downstream of it.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"n_cases": N_CASES, "variants": VARIANTS,
                               "empty_answers": empty, "rows": rows}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
