"""Price the hypervector dimension: quality and throughput on one curve.

The repo's cost thesis is ~200k tokens/sec on one CPU core, i.e. 15-30 billion
tokens per dollar against a $1/1B target, so there is 15-30x of headroom to
spend. What nobody here has measured is the **exchange rate**: what a dimension
buys in quality and what it costs in speed. That is worth as much as any single
model's score, and it is the deliverable this script exists for.

How the two halves are measured, and why differently
----------------------------------------------------
**Quality comes from the sweep, never from here.** ``symbolic-ai-models sweep``
is the authority in this repo — scratch scripts have contradicted it twice, both
times flattering the write-up. So this script does not compute accuracy or bits
at all. It reads them out of the ``summary.json`` that a sweep wrote, one sweep
per dimension::

    for d in 256 1024 4096 16384 65536; do
      uv run symbolic-ai-models sweep --config configs/full179.toml \\
        --out runs/vsa_dim/d$d --resume --extra "{\\"vsa_dim\\": $d}" \\
        --models vsa-002,vsa_sum-004,vsa_hks-004
    done

**Throughput is measured here, because it is a timing and not a claim.** It is
measured on the *very model the sweep fitted*, reloaded from that run directory,
so the row that reports 0.28 label accuracy and the row that reports 180k
tokens/sec are the same object and not two fits that happen to share a name.

What "tokens/sec" means here, stated because it is not obvious
---------------------------------------------------------------
The masked-node task consumes a **graph**, not a token sequence. Quoting a
per-graph rate would not compare to anything, so the denominator is the token
count of the *same episodes'* prose — the number ``token_n`` in every
``summary.json`` — and the numerator is the wall clock of one full prediction
pass over their graphs::

    tokens/sec = sum_e |encode(text_e)| / seconds(forward over the graphs of e)

That is the same convention as the 235,685 / 210,864 / 156,960 figures in
``APPROACH.md``, so the numbers here can sit beside them. Fitting time is
reported separately and is not in it: a rule-based model fits once and predicts
forever, and folding the fit into the rate would price a cost the deployment
does not pay per token.

The clock is **CPU time**, not wall clock, and that is not fastidiousness. This
box carries real training alongside these runs — load average 17-30 on 20 cores
while the sweep was fitting — and it showed up as a 3.4x spread in ``seconds``
between two models doing near-identical work. Both clocks are recorded so the
gap between them stays visible.

One process per point, and each point written the moment it lands: long
single-process jobs on this box are killed at ~20 minutes and take the process
group with them. See ``scripts/wals_perlang.py`` for the same shape and the four
dead runs that taught it.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

OUT = Path("runs/vsa_dim")
#: The last point is deliberately too expensive. A curve with no right-hand end
#: cannot say where the knee is, and "more dimensions is better" is exactly the
#: conclusion an under-extended sweep produces.
DIMENSIONS = (256, 1024, 4096, 16384, 65536)


def throughput(run_dir: Path, batch: int = 32) -> dict:
    """Time one full prediction pass over the run's own evaluation episodes."""
    from symbolic_ai_core.data.batch import collate_graph
    from symbolic_ai_models.train import load_data, load_run

    model, tok, cfg = load_run(run_dir)
    _, episodes = load_data(cfg)
    tokens = sum(len(tok.encode(e.text)) for e in episodes)
    nodes = 0

    # One untimed pass over the first chunk: the first call allocates the
    # projection matrices and warms numpy's threadpool, and charging that to the
    # rate would make small dimensions look worse than they are.
    chunks = [episodes[i:i + batch] for i in range(0, len(episodes), batch)]
    rng = np.random.default_rng(20_250_811)
    warm = collate_graph(chunks[0], tok, max_nodes=cfg.max_nodes,
                         mask_rate=cfg.mask_rate, rng=rng)
    with torch.no_grad():
        model(warm)

    # Two clocks over the same episodes, because they price different things.
    #
    # `forward` is deployment-realistic and includes the harness's dense
    # assembly: `_mix` materialises a [B, L, V] tensor, 32 x 128 x 8192 floats
    # = 134MB per batch, which is O(vocabulary) and completely independent of
    # `d`. Timing only that would report the *tokenizer's* size as the cost of
    # the embedding -- it is what made a first pass here read 1,342 tok/s for a
    # model APPROACH.md clocks in the hundreds of thousands.
    #
    # `votes` is the model's own inner loop -- build the view, run the algebra,
    # clean up -- and is the thing that actually scales with `d`. The ratio
    # between the two is itself worth reading: it says how much of a symbolic
    # model's deployed cost is its reasoning and how much is the interface it
    # has to speak through.
    inner = 0.0
    wall0, cpu0 = time.perf_counter(), time.process_time()
    with torch.no_grad():
        for chunk in chunks:
            collated = collate_graph(
                chunk, tok, max_nodes=cfg.max_nodes, mask_rate=cfg.mask_rate,
                rng=np.random.default_rng(20_250_811))
            nodes += int(collated.pad_mask.sum())
            mark = time.process_time()
            for b in range(len(chunk)):
                view = model._view(collated, b)
                if len(view):
                    model.node_votes(view)
                    model.source_votes(view)
            inner += time.process_time() - mark
            model(collated)
    wall = time.perf_counter() - wall0
    # CPU time, not wall clock, is the rate that gets quoted. This box carries
    # real training alongside: load average was 17-30 on 20 cores while these
    # runs were fitted, and it showed up as a 3.4x spread in `seconds` between
    # two models doing near-identical work. A tokens/sec quoted off wall clock
    # under that would be a measurement of the neighbours. Both are recorded so
    # the gap between them is visible rather than assumed away.
    seconds = time.process_time() - cpu0

    summary = json.loads((run_dir / "summary.json").read_text())
    node = summary.get("final", {}).get("node", {})
    return {
        "model": summary["model"],
        "vsa_dim": int(summary["config"].get("extra", {}).get("vsa_dim", 4096)),
        "episodes": len(episodes), "tokens": tokens, "nodes": nodes,
        "predict_cpu_seconds": seconds, "predict_wall_seconds": wall,
        "votes_cpu_seconds": inner,
        "tokens_per_sec": tokens / seconds if seconds else float("nan"),
        "votes_tokens_per_sec": tokens / inner if inner else float("nan"),
        "nodes_per_sec": nodes / seconds if seconds else float("nan"),
        "fit_seconds": float(summary.get("seconds", float("nan"))),
        "parameters": int(summary.get("parameters", 0)),
        "label_acc": node.get("label_acc"), "label_lift": node.get("label_lift"),
        "label_bits": node.get("label_bits"),
        "label_bits_lift": node.get("label_bits_lift"),
        "copy_acc": node.get("copy_acc"), "copy_lift": node.get("copy_lift"),
        "renaming_drop": summary.get("renaming", {}).get("drop"),
        "knob": _knob(run_dir),
    }


