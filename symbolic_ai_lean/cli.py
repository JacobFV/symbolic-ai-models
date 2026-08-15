"""``symbolic-ai-lean`` — the ``006`` line's own entry point.

    uv run symbolic-ai-lean gate                      # the pre-registered gate
    uv run symbolic-ai-lean gate --n 5 --json out.json
    uv run symbolic-ai-lean show --lesson analogy     # one episode, elaborated
    uv run symbolic-ai-lean emit --lesson analogy     # .lean source for the oracle

``gate`` is a **diagnostic, not a sweep**. It reports a property of the data and
the kernel — how much of a candidate set a typechecker can refuse, and whether
the right answer survives — and it deliberately touches no model and no floor.
A number from here may not be quoted as a result about a model.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence


def cmd_gate(args: argparse.Namespace) -> int:
    from symbolic_ai_core.data.curriculum import resolve_lessons
    from .gate import run_gate

    lessons = resolve_lessons(args.lessons) if args.lessons else None
    res = run_gate(lessons=lessons, n=args.n, seed0=args.seed0,
                   mask_rate=args.mask_rate, max_nodes=args.max_nodes,
                   mask_seed=args.mask_seed)
    print(res.table())
    if args.json:
        payload = {
            "modes": res.modes, "n_episodes": res.n_episodes,
            "n_holes": res.n_holes, "n_copyable": res.n_copyable,
            "seed0": args.seed0, "n": args.n, "mask_rate": args.mask_rate,
            "max_nodes": args.max_nodes, "mask_seed": args.mask_seed,
            "lessons": len(lessons) if lessons else "all",
            "seconds": res.seconds, "checks": res.checks,
            "rows": {m: {"median_prune": res.median_prune(m),
                         "mean_prune": res.mean_prune(m),
                         "median_prune_label": res.median_prune_label(m),
                         "gold_survival": res.survival(m),
                         "matched_random": res.matched_random(m)}
                     for m in res.modes},
            "coverage": {"symbols": res.total_symbols,
                         "demoted": res.demoted_symbols,
                         "nodes": res.total_nodes,
                         "untyped": res.untyped_nodes,
                         "undeclared_candidates": res.unconstrained_checks,
                         "candidate_checks": res.total_checks},
        }
        with open(args.json, "w") as fh:
            json.dump(payload, fh, indent=2)
        print(f"\nwrote {args.json}")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    from symbolic_ai_core.data.curriculum import generate, resolve_lessons
    from .elaborate import elaborate
    from .expr import pretty
    from .translate import graph_to_expr

    lessons = resolve_lessons(args.lesson)
    ep = next(iter(generate(lessons[:1], n=1, seed0=args.seed0)))
    print(f"=== {ep.lesson_id} ({len(ep.graph)} nodes) ===")
    print(ep.graph.sexpr()[:1200])
    elab = elaborate(ep.graph, [], mode=args.mode)
    print(f"\nsignature ({len(elab.decl)} declarations, "
          f"{len(elab.demoted)} demoted, {len(elab.untyped)} untyped nodes):")
    for name, ty in sorted(elab.decl.items())[:args.limit]:
        print(f"  {name:<28} : {pretty(elab.ctx.instantiate(ty))}")
    if elab.demoted:
        print(f"  demoted: {sorted(elab.demoted)}")
    if args.expr:
        print("\nsyntax:\n" + pretty(graph_to_expr(ep.graph))[:1200])
    return 0


def cmd_emit(args: argparse.Namespace) -> int:
    from symbolic_ai_core.data.curriculum import generate, resolve_lessons
    from .emit import lean_source

    lessons = resolve_lessons(args.lesson)
    ep = next(iter(generate(lessons[:1], n=1, seed0=args.seed0)))
    src = lean_source(ep.graph, name=ep.lesson_id)
    if args.out:
        with open(args.out, "w") as fh:
            fh.write(src)
        print(f"wrote {args.out}")
    else:
        print(src)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="symbolic-ai-lean", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("gate", help="the pre-registered gating diagnostic")
    g.add_argument("--lessons", default=None,
                   help="default: every generatable lesson, which is the point")
    g.add_argument("--n", type=int, default=3, help="episodes per lesson")
    g.add_argument("--seed0", type=int, default=500,
                   help="held-out training seeds; eval starts at 1,000,000")
    g.add_argument("--mask-rate", type=float, default=0.15)
    g.add_argument("--max-nodes", type=int, default=128)
    g.add_argument("--mask-seed", type=int, default=0)
    g.add_argument("--json", default=None)
    g.set_defaults(fn=cmd_gate)

    s = sub.add_parser("show", help="one episode's elaborated signature")
    s.add_argument("--lesson", default="analogy")
    s.add_argument("--seed0", type=int, default=500)
    s.add_argument("--mode", default="open")
    s.add_argument("--limit", type=int, default=40)
    s.add_argument("--expr", action="store_true")
    s.set_defaults(fn=cmd_show)

    e = sub.add_parser("emit", help="Lean 4 source, for the outside oracle")
    e.add_argument("--lesson", default="analogy")
    e.add_argument("--seed0", type=int, default=500)
    e.add_argument("--out", default=None)
    e.set_defaults(fn=cmd_emit)

    args = p.parse_args(argv)
    return int(args.fn(args))


if __name__ == "__main__":                            # pragma: no cover
    sys.exit(main())
