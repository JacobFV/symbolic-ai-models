"""The measurement harness every reader arm is scored on. Arm zero included.

`APPROACH.md` and the programme directive both say the same thing: score the
reader at the **world** level and at **end-to-end task success**, keep the
oracle world as a ceiling, and never report one opaque number. This builds that
harness once, so every later arm is a function passed to it.

Three things it insists on:

**The two populations are reported separately.**
`notes/findings/2026-08-18-the-flood-floor-is-the-empty-answer-share-...md`
showed that 45% of flood cases have an **empty** correct answer, which survives
any amount of reader failure for free. A pooled score is 45% a measure of the
case mix, so the harness prints pooled *and* non-empty and treats the non-empty
column as the result.

**Dependency-weighted recall, not just global recall.** A reader can miss many
claims and lose nothing if the answer did not depend on them. The dependency set
is measured by ablation -- drop a claim, re-solve, see if the answer moves -- so
this is a measurement rather than a heuristic weighting.

**Arm zero is the existing template reader on the new surface.** It is not a
strawman: it is the repo's only reader, and its regexes are keyed to the *old*
report's phrasings. What it scores here is the honest starting point of the
text→world front.

Run: uv run python -u scripts/reader_arms.py
"""

from __future__ import annotations

import dataclasses
import json
import statistics
from pathlib import Path
from typing import Callable

from symbolic_ai_core.world import Quantity, WorldSnapshot
from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood.flow import solve
from symbolic_ai_generators.flood.read import read_report
from symbolic_ai_generators.flood.read_surface import read_lexical, read_surface
from symbolic_ai_generators.flood.surface import render_observation

OUT = Path("runs/reader_arms.json")
N_CASES = 40


def claim_key(c) -> tuple:
    """A claim identity that ignores object identity but not content."""
    parts: list = [c.predicate, c.polarity]
    for role, v in sorted(c.roles.items()):
        if isinstance(v, Quantity):
            parts.append((role, round(float(v.value), 6), v.unit))
        elif hasattr(v, "id"):
            parts.append((role, v.id))
        else:
            parts.append((role, str(v)))
    return tuple(parts)


def dependency_set(case) -> set[tuple]:
    """Claims whose individual removal moves the answer."""
    base = solve(case.world)[0]
    out = set()
    for i, c in enumerate(case.world.claims):
        w = dataclasses.replace(
            case.world,
            claims=tuple(x for j, x in enumerate(case.world.claims) if j != i))
        try:
            got = solve(w)[0]
        except Exception:
            got = None
        if got != base:
            out.add(claim_key(c))
    return out


def score_arm(name: str, reader: Callable[[object], WorldSnapshot | None],
              cases, truths, deps) -> dict:
    tp = fp = fn = 0
    dep_tp = dep_n = 0
    #: per-kind recall over the CRITICAL claims only, which is what the refined
    #: law needs. Global per-kind recall would count claims the answer never
    #: depended on.
    kind_tp: dict[str, int] = {}
    kind_n: dict[str, int] = {}
    hits = hits_ne = n_ne = 0
    errors = 0
    for case, want, dep in zip(cases, truths, deps):
        gold = {claim_key(c) for c in case.world.claims}
        try:
            got_world = reader(case)
        except Exception:
            got_world = None
        got = ({claim_key(c) for c in got_world.claims}
               if got_world is not None else set())
        tp += len(got & gold)
        fp += len(got - gold)
        fn += len(gold - got)
        dep_tp += len(dep & got)
        dep_n += len(dep)
        for key in dep:
            kind = key[0]
            kind_n[kind] = kind_n.get(kind, 0) + 1
            kind_tp[kind] = kind_tp.get(kind, 0) + (key in got)
        if got_world is None:
            answer = ()
            errors += 1
        else:
            try:
                answer = solve(got_world)[0]
            except Exception:
                answer = ()
                errors += 1
        ok = answer == want
        hits += ok
        if want:
            n_ne += 1
            hits_ne += ok
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    per_kind = {k: kind_tp.get(k, 0) / n for k, n in kind_n.items() if n}
    crit_per_case = {k: n / len(cases) for k, n in kind_n.items()}
    return {"arm": name, "claim_precision": prec, "claim_recall": rec,
            "critical_recall_by_kind": per_kind,
            "critical_per_case_by_kind": crit_per_case,
            "claim_f1": (2 * prec * rec / (prec + rec)) if prec + rec else 0.0,
            "dependency_recall": dep_tp / dep_n if dep_n else float("nan"),
            "accuracy_pooled": hits / len(cases),
            "accuracy_non_empty": hits_ne / max(1, n_ne),
            "n_non_empty": n_ne, "solve_errors": errors}