def _knob(run_dir: Path) -> float | None:
    """The construction's fitted scalar, read off the rendered rules."""
    text = (run_dir / "rules.txt")
    if not text.exists():
        return None
    for line in text.read_text(encoding="utf-8").splitlines():
        if "knob=" in line:
            return float(line.split("knob=")[1].split(",")[0])
    return None


def main(argv: list[str]) -> int:
    roots = [Path(a) for a in argv] or sorted(OUT.glob("d*/*"))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "timing").mkdir(exist_ok=True)
    for run_dir in roots:
        if not (run_dir / "summary.json").exists():
            print(f"{run_dir}: no summary, skipped", flush=True)
            continue
        dest = OUT / "timing" / f"{run_dir.parent.name}-{run_dir.name}.json"
        if dest.exists():
            continue
        try:
            row = throughput(run_dir)
        except Exception as e:                                # keep going
            print(f"{run_dir} FAILED {type(e).__name__}: {e}", flush=True)
            continue
        dest.write_text(json.dumps(row, indent=1), encoding="utf-8")
        print(f"{row['model']:<22} d={row['vsa_dim']:<6} "
              f"acc {row['label_acc']:.3f}  bits {row['label_bits']:.3f}  "
              f"{row['votes_tokens_per_sec']:>9,.0f} tok/s reasoning  "
              f"{row['tokens_per_sec']:>8,.0f} end-to-end  "
              f"fit {row['fit_seconds']:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
