"""``symbolic_ai_models`` — build data, train an architecture, compare the results."""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from dataclasses import fields
from pathlib import Path
from typing import Any, Sequence

__all__ = ["main"]


# ---------------------------------------------------------------------------
# config plumbing
# ---------------------------------------------------------------------------
def _load_toml(path: str | Path) -> dict[str, Any]:
    with Path(path).open("rb") as f:
        return tomllib.load(f)


def _config_from_args(args: argparse.Namespace):
    """Layer a TOML file under the command line: explicit flags always win."""
    from .train import TrainConfig
    data: dict[str, Any] = {}
    if args.config:
        data.update(_load_toml(args.config))
    known = {f.name for f in fields(TrainConfig)}
    for key, value in vars(args).items():
        if key in known and value is not None:
            data[key] = value
    if isinstance(data.get("tasks"), str):
        data["tasks"] = tuple(t.strip() for t in data["tasks"].split(",") if t.strip())
    if isinstance(data.get("extra"), str):
        data["extra"] = json.loads(data["extra"])
    weights = data.get("task_weights")
    if isinstance(weights, str):
        data["task_weights"] = {k: float(v) for k, v in
                                (p.split("=") for p in weights.split(","))}
    data.setdefault("task_weights", {t: 1.0 for t in data.get("tasks", ("lm", "node"))})
    return TrainConfig.from_dict(data)


def _add_train_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument("--config", help="TOML file of defaults; flags override it")
    p.add_argument("--model", help="architecture id (see `symbolic_ai_models models`)")
    p.add_argument("--tasks", help="comma-separated: lm, node, or both")
    p.add_argument("--task-weights", dest="task_weights",
                   help="e.g. lm=1.0,node=0.5")
    p.add_argument("--data", help="a directory built by `symbolic_ai_models data`")
    p.add_argument("--lessons", help="all | core170 | tag:X | cap:X | a,b,c")
    p.add_argument("--n-train", dest="n_train", type=int)
    p.add_argument("--n-eval", dest="n_eval", type=int)
    p.add_argument("--language")
    p.add_argument("--steps", type=int)
    p.add_argument("--batch-size", dest="batch_size", type=int)
    p.add_argument("--lr", type=float)
    p.add_argument("--d-model", dest="d_model", type=int)
    p.add_argument("--n-layers", dest="n_layers", type=int)
    p.add_argument("--n-heads", dest="n_heads", type=int)
    p.add_argument("--d-ff", dest="d_ff", type=int)
    p.add_argument("--dropout", type=float)
    p.add_argument("--mask-rate", dest="mask_rate", type=float)
    p.add_argument("--max-nodes", dest="max_nodes", type=int)
    p.add_argument("--max-len", dest="max_len", type=int)
    p.add_argument("--vocab-size", dest="vocab_size", type=int)
    p.add_argument("--eval-every", dest="eval_every", type=int)
    p.add_argument("--log-every", dest="log_every", type=int)
    p.add_argument("--warmup", type=int)
    p.add_argument("--no-amp", dest="amp", action="store_false", default=None,
                   help="disable bfloat16 autocast")
    p.add_argument("--seed", type=int)
    p.add_argument("--device")
    p.add_argument("--extra", help="JSON of architecture-specific options")
    p.add_argument("--out", help="output directory for the run")


def _progress(step: int, total: int, losses: dict[str, float],
              grad: float, metrics: dict | None = None) -> None:
    parts = " ".join(f"{k}={v:.3f}" for k, v in losses.items())
    if metrics is None:
        print(f"  step {step + 1:>6}/{total}  {parts}  |g|={grad:.2f}", flush=True)
        return
    summary = "  ".join(
        f"{task}: " + " ".join(f"{k}={v:.3f}" for k, v in sorted(m.items())
                               if k.endswith(("_acc", "_bits", "_lift")))
        for task, m in metrics.items())
    print(f"  eval @ {step + 1:>6}  {summary}", flush=True)


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------
def cmd_models(args: argparse.Namespace) -> int:
    from .models import REGISTRY, model_names
    from .models.symbolic import RuleBasedModel
    for family, want in (("neural", False), ("rule-based", True)):
        print(f"--- {family} ---")
        for name in model_names():
            if issubclass(REGISTRY[name], RuleBasedModel) == want:
                print(f"  {name:<13}{getattr(REGISTRY[name], 'summary', '')}")
    return 0


