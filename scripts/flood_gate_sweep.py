"""Fit and score a learned routing gate against the hand-written one.

Splits are the repo's standing ones and they are the reason the number means
anything: fitted on training seeds, **threshold tuned on a development split**,
reported on evaluation seeds from a million that nothing ever saw. The
evaluation seeds are read exactly once, at the end.

Scored on the **constrained** objective -- cheapest arm achieving accuracy at
least ``--bar`` -- because the raw ratio has a perverse regime far above the
floor and would reward a gate that gives accuracy away. See
``notes/findings/2026-08-18-dollars-per-solved-above-floor-rewards-losing-accuracy.md``.
"""

from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from symbolic_ai_core.flow import (Binding, Context, FlowGraph, Node,  # noqa: E402
                                   evaluate)
from symbolic_ai_core.world import Claim  # noqa: E402
from symbolic_ai_generators.flood import generate  # noqa: E402
from symbolic_ai_generators.flood.features import feature_vector  # noqa: E402
from symbolic_ai_generators.flood.flow import solve  # noqa: E402
from symbolic_ai_generators.flood.gate_model import GateModel, fit  # noqa: E402
from symbolic_ai_generators.flood.world import reach_rules  # noqa: E402
from symbolic_ai_kernels.flow_ops import world_artifact  # noqa: E402

FLOOR = 0.440


def cheap_arm(world):
    """datalog + reconcile + capacity. What the gate escalates *from*."""
    g = FlowGraph(nodes=(
        Node(id="world", op="flow.const@1",
             params={"artifact": world_artifact(world)}),
        Node(id="reach", op="kernel.run@1",
             params={"kernel": "datalog@1",
                     "request": {"rules": reach_rules(),
                                 "role_names": {"open": ["a", "b"],
                                                "reach": ["a", "b"]}}},
             inputs={"world": Binding("world", "out")}),
        Node(id="world2", op="world.apply_delta@1",
             inputs={"world": Binding("world", "out"),
                     "delta": Binding("reach", "delta")}),
        Node(id="cheap", op="flood.capacity_only@1",
             inputs={"world": Binding("world2", "world")}),
    ), outputs={"claims": Binding("cheap", "claims"),
                "reach": Binding("reach", "claims")})
    outs, ctx = evaluate(g, ctx=Context())
    ans = tuple(sorted(c["roles"]["vehicle"]["entity"]
                       for c in outs["claims"].value["claims"]
                       if c["polarity"] == "positive"))
    reach = [Claim.from_dict(x) for x in outs["reach"].value["claims"]]
    return ans, ctx.trace.total_usd, reach


def collect(seeds):
    rows = []
    for s in seeds:
        c = generate(s)
        cheap, cheap_usd, reach = cheap_arm(c.world)
        full, _, fctx = solve(c.world, ctx=Context())
        rows.append({"seed": s, "x": feature_vector(c.world, reach),
                     "cheap": cheap, "full": full, "oracle": c.answer,
                     "cheap_usd": cheap_usd, "full_usd": fctx.trace.total_usd,
                     "safe": int(tuple(cheap) == tuple(full))})
    return rows


def score(rows, decide):
    """``decide(row) -> take_cheap``. Returns (accuracy, mean usd, cheap share)."""
    hit = usd = taken = 0
    for r in rows:
        use = decide(r)
        taken += use
        hit += tuple(r["cheap"] if use else r["full"]) == tuple(r["oracle"])
        usd += r["cheap_usd"] if use else r["full_usd"]
    n = len(rows)
    return hit / n, usd / n, taken / n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n-train", type=int, default=800)
    ap.add_argument("--n-dev", type=int, default=400)
    ap.add_argument("--n-eval", type=int, default=400)
    ap.add_argument("--bar", type=float, default=0.99)
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    print(f"collecting train={args.n_train} dev={args.n_dev} "
          f"eval={args.n_eval} ...", flush=True)
    train = collect(range(args.n_train))
    dev = collect(range(500_000, 500_000 + args.n_dev))
    ev = collect(range(1_000_000, 1_000_000 + args.n_eval))

    base_rate = statistics.mean(r["safe"] for r in train)
    print(f"the cheap answer is already correct on {base_rate:.3f} of training "
          f"worlds\n")

    model = fit([(r["x"], r["safe"]) for r in train],
                fitted_on=f"seeds 0..{args.n_train - 1}")
    print("weights:", model.explain(), "\n")

    # --- threshold on DEV, against the accuracy bar --------------------
    best = None
    for t in [i / 100 for i in range(50, 100)]:
        model.threshold = t
        acc, usd, share = score(dev, lambda r: model.take_cheap(r["x"]))
        if acc >= args.bar and (best is None or usd < best[2]):
            best = (t, acc, usd, share)
    if best is None:
        print(f"no threshold reaches accuracy >= {args.bar} on dev; "
              f"falling back to the most conservative")
        model.threshold = 0.99
    else:
        model.threshold = best[0]
        print(f"dev-tuned threshold {best[0]:.2f}: acc {best[1]:.3f} "
              f"usd {best[2]:.3e} cheap-share {best[3]:.3f}\n")

    # --- report on EVAL, read once -------------------------------------
    arms = {
        "always full": lambda r: False,
        "hand gate (lossless)": lambda r: bool(_hand(r)),
        "learned gate": lambda r: model.take_cheap(r["x"]),
        "always cheap": lambda r: True,
    }
    print(f"{'arm':<24}{'acc':>7}{'lift':>8}{'$/ep':>12}"
          f"{'$/solved>floor':>16}{'cheap%':>9}   at bar {args.bar}")
    ok = {}
    for name, fn in arms.items():
        acc, usd, share = score(ev, fn)
        lift = acc - FLOOR
        per = usd / lift if lift > 0 else float("inf")
        mark = "" if acc >= args.bar else "   (below bar)"
        if acc >= args.bar:
            ok[name] = usd
        print(f"{name:<24}{acc:>7.3f}{lift:>8.3f}{usd:>12.3e}"
              f"{per:>16.3e}{share:>9.3f}{mark}")
    if ok:
        winner = min(ok, key=ok.get)
        print(f"\ncheapest arm at accuracy >= {args.bar}: {winner} "
              f"({ok[winner]:.3e}/episode)")
    if args.out:
        model.save(args.out)
        print(f"model written to {args.out}")
    return 0


def _hand(row) -> bool:
    """The hand gate's decision, recomputed from the same features."""
    from symbolic_ai_generators.flood.features import FEATURES
    f = dict(zip(FEATURES, row["x"]))
    if f["reachable"] == 0.0:
        return True
    return bool(f["laden_over_min_limit"] and f["laden_over_min_limit"] <= 1.0)


if __name__ == "__main__":
    raise SystemExit(main())
