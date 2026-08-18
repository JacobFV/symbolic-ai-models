"""``symbolic-ai`` — look at the substrate: sources, kernels, and one live task.

Three subcommands, each answering a question that was previously only answerable
by reading code:

``sources``   what does this repo know about, and which bytes are on this disk?
``kernels``   which kernels exist, what do they require, and is the toolchain here?
``margin``    how far each task sits from its decision boundary, and therefore
              whether to spend on recall or precision and whether a router is
              worth building at all.
``flood``     run the three-kernel task and print the trace and the answer.
"""

from __future__ import annotations

import argparse
import json
from typing import Sequence

__all__ = ["main"]


def _sources(args) -> int:
    from .source import SourceRegistry, data_root
    from .source.license import license_closure

    reg = SourceRegistry()
    sources = reg.sources()
    rows = reg.census()
    held = sum(1 for r in rows if r["held"])
    total = sum(int(r["bytes"]) for r in rows)
    print(f"{len(sources)} sources, {len(rows)} snapshots, "
          f"{held} held on this disk ({total / 2**30:.1f} GiB)")
    print(f"data root: {data_root()}"
          f"{'' if data_root().exists() else '  (absent -- a normal state)'}\n")
    print(f"{'source':<18} {'access':<14} {'redistribution':<18} "
          f"{'held':<5} {'GiB':>7}")
    for r in rows:
        s = sources.get(str(r["source"]))
        acc = (s.access.get("class", "?") if s else "?")
        red = (s.license.get("redistribution", "?") if s else "?")
        print(f"{str(r['source']):<18} {acc:<14} {red:<18} "
              f"{'yes' if r['held'] else 'no':<5} "
              f"{int(r['bytes']) / 2**30:>7.2f}")

    arts = reg.artifacts()
    if arts:
        print(f"\n{len(arts)} artifacts:")
        for aid, a in sorted(arts.items()):
            closure = a.raw.get("license_lineage", {}).get("redistribution", "?")
            print(f"  {aid:<24} {len(a.parents):>2} parents   "
                  f"redistribution: {closure}")
    return 0


def _kernels(args) -> int:
    from symbolic_ai_kernels import get_kernel, kernel_ids

    print(f"{'kernel':<12} {'runtime':<9} {'available':<10} {'semantics'}")
    for kid in kernel_ids():
        k = get_kernel(kid)
        ok, why = k.available()
        m = k.manifest
        print(f"{kid:<12} {m.runtime:<9} {('yes' if ok else 'NO'):<10} "
              f"{', '.join(m.semantics)}")
        if not ok:
            print(f"             ^ {why}")
        if args.verbose:
            print(f"             requires {list(m.requires)}  "
                  f"provides {list(m.provides)}  authority {dict(m.authority)}")
    return 0


def _flood(args) -> int:
    from symbolic_ai_generators.flood import generate
    from symbolic_ai_generators.flood.flow import solve

    hits = 0
    for seed in range(args.seed, args.seed + args.n):
        case = generate(seed)
        got, outs, ctx = solve(case.world)
        ok = tuple(got) == tuple(case.answer)
        hits += ok
        if args.n == 1 or args.verbose:
            print(case.report)
            print()
            for run in ctx.trace.runs:
                mark = "cached" if run.cached else ("skipped" if run.skipped
                                                    else f"{run.wall_ns/1e6:.1f}ms")
                print(f"  {run.node:<8} {run.op:<22} {mark}")
            dl = outs["projection_datalog"].value
            # Claim-level losses first: "a dict facet value did not project" is
            # true and dull, while "a Quantity carries a unit" is the one that
            # says why another kernel exists.
            order = {"claim": 0, "uncertainty": 1, "valid_time": 2, "scope": 3}
            shown = sorted(dl["discarded"],
                           key=lambda d: order.get(d["kind"], 9))
            print(f"\n  datalog discarded {len(dl['discarded'])}, including:")
            for d in shown[:2]:
                print(f"    - [{d['kind']}] {d['why'][:80]}")
            print(f"  candidate routes: {outs['load_report'].value['n_routes']}"
                  f"   SMT calls: {outs['load_report'].value['n_smt_calls']}")
            print(f"  trace: {len(ctx.trace.runs)} nodes, "
                  f"{ctx.trace.unpriced} unpriced (NOT free)")
        print(f"seed {seed}: flow {got}  oracle {case.answer}  "
              f"{'ok' if ok else 'MISMATCH'}")
    if args.n > 1:
        print(f"\nagreement {hits}/{args.n} = {hits / args.n:.3f}")
    return 0


