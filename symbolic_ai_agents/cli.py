"""``symbolic_ai_agents`` — list, inspect, run, sweep, compare, read."""

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
    from .train import RunConfig
    data: dict[str, Any] = {}
    if args.config:
        data.update(_load_toml(args.config))
    known = {f.name for f in fields(RunConfig)}
    for key, value in vars(args).items():
        if key in known and value is not None:
            data[key] = value
    if isinstance(data.get("envs"), str):
        data["envs"] = tuple(e.strip() for e in data["envs"].split(",") if e.strip())
    if isinstance(data.get("extra"), str):
        data["extra"] = json.loads(data["extra"])
    return RunConfig.from_dict(data)


def _add_run_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument("--config", help="TOML file of defaults; flags override it")
    p.add_argument("--agent", help="policy id (see `symbolic-ai-agents agents`)")
    p.add_argument("--envs", help="comma-separated: choice, retry, repair, probe")
    p.add_argument("--data", help="a directory built by `symbolic-ai-models data`")
    p.add_argument("--lessons", help="all | core170 | tag:X | cap:X | a,b,c")
    p.add_argument("--n-train", dest="n_train", type=int)
    p.add_argument("--n-eval", dest="n_eval", type=int)
    p.add_argument("--language")
    p.add_argument("--max-nodes", dest="max_nodes", type=int)
    p.add_argument("--vocab-size", dest="vocab_size", type=int)
    p.add_argument("--tries", type=int, help="retry: attempts allowed")
    p.add_argument("--mask-rate", dest="mask_rate", type=float,
                   help="repair: share of maskable nodes drawn to ask about")
    p.add_argument("--max-steps", dest="max_steps", type=int,
                   help="repair: nodes asked about per episode")
    p.add_argument("--max-actions", dest="max_actions", type=int,
                   help="repair: candidate labels offered per node")
    p.add_argument("--probe-cost", dest="probe_cost", type=float,
                   help="probe: what one reveal costs")
    p.add_argument("--max-probes", dest="max_probes", type=int)
    p.add_argument("--keep", type=int, help="trajectories written out per env")
    p.add_argument("--seed", type=int)
    p.add_argument("--extra", help="JSON of agent-specific options")
    p.add_argument("--out", help="output directory for the run")


def _progress(note: str) -> None:
    print(f"  {note}", flush=True)


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------
def cmd_agents(args: argparse.Namespace) -> int:
    from .agents import REGISTRY, agent_names
    from .envs.base import FLOOR_POLICIES
    for name in agent_names():
        mark = " (floor)" if name in FLOOR_POLICIES else ""
        print(f"  {name:<18}{getattr(REGISTRY[name], 'summary', '')}{mark}")
    print("\n(floor) = also one of the reference policies every environment's "
          "floor is the best of, so it has zero lift wherever it wins.",
          file=sys.stderr)
    return 0


def cmd_envs(args: argparse.Namespace) -> int:
    from .envs import build, env_names
    # Built rather than read off the class: `retry` and `probe` set their
    # horizon from their own config, so the class attribute is 1 for everything
    # and would print a table saying nothing is multi-step.
    for name in env_names():
        env = build(name)
        kind = "interactive" if env.interactive else "one-shot"
        print(f"  {name:<10}{kind:<13}horizon {env.horizon:<4}{env.summary}")
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    """Show one episode as each environment presents it — the clearest picture."""
    from symbolic_ai_models.data.curriculum import generate

    from .envs import build, env_names
    from .train import RunConfig, make_tokenizer

    episodes = list(generate([args.lesson], n=1, seed0=args.seed,
                             language=args.language))
    if not episodes:
        print(f"{args.lesson}: generated nothing", file=sys.stderr)
        return 1
    ep = episodes[0]
    tok = make_tokenizer(RunConfig(vocab_size=args.vocab_size), episodes)
    names = [args.env] if args.env else env_names()
    print(f"=== {ep.lesson_id}  seed={ep.seed}  instance={ep.instance_id}")
    print(f"    answer: {ep.answer!r}\n")
    for name in names:
        env = build(name)
        obs = env.reset(ep, tok=tok)
        print(f"--- {name} (horizon {env.horizon}) ---")
        print(obs.text)
        print(f"  actions: {list(obs.actions)[:12]}")
        if obs.probes:
            print(f"  probes:  {list(obs.probes)}")
        print(f"  oracle:  {env.oracle()!r}\n")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    from .report import environment_table
    from .train import run
    cfg = _config_from_args(args)
    print(f"running {cfg.agent} in {list(cfg.envs)} -> {cfg.out}", flush=True)
    summary = run(cfg, progress=_progress)
    print(f"\n{summary['parameters']:,} learned, {summary['seconds']:.0f}s")
    print(environment_table(summary))
    return 0


