"""Price the `005` IR: what unification and pattern matching cost per token.

``APPROACH.md`` targets ~200k tokens/sec on one CPU core and ``vsa_sum-004`` at
``d = 256`` does 282k, so the cost thesis has headroom — but it is headroom, not
a blank cheque, and a pattern matcher over a space of thousands of atoms can be
ruinous. The pre-registration lists cost as one of the four things that would
refute the line, so it is measured beside the quality rather than instead of it.

**The timing convention is imported, not reimplemented.**
``scripts/vsa_dim_curve.py`` established it — two clocks over the same episodes,
CPU time rather than wall clock, one untimed warm pass, ``tokens/sec`` with the
*prose* token count as the denominator so the number sits beside
``APPROACH.md``'s. Copying thirty lines of it here is how two conventions that
look the same start disagreeing in the third decimal, so this module calls into
it.

The ratio between the two clocks is the number this script exists for. The
``votes`` clock is the model's own inner loop — build the view, encode it to an
atomspace, run the queries, superpose, clean up. The ``forward`` clock adds the
harness's ``[B, L, V]`` assembly, which is 32 x 128 x 8192 floats per batch and
is completely independent of anything the IR does. Quoting only the second would
report the *tokenizer's* size as the price of pattern matching.

Run after the sweep, one process, over whatever run directories are named::

    uv run python scripts/metta_cost.py runs/metta005/*
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from vsa_dim_curve import throughput                          # noqa: E402

OUT = Path("runs/metta005/timing")


def main(argv: list[str]) -> int:
    roots = [Path(a) for a in argv] or sorted(Path("runs/metta005").glob("*"))
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for run_dir in roots:
        if not (run_dir / "summary.json").exists():
            continue
        dest = OUT / f"{run_dir.name}.json"
        if dest.exists():
            rows.append(json.loads(dest.read_text()))
            continue
        try:
            row = throughput(run_dir)
        except Exception as e:                                # keep going
            print(f"{run_dir} FAILED {type(e).__name__}: {e}", flush=True)
            continue
        dest.write_text(json.dumps(row, indent=1), encoding="utf-8")
        rows.append(row)
        print(f"{row['model']:<24} acc {row['label_acc']:.3f}  "
              f"bits {row['label_bits']:.3f}  "
              f"{row['votes_tokens_per_sec']:>9,.0f} tok/s reasoning  "
              f"{row['tokens_per_sec']:>8,.0f} end-to-end  "
              f"fit {row['fit_seconds']:.0f}s", flush=True)
    if rows:
        print(f"\n{'model':<24}{'reasoning tok/s':>18}{'end-to-end tok/s':>18}"
              f"{'interface share':>18}")
        for row in sorted(rows, key=lambda r: -(r["votes_tokens_per_sec"] or 0)):
            share = 1.0 - (row["votes_cpu_seconds"]
                           / max(row["predict_cpu_seconds"], 1e-9))
            print(f"{row['model']:<24}{row['votes_tokens_per_sec']:>18,.0f}"
                  f"{row['tokens_per_sec']:>18,.0f}{share:>17.1%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