def _margin(args) -> int:
    """Profile each task's decision margin and say which errors matter.

    The point of a margin number is that it changes what you build next, so this
    prints the advice rather than the distribution.
    """
    from dataclasses import replace

    from .runtime.margin import margin_profile
    from .world import Quantity, WorldSnapshot

    def scale_quantity(world, factor, predicate):
        out = []
        for c in world.claims:
            q = c.roles.get("value")
            if c.predicate == predicate and isinstance(q, Quantity):
                roles = dict(c.roles)
                roles["value"] = Quantity(max(0.01, q.value * factor), q.unit,
                                          q.stderr)
                out.append(replace(c, roles=roles))
            else:
                out.append(c)
        return WorldSnapshot(entities=world.entities, claims=tuple(out))

    tasks = {}

    if args.task in ("all", "flood"):
        from symbolic_ai_core.flow import Context
        from symbolic_ai_generators.flood import generate as flood
        from symbolic_ai_generators.flood.flow import solve

        pairs = [(flood(s).world, v) for s in range(args.n)
                 for v in sorted(flood(s).vehicles)]
        tasks["flood"] = (
            pairs,
            lambda pw: pw[1] in solve(pw[0], ctx=Context())[0],
            lambda pw, f: (scale_quantity(pw[0], f, "load_limit"), pw[1]))

    if args.task in ("all", "solvency"):
        from symbolic_ai_generators.solvency import decide, generate as solv

        cases = [solv(s) for s in range(args.n * 3)]
        tasks["solvency"] = (
            cases,
            lambda c: decide(c, as_of=c.decision_date)[0],
            lambda c, f: replace(c, filings=tuple((e, v * f, k)
                                                  for e, v, k in c.filings)))

    if args.task in ("all", "scheduling"):
        from symbolic_ai_generators.scheduling import generate as sched
        from symbolic_ai_generators.scheduling.ops import build_program
        from symbolic_ai_kernels import KernelRequest, get_kernel

        asp = get_kernel("asp@1")

        def sched_decide(w):
            program, _ = build_program(w)
            request = KernelRequest(params={"program": program,
                                            "max_models": 1})
            return asp.run(asp.project(w, request), request).ok

        tasks["scheduling"] = (
            [sched(s, slack=args.slack).world for s in range(args.n)],
            sched_decide,
            lambda w, f: scale_quantity(w, f, "duration"))

    if not tasks:
        print(f"unknown task {args.task!r}")
        return 1

    for name, (corpus, decide_fn, scale_fn) in tasks.items():
        p = margin_profile(corpus, decide_fn, scale_fn)
        print(f"{name}:")
        print(f"  n={p.n}  unbounded={p.unbounded}")
        print(f"  {p.advice()}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="symbolic-ai", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("sources", help="what this repo knows and what it holds")
    p.set_defaults(fn=_sources)

    p = sub.add_parser("kernels", help="registered kernels and their toolchains")
    p.add_argument("-v", "--verbose", action="store_true")
    p.set_defaults(fn=_kernels)

    p = sub.add_parser("margin",
                       help="which errors matter, from the uncorrupted corpus")
    p.add_argument("task", nargs="?", default="all",
                   choices=("all", "flood", "solvency", "scheduling"))
    p.add_argument("-n", type=int, default=20)
    p.add_argument("--slack", type=float, default=0.15,
                   help="scheduling only: the decision-margin knob")
    p.set_defaults(fn=_margin)

    p = sub.add_parser("flood", help="run the three-kernel flood task")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("-n", type=int, default=1)
    p.add_argument("-v", "--verbose", action="store_true")
    p.set_defaults(fn=_flood)

    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":                                    # pragma: no cover
    raise SystemExit(main())