def _already_ran(out: Path) -> bool:
    """Did this directory finish?

    Unlike the model harness, there is no step budget to compare against: an
    agent fits in one pass, so "a summary exists" really is "this is complete".
    A config change that would make the old numbers wrong is caught by
    :func:`symbolic_ai_agents.report.config_drift` at print time rather than
    silently skipped here.
    """
    return (out / "summary.json").exists()


def cmd_sweep(args: argparse.Namespace) -> int:
    """Run several agents under one identical config."""
    from .agents import agent_names
    from .report import comparison_table, load_summaries
    from .train import run

    names = (agent_names() if args.agents in (None, "all")
             else [a.strip() for a in args.agents.split(",") if a.strip()])
    root = Path(args.out or "runs/agent-sweep")
    done: list[Path] = []
    if args.resume:
        finished = [n for n in names if _already_ran(root / n)]
        if finished:
            print(f"resuming: {len(finished)} already complete "
                  f"({', '.join(finished)})", flush=True)
        done.extend(root / n for n in finished)
        names = [n for n in names if n not in set(finished)]
    for name in names:
        cfg = _config_from_args(args)
        cfg.agent = name
        cfg.out = str(root / name)
        print(f"\n=== {name} ===", flush=True)
        try:
            run(cfg, progress=_progress)
            done.append(root / name)
        except Exception as e:                            # keep the sweep going
            print(f"  {name} failed: {type(e).__name__}: {e}", file=sys.stderr)
    print("\n" + comparison_table(load_summaries(done), sort_by=args.sort_by))
    return 0


def cmd_eval(args: argparse.Namespace) -> int:
    from symbolic_ai_models.data.curriculum import resolve_lessons

    from .calibration import calibrate_agent
    from .report import environment_table
    from .train import add_lift, evaluate_agent, load_data, load_run, make_envs

    agent, tok, cfg = load_run(args.run)
    if args.data:
        cfg.data = args.data
    train_eps, episodes = load_data(cfg)
    if args.lessons:
        keep = set(resolve_lessons(args.lessons))
        episodes = [e for e in episodes if e.lesson_id in keep]
    if args.limit:
        episodes = episodes[:args.limit]

    envs = make_envs(cfg)
    if args.envs:
        wanted = {e.strip() for e in args.envs.split(",")}
        envs = {k: v for k, v in envs.items() if k in wanted}
    metrics, kept = evaluate_agent(agent, envs, episodes, tok, keep=args.keep)
    # A score without its floor is not a result; the floor is refitted on the
    # training episodes and run on exactly the slice being reported.
    floors = {n: e.floor(episodes, tok, train_eps) for n, e in envs.items()}
    print(environment_table({"agent": cfg.agent,
                             "parameters": agent.n_parameters(),
                             "final": add_lift(metrics, floors)}))

    if args.calibration:
        for name, trajectories in kept.items():
            print(f"\n=== calibration: {name} ===")
            print(calibrate_agent(trajectories).table())
    return 0


def cmd_trace(args: argparse.Namespace) -> int:
    from .trace import read_trajectories, transcript, worst
    path = Path(args.run)
    path = path / "trajectories.jsonl" if path.is_dir() else path
    if not path.exists():
        print(f"no trajectories at {path}", file=sys.stderr)
        return 1
    rows = read_trajectories(path, env=args.env, lesson=args.lesson)
    if args.worst:
        rows = worst(rows, limit=args.n)
    print(transcript(rows, limit=args.n, show_observation=not args.no_observation))
    return 0


