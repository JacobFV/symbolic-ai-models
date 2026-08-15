"""What does a model answer, when the answer node is the thing that is hidden?

A diagnostic, not a headline. It reloads a finished `nodeans` run — the sweep's
own fitted model, on the sweep's own evaluation episodes, all 179 lessons — and
asks *what kind* of wrong the wrong answers are:

* is the predicted symbol one of the episode's own answer options, i.e. has the
  model narrowed to the answer set and then missed inside it?
* is it the label of some **visible** node of the same graph, i.e. is it copying
  a neighbour that is not the answer?
* is it what the structural back-off would have said anyway?

`ansnode_acc` says the models fail. This says whether they fail in the space of
the question or somewhere else entirely, and those are different findings.

    uv run python scripts/nodeans_diagnostic.py runs/infill-ans/corefer-001
"""
from __future__ import annotations

import collections
import os
import sys

os.environ.setdefault("OMP_NUM_THREADS", "4")

import torch

torch.set_num_threads(4)

from symbolic_ai_core.data.batch import answer_nodes, collate_graph
from symbolic_ai_models.train import load_data, load_run


def main(run: str, batch_size: int = 16) -> int:
    model, tok, cfg = load_run(run, device="cpu")
    _, ev = load_data(cfg)
    counts: collections.Counter[str] = collections.Counter()
    wrong_examples: list[tuple[str, str, str]] = []

    for start in range(0, len(ev), batch_size):
        chunk = ev[start:start + batch_size]
        batch = collate_graph(chunk, tok, max_nodes=cfg.max_nodes,
                              mask_mode="answer",
                              rng=__import__("numpy").random.default_rng(0))
        with torch.no_grad():
            logits = model(batch).symbol_logits
        pred = logits.argmax(-1)
        for b, ep in enumerate(chunk):
            n = min(len(ep.graph), cfg.max_nodes)
            roots = answer_nodes(ep.graph, n, ep.answer)
            if not roots:
                counts["episode: no answer node"] += 1
                continue
            counts["episode: scored"] += 1
            visible = {ep.graph.labels[i] for i in range(n)
                       if ep.graph.labels[i] and i not in set(roots)}
            options = {c.strip() for c in ep.choices}
            for i in roots:
                if int(batch.target_tokens[b, i]) < 0:
                    counts["fill: label not in vocabulary"] += 1
                    continue
                counts["fill: scored"] += 1
                said = tok.itos[int(pred[b, i])]
                gold = ep.graph.labels[i].strip()
                if said == gold:
                    counts["fill: correct"] += 1
                    continue
                counts["fill: wrong"] += 1
                if said in options:
                    counts["wrong but inside the answer set"] += 1
                if said in visible:
                    counts["wrong and copied from a visible node"] += 1
                if said not in options and said not in visible:
                    counts["wrong and from neither"] += 1
                if len(wrong_examples) < 15:
                    wrong_examples.append((ep.lesson_id, gold, said))

    scored = counts["fill: scored"] or 1
    print(f"=== {run}")
    for k, v in counts.items():
        print(f"  {k:<38}{v:>7}   {v / scored:.4f}")
    print(f"\n  answer-set size, mean: "
          f"{sum(len(e.choices) for e in ev) / max(len(ev), 1):.2f}")
    print("\n  gold -> said")
    for lesson, gold, said in wrong_examples:
        print(f"    {lesson:<32}{gold!r:<18} -> {said!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(*sys.argv[1:]))
