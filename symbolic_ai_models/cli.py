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
    p.add_argument("--languages",
                   help="comma-separated packs; renders the same seeds in each "
                        "and interleaves them (an exact parallel corpus)")
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


def cmd_readouts(args: argparse.Namespace) -> int:
    """What a model's output can be *read as*, and which channel each one reads.

    Listed alongside the models and the parsers because it is the same kind of
    knob as either: swapping the readout under a fixed model measures the
    readout, swapping the model under a fixed readout measures the model, and
    neither comparison is available while there is only one of them.
    """
    from symbolic_ai_core.readout import REGISTRY

    from . import readouts as _  # noqa: F401  (registration side effect)
    try:
        import symbolic_ai_agents.readouts as _agents  # noqa: F401
    except ImportError:                                   # pragma: no cover
        pass
    for name in REGISTRY.names():
        cls = REGISTRY.get(name)
        mark = "  CEILING" if getattr(cls, "ceiling", False) else ""
        print(f"  {name:<14}{cls.channel:<8}{cls.summary}{mark}")
    return 0


def cmd_tasks(args: argparse.Namespace) -> int:
    from .tasks import TASKS
    for name, cls in sorted(TASKS.items()):
        print(f"{name:<8}{(cls.__doc__ or '').strip().splitlines()[0]}")
    return 0


def cmd_lessons(args: argparse.Namespace) -> int:
    from symbolic_ai_core.data.curriculum import resolve_lessons
    names = resolve_lessons(args.select)
    for n in names:
        print(n)
    print(f"\n{len(names)} lessons", file=sys.stderr)
    return 0


def cmd_data(args: argparse.Namespace) -> int:
    from symbolic_ai_core.data.curriculum import build_split
    counts = build_split(args.out, lessons=args.lessons, n_train=args.n_train,
                         n_eval=args.n_eval, language=args.language,
                         max_nodes=args.max_nodes)
    print(f"wrote {counts['train']} train and {counts['eval']} eval episodes "
          f"to {args.out}")
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    """Show one episode in both surfaces — the clearest picture of the setup."""
    from symbolic_ai_core.data.curriculum import generate
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


def _already_ran(out: Path, args: argparse.Namespace) -> bool:
    """Did this directory finish *the budget being asked for*?

    Only the step budget is compared. It is the one knob a re-run routinely
    raises, and it is the one whose staleness is invisible in the printed table
    -- every other config change (different lessons, a different mask rate)
    produces numbers that obviously do not belong next to the others, whereas a
    stale 300-step row sits in the table looking exactly like a 2000-step one.

    A rule-based model reports `steps` as 0 because it fits in a single pass and
    never consumed a budget, so it is complete whatever is asked of it.
    """
    summary = out / "summary.json"
    if not summary.exists():
        return False
    if getattr(args, "steps", None) is None:
        return True
    try:
        ran = int(json.loads(summary.read_text()).get("steps", 0))
    except (ValueError, OSError):
        return False                     # unreadable: re-run rather than trust
    return ran == 0 or ran >= int(args.steps)


def _sweep_root(args: argparse.Namespace) -> Path:
    """Where a sweep writes: ``--out``, then the config's ``out``, then default.

    The config's was ignored until now, so ``sweep --config
    configs/full179.toml`` wrote to ``runs/sweep`` while the file said
    ``runs/full179`` — silently, and into a directory some *previous* sweep may
    already have filled, where ``--resume`` would then skip models on the
    strength of another run's summaries. That is the same failure ``_already_ran``
    exists to prevent, arriving by a different door.

    Read out of the TOML rather than off the built :class:`TrainConfig`, because
    ``TrainConfig.out`` has a default of its own and an unset field is
    indistinguishable from a set one once the config exists.
    """
    from_config = _load_toml(args.config).get("out") if args.config else None
    return Path(args.out or from_config or "runs/sweep")