def cmd_shortcuts(args: argparse.Namespace) -> int:
    """What the parameter-free cheats score — a floor and a generator audit."""
    from symbolic_ai_models.data.curriculum import generate, resolve_lessons
    from symbolic_ai_models.shortcuts import shortcut_table
    episodes = list(generate(resolve_lessons(args.lessons), n=args.n,
                             seed0=1_000_000, language=args.language))
    print(f"{len(episodes)} episodes from evaluation seeds\n")
    print(shortcut_table(episodes))
    print("\na lesson where one of these scores highly has leaked; that is a "
          "fact about the lesson, not about any agent that beats it.")
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    from .report import comparison_table, environment_table, load_summaries
    summaries = load_summaries(args.runs)
    if args.full:
        for s in summaries:
            print(environment_table(s))
            print()
        return 0
    print(comparison_table(summaries, sort_by=args.sort_by))
    return 0


# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="symbolic-ai-agents",
        description="Run symbolic policies in text environments built from the "
                    "same curriculum episodes symbolic-ai-models trains on.")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("agents", help="list policies").set_defaults(fn=cmd_agents)
    sub.add_parser("envs", help="list environments").set_defaults(fn=cmd_envs)

    i = sub.add_parser("inspect",
                       help="show one episode as each environment presents it")
    i.add_argument("lesson")
    i.add_argument("--env", help="only this environment")
    i.add_argument("--seed", type=int, default=0)
    i.add_argument("--language", default="english")
    i.add_argument("--vocab-size", dest="vocab_size", type=int, default=2048)
    i.set_defaults(fn=cmd_inspect)

    r = sub.add_parser("run", help="fit one policy and score it")
    _add_run_flags(r)
    r.set_defaults(fn=cmd_run)

    s = sub.add_parser("sweep", help="run several policies identically")
    _add_run_flags(s)
    s.add_argument("--agents", default="all",
                   help="all (default) or a,comma,list")
    s.add_argument("--resume", action="store_true",
                   help="skip agents that already wrote summary.json in --out")
    s.add_argument("--sort-by", dest="sort_by", default=None)
    s.set_defaults(fn=cmd_sweep)

    e = sub.add_parser("eval", help="score a finished run")
    e.add_argument("run")
    e.add_argument("--data", help="episode cache to evaluate on")
    e.add_argument("--envs", help="restrict to these environments")
    e.add_argument("--lessons", help="restrict to these lessons")
    e.add_argument("--limit", type=int, help="cap the number of episodes")
    e.add_argument("--keep", type=int, default=64)
    e.add_argument("--calibration", action="store_true",
                   help="also report stated confidence against observed accuracy")
    e.set_defaults(fn=cmd_eval)

    t = sub.add_parser("trace", help="read trajectories (not a metric)")
    t.add_argument("run")
    t.add_argument("--env", help="only this environment")
    t.add_argument("--lesson", help="only this lesson")
    t.add_argument("-n", type=int, default=10)
    t.add_argument("--worst", action="store_true",
                   help="show the lowest-return trajectories")
    t.add_argument("--no-observation", dest="no_observation", action="store_true",
                   help="omit what the agent saw")
    t.set_defaults(fn=cmd_trace)

    sc = sub.add_parser("shortcuts",
                        help="what the parameter-free cheats score on these lessons")
    sc.add_argument("--lessons", default="all")
    sc.add_argument("-n", type=int, default=8)
    sc.add_argument("--language", default="english")
    sc.set_defaults(fn=cmd_shortcuts)

    c = sub.add_parser("compare", help="put finished runs side by side")
    c.add_argument("runs", nargs="+")
    c.add_argument("--sort-by", dest="sort_by", default=None)
    c.add_argument("--full", action="store_true",
                   help="every metric of every environment, one run at a time")
    c.set_defaults(fn=cmd_compare)
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":                                    # pragma: no cover
    raise SystemExit(main())
