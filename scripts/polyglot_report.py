"""Read ``runs/polyglot/*.json`` and print the tables the write-up quotes.

Nothing is computed here that the steps did not already write down; this is
presentation only, so that no number in a note comes from a script that also
decided what to measure.

    uv run python scripts/polyglot_report.py [--metric bracket_f1]

Four tables, in the order the argument runs:

1. **in-sample** — every arm fitted on all 46 languages and scored on all 46,
   against the constant floor.
2. **held out** — the same arms under leave-eight-languages-out, six folds,
   every language held out exactly once. This is the number the objective is
   about.
3. **retention** — held out / in sample, per arm. Same language, same eval
   episodes, only the training mixture changed, so this divides out "that
   language is harder" entirely.
4. **script** — retention split by whether the held-out language's script is
   in the training mixture at all. Thirty-four of the 46 are Latin; the other
   twelve are the only language in the corpus written in theirs.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import statistics
from typing import Any

from symbolic_ai_parsers.polyglot import WALS46, scripts
from symbolic_ai_parsers.scoring import METRICS, SHORT

RUNS = pathlib.Path("runs/polyglot")


def load(protocol: str) -> list[dict[str, Any]]:
    return [json.loads(p.read_text(encoding="utf-8"))
            for p in sorted(RUNS.glob(f"{protocol}-*.json"))]


def collect(steps: list[dict[str, Any]], metric: str
            ) -> dict[str, dict[str, float]]:
    """``parser -> {language: score}``, over every step of one protocol."""
    out: dict[str, dict[str, float]] = {}
    for step in steps:
        for row in step["parsers"]:
            got = out.setdefault(row["parser"], {})
            for lang, cell in row["per_language"].items():
                got[lang] = cell["scores"][metric]
    return out


def mean(xs) -> float:
    xs = [x for x in xs if x == x]
    return statistics.fmean(xs) if xs else float("nan")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--metric", default="bracket_f1", choices=list(METRICS))
    args = ap.parse_args(argv)

    ins, out = load("mixture"), load("fold")
    if not ins and not out:
        print(f"nothing in {RUNS}/. Run scripts/polyglot_lolo.py first.")
        return 2
    floors = (ins or out)[0]["floors"]
    order = [r["parser"] for r in (ins or out)[0]["parsers"]]

    # ---- 1 and 2: every metric, macro over the languages of each protocol
    for title, steps in (("in sample (fitted on all 46)", ins),
                         ("held out (leave 8 out, 6 folds)", out)):
        if not steps:
            continue
        print(f"\n{title} — macro over languages, then over lessons")
        head = f"{'parser':<17}{'langs':>6}" + "".join(f"{SHORT[m]:>8}"
                                                       for m in METRICS)
        print(head + "\n" + "-" * len(head))
        for name in order:
            per = {m: collect(steps, m).get(name, {}) for m in METRICS}
            n = len(per[METRICS[0]])
            print(f"{name:<17}{n:>6}"
                  + "".join(f"{mean(per[m].values()):>8.3f}" for m in METRICS))
        print(f"{'FLOOR (constant)':<17}{'':>6}"
              + "".join(f"{floors[m]:>8.3f}" for m in METRICS))

    if not (ins and out):
        return 0

    # ---- 3: retention, per arm, on the chosen metric
    m = args.metric
    a, b = collect(ins, m), collect(out, m)
    print(f"\nretention on {m}: held-out score / in-sample score, per language")
    print("(same language, same eval episodes; only the training mixture moved)")
    head = (f"{'parser':<17}{'in':>8}{'held':>8}{'keep':>8}"
            f"{'Latn':>8}{'novel':>8}{'gap':>8}")
    print(head + "\n" + "-" * len(head))
    sc = scripts(WALS46)
    for name in order:
        ai, bi = a.get(name, {}), b.get(name, {})
        langs = sorted(set(ai) & set(bi))
        if not langs:
            continue
        keep = {l: (bi[l] / ai[l]) for l in langs if ai[l] > 1e-9}
        latn = [v for l, v in keep.items() if sc[l] == "Latn"]
        novel = [v for l, v in keep.items() if sc[l] != "Latn"]
        print(f"{name:<17}{mean(ai.values()):>8.3f}{mean(bi.values()):>8.3f}"
              f"{mean(keep.values()):>8.3f}{mean(latn):>8.3f}{mean(novel):>8.3f}"
              f"{mean(latn) - mean(novel):>8.3f}")

    # ---- 4: the conditioning comparison, stated as the control demands
    print("\nconditioning, held out and in sample, on " + m)
    for label, table in (("in sample", a), ("held out", b)):
        base = table.get("polycky-001", {})
        for name in ("polycky-002", "polycky-crc"):
            got = table.get(name, {})
            langs = sorted(set(base) & set(got))
            if not langs:
                continue
            d = mean(got[l] - base[l] for l in langs)
            print(f"  {label:<10}{name:<16} {d:+.4f} vs polycky-001")

    idh = [s["id_head"] for s in ins if s.get("id_head")]
    if idh:
        h = idh[0]
        print(f"\nlanguage-id head (the oracle, priced): nearest centroid on "
              f"shape_features\n  acc {h['acc']:.3f}  floor {h['floor']:.3f}  "
              f"over {h['n_languages']} languages")
    return 0


if __name__ == "__main__":                                    # pragma: no cover
    raise SystemExit(main())
