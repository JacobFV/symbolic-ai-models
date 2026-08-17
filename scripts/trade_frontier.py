"""Is the accuracy/equivariance trade a property of a model, or of the task?

`vote_sharpness` and `map_vote_weight` trace the same (accuracy, renamed) curve
inside the `frontier` family, which licensed the phrase "a fixed exchange rate".
That phrase was only ever measured inside one family with two knobs.

This asks the wider question against every scored model: plot each model as a
point in (label_acc, renamed_label_acc), take the Pareto front, and ask whether
the frontier family's knob-curve lies *on* that front or *under* it.

- If every family lands on one curve, the trade is a property of the curriculum
  and the harness, and the whole pointer arc was walking along a constraint.
- If families sit at visibly different offsets, the trade is a model property and
  the distance from the front is the thing worth optimising.

Reads `runs/<sweep>/*/summary.json`; runs nothing.
"""

from __future__ import annotations

import argparse
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _family(name: str) -> str:
    """`frontier-pointsoft` -> `frontier`; `synth` -> `synth`."""
    return name.split("-")[0].split("_")[0]


def load(run_dir: pathlib.Path) -> list[dict]:
    rows = []
    for d in sorted(run_dir.iterdir()):
        f = d / "summary.json"
        if not f.exists():
            continue
        s = json.loads(f.read_text())
        node = s.get("final", {}).get("node")
        ren = s.get("renaming", {})
        if not node or "renamed_label_acc" not in ren:
            continue
        rows.append({
            "model": d.name,
            "family": _family(d.name),
            "acc": float(node["label_acc"]),
            "renamed": float(ren["renamed_label_acc"]),
            "bits": float(node.get("label_bits", float("nan"))),
            "drop": float(ren.get("drop", float("nan"))),
        })
    return rows


def pareto(rows: list[dict]) -> list[dict]:
    """Maximise both `acc` and `renamed`. A row is on the front when nothing
    else is >= on both and > on one."""
    front = []
    for r in rows:
        if not any(o is not r and o["acc"] >= r["acc"] and o["renamed"] >= r["renamed"]
                   and (o["acc"] > r["acc"] or o["renamed"] > r["renamed"])
                   for o in rows):
            front.append(r)
    return sorted(front, key=lambda r: -r["acc"])


def shortfall(row: dict, front: list[dict]) -> float:
    """How much accuracy the front offers at this row's equivariance or better.

    Zero means the row is on the front. Positive means some other model is at
    least this equivariant *and* more accurate, so this row's position is not
    forced by the trade — it is just worse.
    """
    better = [f["acc"] for f in front if f["renamed"] >= row["renamed"]]
    return max(0.0, max(better, default=row["acc"]) - row["acc"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=str(ROOT / "runs" / "full179"))
    args = ap.parse_args()

    rows = load(pathlib.Path(args.run))
    front = pareto(rows)
    on_front = {r["model"] for r in front}

    print(f"{len(rows)} models with both columns; {len(front)} on the front\n")
    print("PARETO FRONT (acc x renamed)")
    print(f"  {'model':24s} {'acc':>7s} {'renamed':>8s} {'bits':>7s} {'drop':>7s}")
    for r in front:
        print(f"  {r['model']:24s} {r['acc']:7.4f} {r['renamed']:8.4f} "
              f"{r['bits']:7.3f} {r['drop']:7.4f}")

    print("\nBY FAMILY: how far the family's best row sits under the front")
    fams: dict[str, list[dict]] = {}
    for r in rows:
        fams.setdefault(r["family"], []).append(r)
    out = []
    for fam, rs in fams.items():
        best = min(rs, key=lambda r: shortfall(r, front))
        out.append((shortfall(best, front), fam, len(rs), best, sum(
            1 for r in rs if r["model"] in on_front)))
    for gap, fam, n, best, k in sorted(out):
        mark = "  <- on the front" if gap == 0.0 else ""
        print(f"  {fam:16s} n={n:2d} front={k:2d} shortfall {gap:6.4f} "
              f"via {best['model']:22s}{mark}")

    print("\nFRONTIER FAMILY, sorted by equivariance — is its knob-curve the front?")
    fr = sorted((r for r in rows if r["family"] == "frontier"),
                key=lambda r: r["renamed"])
    for r in fr:
        mark = "ON FRONT" if r["model"] in on_front else f"under by {shortfall(r, front):.4f}"
        print(f"  {r['model']:24s} acc {r['acc']:.4f} ren {r['renamed']:.4f}  {mark}")


if __name__ == "__main__":
    main()
