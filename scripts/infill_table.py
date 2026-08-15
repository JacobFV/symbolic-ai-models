"""Read the infilling ladder's run directories and print the tables.

Reads ``summary.json`` only — the sweep is the authority and nothing here
recomputes a score. Every column carries its floor, because a number without one
is not a result, and ``copy_ceiling`` is printed beside every pointer column
because masking removes the visible same-label nodes a pointer needs and a
pointer's fall is only a fact about the pointer to the extent that it falls
faster than its own ceiling.

    uv run python scripts/infill_table.py runs/infill-node-r015 runs/infill-node-r035 ...
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

#: The pre-registered arms. Fixed in
#: `notes/decisions/2026-08-14-the-infilling-ladder-preregistration.md` before
#: any number landed, so a later reader can see the split was not chosen to fit.
POINTER = ("corefer-001", "ptrgen-001", "routes-001", "evidence-001",
           "vsa_perm-002", "ruleinduce-001")
NO_POINTER = ("grammar-001", "ngram-001", "ctw-001", "brill-001",
              "omegaclaw_rank-001", "omegaclaw_ctx-001")

KEYS = ("label_acc", "label_floor", "label_lift", "label_bits",
        "label_floor_bits", "label_n", "type_lift", "copy_acc", "copy_floor",
        "copy_lift", "copy_ceiling", "ansnode_acc", "ansnode_floor",
        "ansnode_lift", "ansnode_coverage", "ansnode_n")


def rows(run_dir: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for summary in sorted(run_dir.glob("*/summary.json")):
        d = json.loads(summary.read_text())
        task = next((t for t in ("node", "nodesub", "nodeans", "nodeans1")
                     if t in (d.get("final") or {})), None)
        if task is None:
            continue
        final = d["final"][task]
        row = {k: final.get(k) for k in KEYS}
        row["_task"] = task
        row["_seconds"] = d.get("seconds")
        row["_mask_rate"] = d.get("config", {}).get("mask_rate")
        row["_masking"] = d.get("masking", {})
        row["_renaming"] = (d.get("renaming") or {}).get("drop")
        row["_temperature"] = d.get("temperature")
        out[d.get("model", summary.parent.name)] = row
    return out


def fmt(v, spec="{:.3f}"):
    return "-" if v is None or v != v else spec.format(v)


def main(dirs: list[str]) -> int:
    table = {Path(d).name: rows(Path(d)) for d in dirs}
    models = [m for m in POINTER + NO_POINTER
              if any(m in r for r in table.values())]
    extra = sorted({m for r in table.values() for m in r} - set(models))
    models += extra

    for arm, data in table.items():
        if not data:
            print(f"\n### {arm}: no finished runs\n")
            continue
        any_row = next(iter(data.values()))
        print(f"\n### {arm}   task={any_row['_task']} "
              f"mask_rate={any_row['_mask_rate']} "
              f"fit={any_row['_masking'].get('fit_mask_rate')}/"
              f"{any_row['_masking'].get('fit_mask_mode')}")
        head = (f"{'model':<20}{'lbl acc':>9}{'floor':>9}{'lift':>9}"
                f"{'bits':>9}{'fl bits':>9}{'n':>8}{'typ lift':>10}"
                f"{'cpy acc':>9}{'cpy fl':>9}{'ceiling':>9}{'rename':>9}"
                f"{'temp':>7}{'secs':>7}")
        print(head)
        print("-" * len(head))
        for m in models:
            r = data.get(m)
            if not r:
                continue
            print(f"{m:<20}{fmt(r['label_acc']):>9}{fmt(r['label_floor']):>9}"
                  f"{fmt(r['label_lift']):>9}{fmt(r['label_bits']):>9}"
                  f"{fmt(r['label_floor_bits']):>9}"
                  f"{fmt(r['label_n'], '{:.0f}'):>8}{fmt(r['type_lift']):>10}"
                  f"{fmt(r['copy_acc']):>9}{fmt(r['copy_floor']):>9}"
                  f"{fmt(r['copy_ceiling']):>9}{fmt(r['_renaming']):>9}"
                  f"{fmt(r['_temperature'], '{:.1f}'):>7}"
                  f"{fmt(r['_seconds'], '{:.0f}'):>7}")
        if any_row["_task"] in ("nodeans", "nodeans1"):
            print()
            head = (f"{'model':<20}{'ansnd acc':>11}{'floor':>9}{'lift':>9}"
                    f"{'n':>8}{'coverage':>10}")
            print(head)
            print("-" * len(head))
            for m in models:
                r = data.get(m)
                if not r:
                    continue
                print(f"{m:<20}{fmt(r['ansnode_acc']):>11}"
                      f"{fmt(r['ansnode_floor']):>9}{fmt(r['ansnode_lift']):>9}"
                      f"{fmt(r['ansnode_n'], '{:.0f}'):>8}"
                      f"{fmt(r['ansnode_coverage'], '{:.3f}'):>10}")

    # the curve, arm-mean per pre-registered group
    print("\n### arm means (the pre-registered split), label_lift")
    head = f"{'arm':<24}{'pointer':>10}{'no pointer':>12}{'ceiling':>10}"
    print(head)
    print("-" * len(head))
    for arm, data in table.items():
        if not data:
            continue
        def mean(names, key="label_lift"):
            vals = [data[m][key] for m in names
                    if m in data and data[m].get(key) is not None
                    and data[m][key] == data[m][key]]
            return sum(vals) / len(vals) if vals else float("nan")
        print(f"{arm:<24}{fmt(mean(POINTER)):>10}{fmt(mean(NO_POINTER)):>12}"
              f"{fmt(mean(POINTER + NO_POINTER, 'copy_ceiling')):>10}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
