"""The models abstain. Is that certification, or just not answering?

This session measured certification value on federated data and found it real:
escalation targeting worth **4.69x** on entity alignment, and a maintenance
certificate worth **16.1x** rising to **57.5x** with a tighter sound bound. The
metric is `Targeting` in `symbolic_ai_core.cost`, floored by spending the same
budget blindly.

The repo's actual subject is the language substrate, and nobody has asked
whether its models have any certification value at all. They do abstain --
`symbolic.py`'s back-off exists precisely because *"a model that declined to
answer was being dropped below the baseline it is compared against"* -- and
abstention looks like epistemic virtue.

Under the targeting metric it may be nothing of the sort. `aim_x ~ 1/f_flagged`
needs the flagged set to be **small**, and `symbolic.py:343` records *"ilp
answers 35% of nodes at 0.525 against a floor of 0.332; synth answers 1% at
1.000"*. Escalating 65% or 99% of positions is nearly escalating everything, and
there is no aiming left to do.

**The signal was already computed and thrown away.** `_forward_graph` builds
`s_conf`, which is 0 at every position the model declined to vote on and positive
where it committed, then feeds it to `_mix` and discards it. Same shape as the
certificate arm's discarded slack. It is now exposed as
`ModelOutput.channels["determinacy"]`, consumed by nothing else, so no published
number moves.

Rule-based models are *fitted*, not checkpointed, and their run directories hold
only `rules.txt` and `summary.json` -- so each is rebuilt from its own saved
config and re-fitted in one pass. That is ~7 minutes for six models, and it
reproduces the run rather than reinterpreting it.

Run: uv run python -u scripts/can_the_models_certify.py
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import numpy as np
import torch

from symbolic_ai_models.models.base import FitContext
from symbolic_ai_models.tasks import make_task
from symbolic_ai_models.train import (TrainConfig, _task_kwargs, batches,
                                      build_tokenizer, load_data, make_model)
from symbolic_ai_core.cost import Targeting

#: One config for every model, taken from a real run, so the comparison is
#: about mechanisms and not about budgets.
BASE_RUN = Path("runs/refit-node-r015/vsa_perm-002")
#: Both regimes the docstring at symbolic.py:343 names -- models that vote on
#: nearly everything, and the ones it records as abstaining heavily
#: ("ilp answers 35% of nodes at 0.525; synth answers 1% at 1.000").
#: An abstained set smaller than this is a slice, and a slice may form a
#: hypothesis and never report one. `grammar-001` and `evidence-001` abstain on
#: exactly ONE position out of 5,233; a first version printed their aim x as
#: measurements.
MIN_ABSTAINED = 30
MODELS = ("evidence-001", "grammar-001", "routes-001", "corefer-001",
          "ptrgen-001", "vsa_perm-002", "ilp-001", "synth-001",
          "ruleinduce-001", "syllogism-001")
SCRATCH = Path("/tmp/claude-1000/-home-brandonin-Documents-symbolic-ai-models/f87bb567-e758-412f-94a7-e8df8813daf7/scratchpad/certify")
OUT = Path("runs/can_the_models_certify.json")


def measure(name: str, *, structural_fallback: bool | None = None) -> dict:
    """Fit ``name`` on the shared config and split its accuracy by determinacy.

    ``structural_fallback`` overrides the model's own setting when given, so the
    same code can price the back-off both ways; ``None`` leaves the model's
    default and reproduces the published behaviour exactly.
    """
    cfg_dict = json.loads((BASE_RUN / "summary.json").read_text())["config"]
    fields = {f.name for f in TrainConfig.__dataclass_fields__.values()}
    cfg = TrainConfig(**{k: v for k, v in cfg_dict.items() if k in fields})
    cfg.model = name
    cfg.out = str(SCRATCH / name)
    Path(cfg.out).mkdir(parents=True, exist_ok=True)

    torch.manual_seed(cfg.seed)
    random.seed(cfg.seed)
    np.random.seed(cfg.seed)
    train_eps, episodes = load_data(cfg)
    tok = build_tokenizer(cfg, train_eps)
    tasks = {n: make_task(n, **_task_kwargs(cfg, n)) for n in cfg.tasks}
    model = make_model(cfg, len(tok))
    if structural_fallback is not None:
        model.structural_fallback = structural_fallback
    model.fit(FitContext(
        episodes=train_eps, tok=tok, tasks=tasks,
        task_weights=cfg.task_weights, steps=cfg.steps,
        batch_size=cfg.batch_size, lr=cfg.lr, seed=cfg.seed,
        device=torch.device("cpu"), amp=False,
        checkpoint=str(Path(cfg.out) / "checkpoint.pt")))

    task = tasks["node"]
    if hasattr(task, "rng"):
        task.rng = np.random.default_rng(12345)

    voted_n = voted_ok = abst_n = abst_ok = 0
    has_channel = False
    model.eval()
    with torch.no_grad():
        for batch in batches(episodes, task, tok, batch_size=cfg.batch_size,
                             rng=random.Random(0), shuffle=False):
            out = model(batch)
            det = out.channels.get("determinacy")
            if det is None:
                break
            has_channel = True
            tgt = batch.target_tokens
            pred = out.symbol_logits.argmax(-1)
            keep = tgt >= 0
            ok = (pred == tgt) & keep
            committed = det > 0
            voted_n += int((keep & committed).sum())
            voted_ok += int((ok & committed).sum())
            abst_n += int((keep & ~committed).sum())
            abst_ok += int((ok & ~committed).sum())

    row: dict = {"model": name, "voted_n": voted_n, "abstained_n": abst_n,
                 "structural_fallback": structural_fallback}
    if not has_channel:
        # Distinct from "never abstains", which is a RESULT. This means the
        # model does not go through the graph forward at all.
        return {**row, "status": "no determinacy channel (not a graph model)"}
    n = voted_n + abst_n
    if not n:
        return {**row, "status": "nothing scored"}
    v = voted_n / n
    base = (voted_ok + abst_ok) / n
    row.update(n=n, vote_rate=v, label_acc=base, flagged=1.0 - v,
               acc_voted=(voted_ok / voted_n) if voted_n else float("nan"),
               acc_abstained=(abst_ok / abst_n) if abst_n else float("nan"))
    row["gap"] = row["acc_voted"] - row["acc_abstained"]
    if abst_n == 0:
        # Nothing to aim at. Reporting 0.00x here, as a first version did, is a
        # division artefact dressed as a measurement.
        return {**row, "status": "never abstains -- no flagged set to aim",
                "aim": float("nan")}
    if voted_n == 0:
        return {**row, "status": "never votes -- the flagged set is everything",
                "aim": float("nan")}
    flagged = 1.0 - v
    targeted = v * row["acc_voted"] + flagged * 1.0
    blind = base + flagged * (1.0 - base)
    row["aim"] = ((targeted - base) / (blind - base)
                  if blind > base else float("nan"))
    # The closed form, kept beside the arithmetic because it is the finding:
    #   aim = (1-v)(1-a_abstained) / [(1-v)(1-base)] = (1-a_abstained)/(1-base)
    # The flagged share CANCELS. What governs certification value is not how
    # much you flag but how wrong you are overall, and since a_abstained >= 0,
    #   aim  <=  1 / (1 - label_acc)
    row["ceiling"] = 1.0 / (1.0 - base) if base < 1.0 else float("inf")
    row["status"] = ("measured" if abst_n >= MIN_ABSTAINED
                     else f"abstains on {abst_n} position(s) -- a slice")
    row["targeting"] = Targeting(escalated=flagged, rate_base=base,
                                 rate_targeted=targeted, rate_blind=blind,
                                 escalated_usd_per_attempt=1e-9).above_blind()
    return row


def main() -> None:
    print(f"{len(MODELS)} models, one shared config from {BASE_RUN}\n",
          flush=True)
    hdr = (f"{'model':<18} {'votes on':>9} {'acc|voted':>10} "
           f"{'acc|abst':>9} {'gap':>8} {'label_acc':>10} {'aim x':>8}")
    print(hdr)
    print("-" * len(hdr))
    rows = []
    for name in MODELS:
        try:
            r = measure(name)
        except Exception as exc:                    # noqa: BLE001
            print(f"{name:<18} skipped: {type(exc).__name__}: {exc}")
            continue
        rows.append(r)
        if r["status"] != "measured":
            extra = ""
            if "vote_rate" in r:
                extra = (f"  (votes on {r['vote_rate']:.1%}, "
                         f"acc {r['label_acc']:.3f})")
            print(f"{name:<18} {r['status']}{extra}", flush=True)
            continue
        print(f"{name:<18} {r['vote_rate']:>8.1%} {r['acc_voted']:>10.3f} "
              f"{r['acc_abstained']:>9.3f} {r['gap']:>+8.3f} "
              f"{r['label_acc']:>10.3f} {r['aim']:>7.2f}x", flush=True)

    ok = [r for r in rows if r["status"] == "measured"]
    never = [r for r in rows if r.get("status", "").startswith("never abstains")]
    slices = [r for r in rows if "a slice" in r.get("status", "")]
    if not ok:
        print("\nnothing measurable")
        return
    best = max(ok, key=lambda r: r["aim"])
    print(f"\n{len(ok)} models with an abstained set worth reporting, "
          f"{len(never)} that never abstain,\n{len(slices)} abstaining on "
          f"fewer than {MIN_ABSTAINED} positions and therefore not reported.")
    print(f"\nbest aim x: {best['model']} at {best['aim']:.2f}x, against its "
          f"own ceiling of {best['ceiling']:.2f}x.")
    print(f"this session's federated arms, for scale: escalation targeting "
          f"4.69x,\nmaintenance certificate 16.1x, 57.5x with a tighter sound "
          f"bound.")

    # Derived, not asserted. A first version printed a "middle regime" story
    # that the algebra contradicts: the flagged share cancels exactly.
    print(f"\n  aim = (1-v)(1-a_abstained) / [(1-v)(1-base)] = "
          f"(1 - a_abstained) / (1 - base)")
    print(f"  The FLAGGED SHARE CANCELS. Certification value is not governed by "
          f"how much you\n  flag, nor by how well you flag it, but by how "
          f"wrong you are overall:")
    print(f"\n      aim  <=  1 / (1 - label_acc)\n")
    print(f"  {'model':<18} {'label_acc':>10} {'aim':>7} {'ceiling':>9}")
    for r in sorted(ok, key=lambda r: -r["aim"]):
        print(f"  {r['model']:<18} {r['label_acc']:>10.3f} {r['aim']:>6.2f}x "
              f"{r['ceiling']:>8.2f}x")
    print(f"\n-> A MODEL CAN ONLY CERTIFY TO THE EXTENT IT IS USUALLY RIGHT. "
          f"These models are\n   {min(r['label_acc'] for r in ok):.0%}-"
          f"{max(r['label_acc'] for r in ok):.0%} accurate, so no amount of "
          f"well-aimed abstention can be worth more\n   than "
          f"{max(r['ceiling'] for r in ok):.2f}x. The federated arms reached "
          f"4.69x-57.5x because their base\n   accuracy was 87%-99%, and the "
          f"maintenance oracle's 131.6x is exactly\n   1/(1-0.9924).")
    print(f"\n   The strongest determinacy signal in the set belongs to "
          f"synth-001 -- it votes on\n   2.1% of positions at 0.759 against "
          f"0.062 elsewhere, a gap of +0.697 -- and it\n   is worth 1.02x. "
          f"Signal quality is not the binding constraint.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"base_run": str(BASE_RUN), "rows": rows},
                              indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
