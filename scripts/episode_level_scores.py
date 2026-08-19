"""The episode-level number this repo says it wants, for models that lack one.

`APPROACH.md` names five properties a reportable benchmark needs and says work
moving toward them **outranks work that moves a model up the existing table**.
Four already exist, in `symbolic_ai_models/agent.py`:

1. **Episode-level verdicts.** `CurriculumReport`: one episode, one right/wrong,
   n = 1,432.
2. **No true prefix.** `score_choices` ranks whole continuations from the prompt.
4. **A floor built from every feature the model sees.** `CurriculumReport.floor`
   is `max(uniform, per-lesson majority, best parameter-free shortcut)` -- pick
   the longest option, the one sharing most words with the question, the one
   written unlike the others.

What is missing is that **no model has ever been run through it**.
`runs/agents-full179` holds five baseline policies, and the best of them beats
the floor by **+0.0009**.

So this asks the question the repo says it wants answered and has never asked of
a model: **does anything here beat the episode-level floor?** The position-level
table says these models lift 0.19-0.36 against a 0.143 floor; an episode-level
verdict against a shortcut-aware floor is a different and much harder claim.

Models are fitted from one shared config so the comparison is about mechanisms.

Run: uv run python -u scripts/episode_level_scores.py
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import numpy as np
import torch

from scripts.can_the_models_certify import BASE_RUN, SCRATCH
from symbolic_ai_models.agent import evaluate_choices
from symbolic_ai_models.models.base import FitContext
from symbolic_ai_models.tasks import make_task
from symbolic_ai_models.train import (TrainConfig, _task_kwargs,
                                      build_tokenizer, load_data, make_model)

OUT = Path("runs/episode_level_scores.json")
MODELS = ("corefer-001", "ptrgen-001", "vsa_perm-002", "routes-001",
          "grammar-001", "evidence-001", "ilp-001", "ruleinduce-001",
          "frontier-010")


def measure(name: str) -> dict:
    cfg_dict = json.loads((BASE_RUN / "summary.json").read_text())["config"]
    fields = {f.name for f in TrainConfig.__dataclass_fields__.values()}
    cfg = TrainConfig(**{k: v for k, v in cfg_dict.items() if k in fields})
    cfg.model = name
    cfg.out = str(SCRATCH / f"ep-{name}")
    Path(cfg.out).mkdir(parents=True, exist_ok=True)

    torch.manual_seed(cfg.seed)
    random.seed(cfg.seed)
    np.random.seed(cfg.seed)
    train_eps, episodes = load_data(cfg)
    tok = build_tokenizer(cfg, train_eps)
    tasks = {n: make_task(n, **_task_kwargs(cfg, n)) for n in cfg.tasks}
    model = make_model(cfg, len(tok))
    model.fit(FitContext(
        episodes=train_eps, tok=tok, tasks=tasks,
        task_weights=cfg.task_weights, steps=cfg.steps,
        batch_size=cfg.batch_size, lr=cfg.lr, seed=cfg.seed,
        device=torch.device("cpu"), amp=False,
        checkpoint=str(Path(cfg.out) / "checkpoint.pt")))

    report = evaluate_choices(model, tok, episodes, device="cpu",
                              max_len=cfg.max_len)
    cheat, cheat_score = report.shortcut_floor()
    return {"model": name, "n": len(report.results),
            "accuracy": report.accuracy, "floor": report.floor,
            "lift": report.lift, "shortcut": cheat,
            "shortcut_score": cheat_score, "n_lessons": report.n_lessons,
            "solved": report.solved, "above_floor": report.above_floor}


def main() -> None:
    print(f"{len(MODELS)} models through the EPISODE-LEVEL benchmark, one "
          f"shared config\n", flush=True)
    hdr = (f"{'model':<18} {'n':>6} {'accuracy':>9} {'floor':>8} {'lift':>8} "
           f"{'lessons':>8} {'>floor':>7} {'solved':>7}")
    print(hdr)
    print("-" * len(hdr))
    rows = []
    for name in MODELS:
        try:
            r = measure(name)
        except Exception as exc:                    # noqa: BLE001
            print(f"{name:<18} FAILED: {type(exc).__name__}: {exc}")
            rows.append({"model": name, "error": f"{type(exc).__name__}: {exc}"})
            continue
        rows.append(r)
        print(f"{name:<18} {r['n']:>6,} {r['accuracy']:>9.4f} "
              f"{r['floor']:>8.4f} {r['lift']:>+8.4f} {r['n_lessons']:>8} "
              f"{r['above_floor']:>7} {r['solved']:>7}", flush=True)

    ok = [r for r in rows if "accuracy" in r]
    if not ok:
        print("\nno model could be scored episode-level")
        return
    best = max(ok, key=lambda r: r["lift"])
    print(f"\nbest lift: {best['model']} at {best['lift']:+.4f} "
          f"(accuracy {best['accuracy']:.4f} against floor {best['floor']:.4f})")
    print(f"the floor's winning cheat: {best['shortcut']} at "
          f"{best['shortcut_score']:.4f}")
    print(f"for comparison, the five baseline policies in runs/agents-full179 "
          f"top out at +0.0009.")
    beat = [r for r in ok if r["lift"] > 0.03]
    if beat:
        print(f"\n-> {len(beat)} of {len(ok)} models beat the episode-level "
              f"floor by more than +0.03: "
              f"{', '.join(r['model'] for r in beat)}.")
    else:
        print(f"\n-> NO MODEL beats the episode-level floor by more than +0.03. "
              f"The position-level\n   table shows lifts of 0.19-0.36 against a "
              f"0.143 floor; at episode level against\n   a floor that includes "
              f"the parameter-free cheats, that capability does not\n   survive.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"rows": rows}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