def main() -> None:
    cases = [generate(s) for s in range(N_CASES)]
    truths = [solve(c.world)[0] for c in cases]
    print(f"{N_CASES} cases; measuring dependency sets by ablation ...",
          flush=True)
    deps = [dependency_set(c) for c in cases]
    empty = sum(1 for t in truths if not t)
    print(f"  {empty}/{N_CASES} have an EMPTY answer ({empty/N_CASES:.0%}); "
          f"mean dependency {statistics.mean(len(d) for d in deps):.2f} "
          f"claims\n", flush=True)

    def on_surface(fn, **kw):
        """Every reader arm sees the TEXT and nothing else."""
        return lambda c: fn(render_observation(c).text, **kw)

    arms = (
        ("oracle world (CEILING)", lambda c: c.world),
        ("template reader, OLD report", lambda c: read_report(c.report)),
        ("0  template, NEW surface", on_surface(read_report)),
        ("1  rules, full", on_surface(read_surface)),
        ("2  rules, no coreference", on_surface(read_surface, coref=False)),
        ("3  rules, distractors admitted",
         on_surface(read_surface, reject_distractors=False)),
        ("4  lexical cue routing", on_surface(read_lexical)),
        ("   empty world (no reader)",
         lambda c: dataclasses.replace(c.world, claims=())),
    )
    hdr = (f"{'arm':<30} {'claim P':>8} {'claim R':>8} {'dep R':>7} "
           f"{'acc pooled':>11} {'acc non-empty':>14}")
    print(hdr)
    print("-" * len(hdr))
    rows = []
    for name, fn_ in arms:
        r = score_arm(name, fn_, cases, truths, deps)
        rows.append(r)
        print(f"{name:<30} {r['claim_precision']:>8.3f} "
              f"{r['claim_recall']:>8.3f} {r['dependency_recall']:>7.3f} "
              f"{r['accuracy_pooled']:>11.3f} {r['accuracy_non_empty']:>14.3f}",
              flush=True)

    # --- the law's first predictive use. It says end-to-end success tracks
    # DEPENDENCY-weighted recall, not global recall. An arm whose global recall
    # is high and whose dependency recall is low should fall much further than
    # the global number suggests.
    print(f"\nglobal recall vs dependency recall -- the law says the second "
          f"one predicts:\n")
    print(f"  {'arm':<30} {'global R':>9} {'dep R':>7} {'non-empty':>10}")
    for r in rows:
        if r["arm"].startswith(("0", "1", "2", "3", "4")):
            print(f"  {r['arm']:<30} {r['claim_recall']:>9.3f} "
                  f"{r['dependency_recall']:>7.3f} "
                  f"{r['accuracy_non_empty']:>10.3f}")

    # --- the refined law. The sweep that fitted S = q^k dropped claims at
    # RANDOM; a reader loses SYSTEMATICALLY -- arm 2 loses the demand in every
    # case -- and systematic loss is not exchangeable with random loss of the
    # same size. The per-kind form makes that explicit:
    #
    #     S  =  prod_kind  q_kind ^ d_kind
    #
    # with d_kind the ablation-measured critical claims of that kind per case.
    # A kind lost entirely sends its factor, and the product, to zero -- which
    # no single-q model can express.
    K_GLOBAL = 8.31
    print(f"\ntwo forms of the survival law against measurement:\n")
    print(f"  {'arm':<30} {'dep R':>7} {'q^k':>8} {'prod q^d':>10} "
          f"{'measured':>10}")
    for r in rows:
        if not r["arm"][0] in "01234":
            continue
        q = r["dependency_recall"]
        flat = q ** K_GLOBAL
        prod = 1.0
        for kind, d in r["critical_per_case_by_kind"].items():
            qk = r["critical_recall_by_kind"].get(kind, 0.0)
            prod *= qk ** d if qk > 0 else 0.0
        r["law_flat"], r["law_per_kind"] = flat, prod
        print(f"  {r['arm']:<30} {q:>7.3f} {flat:>8.3f} {prod:>10.3f} "
              f"{r['accuracy_non_empty']:>10.3f}")
    scored = [r for r in rows if "law_flat" in r]
    e_flat = sum(abs(r["law_flat"] - r["accuracy_non_empty"])
                 for r in scored) / len(scored)
    e_kind = sum(abs(r["law_per_kind"] - r["accuracy_non_empty"])
                 for r in scored) / len(scored)
    print(f"\n  mean |error|:  flat q^k {e_flat:.3f}   per-kind "
          f"{e_kind:.3f}   ({'per-kind wins' if e_kind < e_flat else 'flat wins'})")

    tmpl = next(r for r in rows if "NEW surface" in r["arm"])
    none = next(r for r in rows if "no reader" in r["arm"])
    print(f"\nThe template reader on the new surface recovers "
          f"{tmpl['claim_recall']:.1%} of claims at "
          f"{tmpl['claim_precision']:.1%} precision.")
    print(f"It scores {tmpl['accuracy_pooled']:.3f} POOLED and "
          f"{tmpl['accuracy_non_empty']:.3f} on cases with a real answer.")
    print(f"A world with no claims at all scores "
          f"{none['accuracy_pooled']:.3f} / {none['accuracy_non_empty']:.3f}.")
    if abs(tmpl["accuracy_pooled"] - none["accuracy_pooled"]) < 0.05:
        print(f"\n-> The pooled column CANNOT distinguish the template reader "
              f"from having no\n   reader at all. Every arm from here is "
              f"reported on the non-empty column.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"n_cases": N_CASES, "empty_answers": empty,
                               "rows": rows}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