def cmd_tasks(args: argparse.Namespace) -> int:
    from .tasks import TASKS
    for name, cls in sorted(TASKS.items()):
        print(f"{name:<8}{(cls.__doc__ or '').strip().splitlines()[0]}")
    return 0


def cmd_lessons(args: argparse.Namespace) -> int:
    from .data.curriculum import resolve_lessons
    names = resolve_lessons(args.select)
    for n in names:
        print(n)
    print(f"\n{len(names)} lessons", file=sys.stderr)
    return 0


def cmd_data(args: argparse.Namespace) -> int:
    from .data.curriculum import build_split
    counts = build_split(args.out, lessons=args.lessons, n_train=args.n_train,
                         n_eval=args.n_eval, language=args.language,
                         max_nodes=args.max_nodes)
    print(f"wrote {counts['train']} train and {counts['eval']} eval episodes "
          f"to {args.out}")
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    """Show one episode in both surfaces — the clearest picture of the setup."""
    from .data.curriculum import generate
    for ep in generate([args.lesson], n=1, seed0=args.seed, language=args.language):
        print(f"=== {ep.lesson_id}  seed={ep.seed}  instance={ep.instance_id}\n")
        print("--- text (next-token task) ---")
        print(ep.text)
        print(f"\n--- graph ({len(ep.graph)} nodes, masked-node task) ---")
        print(ep.graph.sexpr())
        print("\n--- node table ---")
        print(f"{'i':>4} {'type':<10}{'label':<20}{'parent':>7}{'slot':>5}{'depth':>6}")
        for i, (lab, typ) in enumerate(zip(ep.graph.labels, ep.graph.types)):
            print(f"{i:>4} {typ:<10}{lab[:19]:<20}{ep.graph.parent[i]:>7}"
                  f"{ep.graph.slot[i]:>5}{ep.graph.depth[i]:>6}")
    return 0


def cmd_train(args: argparse.Namespace) -> int:
    from .train import train
    cfg = _config_from_args(args)
    print(f"training {cfg.model} on {list(cfg.tasks)} -> {cfg.out}", flush=True)
    summary = train(cfg, progress=_progress)
    print(f"\n{summary['parameters']:,} parameters, "
          f"{summary['seconds']:.0f}s on {summary['device']}")
    print(json.dumps(summary["final"], indent=2))
    return 0


def cmd_sweep(args: argparse.Namespace) -> int:
    """Train several architectures under one identical config."""
    from .models import model_names
    from .report import comparison_table, load_summaries
    from .train import train

    names = _select_models(args.models)
    root = Path(args.out or "runs/sweep")
    done: list[Path] = []
    for name in names:
        cfg = _config_from_args(args)
        cfg.model = name
        cfg.out = str(root / name)
        print(f"\n=== {name} ===", flush=True)
        try:
            train(cfg, progress=_progress)
            done.append(root / name)
        except Exception as e:                                # keep the sweep going
            print(f"  {name} failed: {type(e).__name__}: {e}", file=sys.stderr)
    print("\n" + comparison_table(load_summaries(done)))
    return 0


def _select_models(spec: str | None) -> list[str]:
    """``all``, a family name, or a comma-separated list."""
    from .models import REGISTRY, model_names
    from .models.symbolic import RuleBasedModel
    if spec in (None, "all"):
        return model_names()
    if spec in ("neural", "rule-based", "symbolic"):
        want_rules = spec != "neural"
        return [n for n in model_names()
                if issubclass(REGISTRY[n], RuleBasedModel) == want_rules]
    return [m.strip() for m in spec.split(",") if m.strip()]


