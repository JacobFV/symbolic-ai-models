"""Print the `005` sweep as one table, with every floor beside every number.

`notes/README.md` rule 2: a number without its floor is not a result, and for
label numbers the copy ceiling goes with it. So this reads the floors out of
each ``summary.json`` and **asserts they are identical across rows** before
printing anything — a table whose rows were scored against different floors is
worse than no table, and this repo has published one.

    uv run python scripts/metta_table.py runs/metta005
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

COLUMNS = ("label_acc", "label_lift", "label_bits", "label_bits_lift",
           "type_acc", "type_lift", "copy_acc", "copy_lift")


def main(argv: list[str]) -> int:
    root = Path(argv[0] if argv else "runs/metta005")
    rows = []
    floors: dict[str, set] = {}
    for path in sorted(root.glob("*/summary.json")):
        d = json.loads(path.read_text())
        node = d.get("final", {}).get("node", {})
        if not node:
            continue
        for key in ("label_floor", "type_floor", "copy_floor", "copy_ceiling"):
            floors.setdefault(key, set()).add(round(float(node.get(key, 0)), 6))
        rows.append({"model": d["model"], "seconds": d.get("seconds", 0),
                     "params": d.get("parameters", 0),
                     "rename": (d.get("renaming") or {}).get("drop"),
                     **{c: node.get(c) for c in COLUMNS}})
    if not rows:
        print(f"no finished runs in {root}")
        return 1

    for key, values in floors.items():
        assert len(values) == 1, (
            f"rows disagree on {key}: {sorted(values)} -- they were not scored "
            f"against the same floor and must not appear in one table")
    print(f"{root}: {len(rows)} rows.  floors: label "
          f"{next(iter(floors['label_floor'])):.3f}, type "
          f"{next(iter(floors['type_floor'])):.3f}, copy "
          f"{next(iter(floors['copy_floor'])):.3f}; copy ceiling "
          f"{next(iter(floors['copy_ceiling'])):.3f}\n")

    head = (f"{'model':<24}{'lbl acc':>9}{'lbl lift':>10}{'bits':>8}"
            f"{'bits lift':>11}{'typ acc':>9}{'typ lift':>10}"
            f"{'cpy acc':>9}{'cpy lift':>10}{'rename':>9}{'secs':>7}")
    print(head)
    print("-" * len(head))
    for r in sorted(rows, key=lambda r: -(r["label_acc"] or 0)):
        rename = "    -   " if r["rename"] is None else f"{r['rename']:+.3f}"
        print(f"{r['model']:<24}{r['label_acc']:>9.3f}{r['label_lift']:>+10.3f}"
              f"{r['label_bits']:>8.3f}{r['label_bits_lift']:>+11.3f}"
              f"{r['type_acc']:>9.3f}{r['type_lift']:>+10.3f}"
              f"{r['copy_acc']:>9.3f}{r['copy_lift']:>+10.3f}"
              f"{rename:>9}{r['seconds']:>7.0f}")
    print("\nrename is the summary.json `drop`: positive means accuracy was LOST "
          "under a permutation of all symbols, with no refitting.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