def cmd_sweep(args: argparse.Namespace) -> int:
    """Train several architectures under one identical config."""
    from .models import model_names
    from .report import comparison_table, load_summaries
    from .train import train

    names = _select_models(args.models)
    root = _sweep_root(args)
    done: list[Path] = []
    if args.resume:
        # A sweep over the whole curriculum takes long enough that it will not
        # always survive the session that started it, and losing eleven finished
        # models because the twelfth was interrupted is the kind of waste that
        # quietly discourages running the honest experiment at all.
        #
        # "Complete" has to mean *the requested budget was run*, not merely that
        # a summary file exists. Raising `--steps` on a directory of finished
        # 300-step runs and asking to resume skipped all six and reprinted the
        # old table -- it looked like a successful re-run and was a no-op, which
        # is the most expensive kind of wrong answer this repo can produce.
        finished = [n for n in names if _already_ran(root / n, args)]
        if finished:
            print(f"resuming: {len(finished)} already complete "
                  f"({', '.join(finished)})", flush=True)
        done.extend(root / n for n in finished)
        names = [n for n in names if n not in set(finished)]
    for name in names:
        cfg = _config_from_args(args)
        cfg.model = name
        cfg.out = str(root / name)
        # A sweep asked to resume also resumes each model's partial training,
        # not merely skipping the ones that finished.
        cfg.resume = bool(args.resume)
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
    # Resolve bare names to their registered version, so `--models corefer`
    # writes `runs/.../corefer-001` and the run directory says which model
    # produced it. A pinned name passes through untouched.
    from .models.registry import get as _get
    out = []
    for m in spec.split(","):
        m = m.strip()
        if not m:
            continue
        try:
            out.append(_get(m).name)
        except KeyError:
            out.append(m)          # let train report the unknown-model error
    return out


def cmd_eval(args: argparse.Namespace) -> int:
    from .agent import evaluate_choices
    from symbolic_ai_core.data.curriculum import resolve_lessons
    from .tasks import make_task
    from .train import _add_lift, _task_kwargs, evaluate_model, load_data, load_run

    device = args.device or "cpu"
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

    if args.calibration:
        from symbolic_ai_core.calibration import calibrate_model
        for name, task in tasks.items():
            print(f"\n=== calibration: {name} ===")
            print(calibrate_model(model, task, episodes, tok,
                                  device=_device(device)).table())

    if args.curriculum:
        print("\n=== curriculum: choose the answer from the episode's options ===")
        report = evaluate_choices(model, tok, episodes, device=device,
                                  max_len=cfg.max_len)
        print(report.table(limit=args.limit_lessons))
    return 0


def cmd_parsers(args: argparse.Namespace) -> int:
    from .parsers import REGISTRY, parser_names
    for name in parser_names():
        cls = REGISTRY[name]
        kind = "learned" if cls.learned else "written"
        print(f"{name:<14}{kind:<9}{cls.summary}")
    return 0


def cmd_parse_eval(args: argparse.Namespace) -> int:
    """Score parsers against the structure the curriculum generated the text from."""
    from symbolic_ai_core.data.curriculum import generate, resolve_lessons
    from .parsers import build, evaluate_parser, parser_names
    from .parsers.evaluate import ParserReport
    from .parsers.scale import curve_table, scaling_curve
    from .train import TrainConfig, build_tokenizer

    lessons = resolve_lessons(args.lessons)
    names = (parser_names() if args.parsers in (None, "all")
             else [p.strip() for p in args.parsers.split(",")])

    if args.curve:
        sizes = [int(s) for s in args.curve.split(",")]
        print(curve_table(scaling_curve(names, lessons, sizes=sizes,
                                        n_eval=args.n_eval)))
        return 0

    training = list(generate(lessons, n=args.n_train, seed0=0))
    evaluation = list(generate(lessons, n=args.n_eval, seed0=1_000_000))
    tok = build_tokenizer(TrainConfig(vocab_size=args.vocab_size), training)
    print(f"fitted on {len(training)} episodes, scored on {len(evaluation)} "
          f"from disjoint seeds\n")
    print(ParserReport.header())
    for name in names:
        parser = build(name)
        parser.fit(training, tok)
        print(evaluate_parser(parser, evaluation, tok).row())
    if args.render:
        parser = build(args.render)
        parser.fit(training, tok)
        print(f"\n=== {args.render} ===\n{parser.render()}")
    return 0