def cmd_eval(args: argparse.Namespace) -> int:
    from .agent import evaluate_choices
    from .data.curriculum import resolve_lessons
    from .tasks import make_task
    from .train import _add_lift, _task_kwargs, evaluate_model, load_data, load_run

    device = args.device or ("cuda" if _cuda() else "cpu")
    model, tok, cfg = load_run(args.run, device=device)
    if args.data:
        cfg.data = args.data
    train_eps, episodes = load_data(cfg)
    if args.lessons:
        keep = set(resolve_lessons(args.lessons))
        episodes = [e for e in episodes if e.lesson_id in keep]
    if args.limit:
        episodes = episodes[:args.limit]

    tasks = {n: make_task(n, **_task_kwargs(cfg, n)) for n in cfg.tasks}
    metrics = evaluate_model(model, tasks, episodes, tok,
                             batch_size=cfg.batch_size,
                             device=_device(device), amp=cfg.amp)
    # A score without its floor is not a result; the floor is refitted on the
    # training episodes and scored on exactly the eval slice being reported.
    floors = {n: t.floor(episodes, tok, train_eps) for n, t in tasks.items()}
    print(json.dumps(_add_lift(metrics, floors), indent=2))

    if args.curriculum:
        print("\n=== curriculum: choose the answer from the episode's options ===")
        report = evaluate_choices(model, tok, episodes, device=device,
                                  max_len=cfg.max_len)
        print(report.table(limit=args.limit_lessons))
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    from .report import comparison_table, history_table, load_summaries
    if args.history:
        print(history_table(args.runs[0]))
        return 0
    print(comparison_table(load_summaries(args.runs), sort_by=args.sort_by))
    return 0


def _cuda() -> bool:
    import torch
    return torch.cuda.is_available()


def _device(name: str):
    import torch
    return torch.device(name)


# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="symbolic-ai-models",
        description="Train and evaluate symbolic text models on one harness: "
                    "next-token prediction and masked graph-node prediction.")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("models", help="list architectures").set_defaults(fn=cmd_models)
    sub.add_parser("tasks", help="list tasks").set_defaults(fn=cmd_tasks)

    q = sub.add_parser("lessons", help="list curriculum lessons")
    q.add_argument("select", nargs="?", default="all",
                   help="all | core170 | tag:X | cap:X | a,b,c")
    q.set_defaults(fn=cmd_lessons)

    d = sub.add_parser("data", help="build a train/eval episode cache")
    d.add_argument("--out", default="data/default")
    d.add_argument("--lessons", default="all")
    d.add_argument("--n-train", dest="n_train", type=int, default=32)
    d.add_argument("--n-eval", dest="n_eval", type=int, default=8)
    d.add_argument("--language", default="english")
    d.add_argument("--max-nodes", dest="max_nodes", type=int, default=512)
    d.set_defaults(fn=cmd_data)

    i = sub.add_parser("inspect", help="show one episode as text and as a graph")
    i.add_argument("lesson")
    i.add_argument("--seed", type=int, default=0)
    i.add_argument("--language", default="english")
    i.set_defaults(fn=cmd_inspect)

    t = sub.add_parser("train", help="train one architecture")
    _add_train_flags(t)
    t.set_defaults(fn=cmd_train)

    s = sub.add_parser("sweep", help="train several architectures identically")
    _add_train_flags(s)
    s.add_argument("--models", default="all",
                   help="all (default) | neural | symbolic | a,comma,list")
    s.set_defaults(fn=cmd_sweep)

    e = sub.add_parser("eval", help="score a finished run")
    e.add_argument("run")
    e.add_argument("--data", help="episode cache to evaluate on")
    e.add_argument("--lessons", help="restrict to these lessons")
    e.add_argument("--limit", type=int, help="cap the number of episodes")
    e.add_argument("--limit-lessons", dest="limit_lessons", type=int, default=30)
    e.add_argument("--curriculum", action="store_true",
                   help="also score by choosing among the episode's options")
    e.add_argument("--device")
    e.set_defaults(fn=cmd_eval)

    c = sub.add_parser("compare", help="put finished runs side by side")
    c.add_argument("runs", nargs="+")
    c.add_argument("--sort-by", dest="sort_by", default="lbl lift")
    c.add_argument("--history", action="store_true",
                   help="show the eval curve of the first run instead")
    c.set_defaults(fn=cmd_compare)
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":                                    # pragma: no cover
    raise SystemExit(main())