def cmd_sample(args: argparse.Namespace) -> int:
    """Decode continuations and print them, for a person or a reviewing model."""
    from .decode import SamplingConfig, sample_episodes, transcript, write_json
    from symbolic_ai_core.data.curriculum import resolve_lessons
    from .train import load_data, load_run

    device = args.device or "cpu"
    model, tok, cfg = load_run(args.run, device=device)
    if args.data:
        cfg.data = args.data
    _, episodes = load_data(cfg)
    if args.lessons:
        keep = set(resolve_lessons(args.lessons))
        episodes = [e for e in episodes if e.lesson_id in keep]

    # Spread the sample across lessons rather than taking the first N, which
    # would be the first lesson in registry order and nothing else.
    if args.per_lesson:
        seen: dict[str, int] = {}
        picked = []
        for e in episodes:
            if seen.get(e.lesson_id, 0) < args.per_lesson:
                seen[e.lesson_id] = seen.get(e.lesson_id, 0) + 1
                picked.append(e)
        episodes = picked
    if args.n:
        episodes = episodes[:args.n]

    sampling = SamplingConfig(
        max_new_tokens=args.max_new_tokens, greedy=not args.sample,
        temperature=args.temperature, top_k=args.top_k, top_p=args.top_p,
        seed=args.seed)
    samples = sample_episodes(model, tok, episodes, config=sampling, device=device)
    print(transcript(samples, show_prompt=not args.no_prompt))
    if args.json:
        path = write_json(args.json, samples, model=cfg.model, config=sampling)
        print(f"\nwrote {len(samples)} samples to {path}", file=sys.stderr)
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
    sub.add_parser("readouts", help="list readouts").set_defaults(fn=cmd_readouts)
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
    t.add_argument("--resume", action="store_true",
                   help="continue from out/checkpoint.pt if it exists")
    t.set_defaults(fn=cmd_train)

    s = sub.add_parser("sweep", help="train several architectures identically")
    _add_train_flags(s)
    s.add_argument("--models", default="all",
                   help="all (default) | neural | symbolic | a,comma,list")
    s.add_argument("--resume", action="store_true",
                   help="skip models that already wrote summary.json in --out")
    s.set_defaults(fn=cmd_sweep)

    e = sub.add_parser("eval", help="score a finished run")
    e.add_argument("run")
    e.add_argument("--data", help="episode cache to evaluate on")
    e.add_argument("--lessons", help="restrict to these lessons")
    e.add_argument("--limit", type=int, help="cap the number of episodes")
    e.add_argument("--limit-lessons", dest="limit_lessons", type=int, default=30)
    e.add_argument("--calibration", action="store_true",
                   help="also report stated confidence against observed accuracy")
    e.add_argument("--curriculum", action="store_true",
                   help="also score by choosing among the episode's options")
    e.add_argument("--device")
    e.set_defaults(fn=cmd_eval)

    p_ = sub.add_parser("sample", help="decode continuations to read (not a metric)")
    p_.add_argument("run")
    p_.add_argument("--data", help="episode cache to sample from")
    p_.add_argument("--lessons", help="restrict to these lessons")
    p_.add_argument("-n", type=int, help="cap the total number of samples")
    p_.add_argument("--per-lesson", dest="per_lesson", type=int, default=2,
                    help="how many episodes per lesson (default 2)")
    p_.add_argument("--max-new-tokens", dest="max_new_tokens", type=int, default=24)
    p_.add_argument("--sample", action="store_true",
                    help="sample instead of decoding greedily")
    p_.add_argument("--temperature", type=float, default=1.0)
    p_.add_argument("--top-k", dest="top_k", type=int, default=0)
    p_.add_argument("--top-p", dest="top_p", type=float, default=0.0)
    p_.add_argument("--json", help="also write the samples as JSON, for an "
                                   "LLM reviewer")
    p_.add_argument("--no-prompt", dest="no_prompt", action="store_true",
                    help="omit prompts from the transcript")
    p_.add_argument("--seed", type=int, default=0)
    p_.add_argument("--device")
    p_.set_defaults(fn=cmd_sample)

    sub.add_parser("parsers", help="list parsers").set_defaults(fn=cmd_parsers)

    pe = sub.add_parser("parse-eval",
                        help="score parsers against the generator's own structure")
    pe.add_argument("--parsers", default="all", help="all (default) or a,comma,list")
    pe.add_argument("--lessons", default="all")
    pe.add_argument("--n-train", dest="n_train", type=int, default=32)
    pe.add_argument("--n-eval", dest="n_eval", type=int, default=8)
    pe.add_argument("--vocab-size", dest="vocab_size", type=int, default=4096)
    pe.add_argument("--curve", help="comma-separated training sizes, e.g. 4,16,64,256")
    pe.add_argument("--render", help="also print what this parser learned")
    pe.set_defaults(fn=cmd_parse_eval)

    c = sub.add_parser("compare", help="put finished runs side by side")
    c.add_argument("runs", nargs="+")
    c.add_argument("--sort-by", dest="sort_by", default="ans lift")
    c.add_argument("--history", action="store_true",
                   help="show the eval curve of the first run instead")
    c.set_defaults(fn=cmd_compare)
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":                                    # pragma: no cover
    raise SystemExit(main())
