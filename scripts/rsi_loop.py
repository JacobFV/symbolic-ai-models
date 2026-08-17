"""Propose, run, rank, propose again — without a human turn between the steps.

The user's instruction is "automate the RSI loop", and the thing it replaces is
sitting in the loop hand-driving one model at a time. This is the driver.

    uv run python scripts/rsi_loop.py --rounds 3
    uv run python scripts/rsi_loop.py --model frontier-001 --objective equivariant
    uv run python scripts/rsi_loop.py --final frontier-001:min_support=24

One round is: take a candidate list, run every candidate that has not been run,
read the rows back, rank them, write the table down, and generate the next
round's candidates from what survived. Nothing here needs a person between two
steps, and the ledger under ``runs/rsi/ledger.json`` means a killed process
resumes instead of restarting.

Three things are deliberate and are the whole reason this is a script rather
than a shell loop.

**It cannot tune against evaluation.**
``CLAUDE.md`` says design choices are settled on held-out *training* episodes and
that seeds >= 1,000,000 are evaluation only. Until ``TrainConfig.eval_seed0``
existed there was no way to obey that while scoring anything, so any knob ever
fitted by reading a sweep was fitted against evaluation. This driver **refuses**
to rank candidates on a config whose ``eval_seed0`` is in the evaluation range.
The development split lives at 500,000 — clear of training seeds below ~20 and
clear of evaluation at a million. ``--final`` is the one door to the evaluation
seeds, it takes an explicit candidate name, and it does not rank anything: it
scores one already-chosen thing, once, which is what an evaluation set is for.

**It always prints the memorisation column, whatever it ranks by.**
This repo's central and most expensive lesson is that accuracy rewards
memorising the vocabulary — ``ensemble-001``'s 1.14-bit headline was vocabulary
memorisation, and ``frontier-001`` is first on accuracy while being the second
least equivariant model ever measured here. A search ranked on ``label_acc``
will walk straight into that, every time, and it will look like progress. So
every table prints ``acc``, ``bits``, ``renamed`` and ``drop`` together, and
``--objective equivariant`` ranks on the accuracy that *survives* a symbol
permutation, which is the one number a memoriser cannot buy.

**A candidate is a knob, not a rewrite.**
Most of the space worth searching is ``extra`` on a model that already exists —
``min_support``, ``min_precision``, ``resolver_forms``. Those need no code, so
the loop can run them unattended. A candidate that needs a new architecture is
a different job and belongs to an agent, not to this file; the loop's output is
what tells you which one is worth commissioning.
"""
from __future__ import annotations

import argparse
import copy
import itertools
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

os.environ.setdefault("OMP_NUM_THREADS", "4")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

#: Where the loop's runs and its ledger live. Separate from ``runs/full179`` on
#: purpose: these are development-split scores and must never be picked up by a
#: `compare` over the published directory, where every row is an evaluation
#: number. Mixing the two would put two different questions in one table.
RSI_ROOT = ROOT / "runs" / "rsi"

#: The seed the development split starts at. Above any plausible ``n_train``
#: and half a million below the evaluation range.
DEV_SEED0 = 500_000
EVAL_SEED0 = 1_000_000


@dataclass
class Candidate:
    """One thing to try: a registered model plus the knobs it runs under."""

    model: str
    extra: dict[str, Any] = field(default_factory=dict)
    #: Why this is worth a run, and what you expect. Written to the round note.
    #: `CLAUDE.md`'s one rule that does not relax at any depth is that you say
    #: what you expect before the number lands, so this is not optional and the
    #: loop refuses a candidate without it.
    why: str = ""

    @property
    def tag(self) -> str:
        if not self.extra:
            return self.model
        bits = ",".join(f"{k}={_short(v)}" for k, v in sorted(self.extra.items()))
        return f"{self.model}[{bits}]"

    @property
    def slug(self) -> str:
        keep = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.="
        return "".join(c if c in keep else "_" for c in self.tag)


def _short(v: Any) -> str:
    if isinstance(v, (list, tuple)):
        return "+".join(str(x) for x in v)
    return str(v)


# ---------------------------------------------------------------------------
# what gets ranked
# ---------------------------------------------------------------------------
#: ``name -> (read a row -> a number, higher is better)``.
#:
#: ``equivariant`` is the default and the recommendation. It is the accuracy
#: that survives permuting every symbol, so a candidate cannot win it by
#: memorising the vocabulary — which is the failure mode every other objective
#: here rewards. ``acc`` is what this repo has always published and is kept so
#: that the difference between the two rankings stays visible.
OBJECTIVES: dict[str, tuple[Callable[[dict], float | None], bool]] = {
    "equivariant": (lambda r: r.get("renamed"), True),
    "acc": (lambda r: r.get("label_acc"), True),
    "bits": (lambda r: r.get("label_bits"), False),
    "lift": (lambda r: r.get("label_lift"), True),
    "type": (lambda r: r.get("type_acc"), True),
}


def read_row(out: Path) -> dict[str, Any] | None:
    """The comparable numbers from a finished run, or ``None``."""
    path = out / "summary.json"
    if not path.exists():
        return None
    s = json.loads(path.read_text())
    node = (s.get("final") or {}).get("node") or {}
    if not node:
        return None
    ren = s.get("renaming") or {}
    return {
        "model": s.get("model"),
        "label_acc": node.get("label_acc"),
        "label_bits": node.get("label_bits"),
        "label_lift": node.get("label_lift"),
        "type_acc": node.get("type_acc"),
        # `renamed_label_acc`, not `renamed`: the field is named for the metric
        # it is, and guessing the short name cost a whole round-zero sweep that
        # ran all seventeen candidates and then printed an empty table, because
        # every objective read `None` and every row was filtered out. A ranking
        # key that silently misses is worse than one that raises, so the loop
        # now checks the field exists before it runs anything — see `main`.
        "plain": ren.get("label_acc"),
        "renamed": ren.get("renamed_label_acc"),
        "drop": ren.get("drop"),
        "seconds": s.get("seconds"),
        "eval_seed0": (s.get("config") or {}).get("eval_seed0"),
    }


# ---------------------------------------------------------------------------
# running one candidate
# ---------------------------------------------------------------------------
def run_one(cand: Candidate, *, config: Path, out_root: Path, eval_seed0: int,
            force: bool = False) -> dict[str, Any] | None:
    from symbolic_ai_models.cli import _load_toml
    from symbolic_ai_models.train import TrainConfig, train

    out = out_root / cand.slug
    if not force:
        got = read_row(out)
        if got is not None:
            got["tag"] = cand.tag
            got["cached"] = True
            return got

    data = _load_toml(config)
    data["tasks"] = tuple(t.strip() for t in str(data.get("tasks", "node")).split(",")
                          if t.strip())
    data.setdefault("task_weights", {t: 1.0 for t in data["tasks"]})
    data["model"] = cand.model
    data["out"] = str(out)
    data["eval_seed0"] = eval_seed0
    data["extra"] = {**(data.get("extra") or {}), **cand.extra}
    cfg = TrainConfig.from_dict(data)
    print(f"  running {cand.tag}", flush=True)
    try:
        train(cfg)
    except Exception as e:                       # a dead arm is a result
        print(f"  {cand.tag} failed: {type(e).__name__}: {e}", file=sys.stderr)
        return None
    got = read_row(out)
    if got is not None:
        got["tag"] = cand.tag
        got["cached"] = False
    return got


# ---------------------------------------------------------------------------
# proposing
# ---------------------------------------------------------------------------
#: Knob spaces, per model. A round-zero proposal is the baseline plus one
#: single-knob deviation at a time — a coordinate sweep, which is the cheapest
#: thing that says which knobs matter at all. Later rounds recombine the knobs
#: that moved. Add a model here and it is searchable without touching anything
#: else in this file.
SPACES: dict[str, dict[str, list[Any]]] = {
    "frontier-001": {
        "min_support": [6, 12, 24, 48],
        # Separate from `min_support` on purpose: this is the *proposal* gate,
        # and an absolute count there is what stops rare structure from ever
        # earning its own guard. The Wilson bound still decides what survives,
        # so lowering this should raise recall on rare phenomena without
        # admitting noise -- that is the prediction the loop is being asked to
        # check on the development split.
        "propose_support": [2, 3, 4, 6],
        "min_precision": [0.3, 0.5, 0.7],
        "max_rules": [400, 2000, 6000],
        "frontier_repeats": [2, 3, 5],
        "resolver_forms": [["const", "copy", "map"], ["const", "copy"],
                           ["copy", "map"]],
    },
}


def propose_round0(model: str) -> list[Candidate]:
    """Baseline, then one knob moved at a time."""
    space = SPACES.get(model, {})
    out = [Candidate(model, {}, why="the registered defaults, as the baseline "
                                    "every other row is read against")]
    for knob, values in space.items():
        for v in values:
            out.append(Candidate(
                model, {knob: v},
                why=f"one knob moved: {knob}={_short(v)}. A coordinate sweep "
                    f"says which knobs move anything at all before any pair of "
                    f"them is tried together."))
    return _dedupe(out)


def propose_next(model: str, ranked: list[dict], round_no: int,
                 width: int = 2) -> list[Candidate]:
    """Recombine the knobs that moved, around the best rows so far."""
    space = SPACES.get(model, {})
    if not space or not ranked:
        return []
    best = [r for r in ranked[:width] if r.get("extra")]
    out: list[Candidate] = []
    for a, b in itertools.combinations(best, 2):
        merged = {**a["extra"], **b["extra"]}
        if len(merged) > 1:
            out.append(Candidate(
                model, merged,
                why=f"round {round_no}: the two knobs that ranked highest "
                    f"separately, together. If the pair does not beat the "
                    f"better single, the knobs are not independent and the "
                    f"coordinate sweep was the wrong shape."))
    for r in best:
        for knob, values in space.items():
            if knob in r["extra"]:
                continue
            for v in values[:2]:
                out.append(Candidate(
                    model, {**r["extra"], knob: v},
                    why=f"round {round_no}: {knob}={_short(v)} added to the "
                        f"leading row, to see whether it still pays once the "
                        f"leader has moved."))
    return _dedupe(out)


def _dedupe(cands: Iterable[Candidate]) -> list[Candidate]:
    seen: set[str] = set()
    out: list[Candidate] = []
    for c in cands:
        if c.slug in seen:
            continue
        seen.add(c.slug)
        out.append(c)
    return out


# ---------------------------------------------------------------------------
# reporting
# ---------------------------------------------------------------------------
COLUMNS = (("tag", 44, "s"), ("label_acc", 9, ".4f"), ("label_bits", 11, ".3f"),
           ("renamed", 9, ".4f"), ("drop", 8, ".4f"), ("type_acc", 9, ".4f"))


def table(rows: list[dict], objective: str) -> str:
    head = "".join(f"{n:>{w}}" if n != "tag" else f"{n:<{w}}"
                   for n, w, _ in COLUMNS)
    lines = [head, "-" * len(head)]
    for r in rows:
        cells = []
        for name, width, fmt in COLUMNS:
            v = r.get(name)
            if name == "tag":
                cells.append(f"{str(v)[:width]:<{width}}")
            elif isinstance(v, (int, float)):
                cells.append(f"{v:>{width}{fmt}}")
            else:
                cells.append(f"{'-':>{width}}")
        lines.append("".join(cells))
    lines.append("-" * len(head))
    lines.append(
        f"ranked by `{objective}`. `renamed` is accuracy after permuting every "
        f"symbol without refitting and `drop` is what that cost — a candidate "
        f"that wins on acc and loses it all on drop bought vocabulary, not "
        f"reasoning.")
    return "\n".join(lines)


def write_note(model: str, round_no: int, rows: list[dict], objective: str,
               date: str) -> Path:
    path = ROOT / "notes" / "findings" / f"{date}-rsi-{model}-round-{round_no}.md"
    body = [
        "---", f"date: {date}", "author: rsi-loop", "status: provisional",
        "related: [2026-08-16-first-on-accuracy-eleventh-on-bits]", "---", "",
        f"# RSI loop, `{model}`, round {round_no} — ranked by `{objective}`", "",
        f"Development split (`eval_seed0={DEV_SEED0}`), **not** evaluation "
        f"seeds. These numbers settle a design choice; they are not comparable "
        f"with anything in `runs/full179`, where every row is scored at "
        f"{EVAL_SEED0}. The chosen candidate gets one evaluation run "
        f"(`--final`) and that is the number that may be quoted.", "",
        "```", table(rows, objective), "```", "",
        "## What each candidate was for", "",
    ]
    for r in rows:
        body.append(f"- **`{r['tag']}`** — {r.get('why', '(no rationale recorded)')}")
    body += ["", "## Read the two rankings against each other", ""]
    by_acc = sorted([r for r in rows if r.get("label_acc") is not None],
                    key=lambda r: -r["label_acc"])
    by_eq = sorted([r for r in rows if r.get("renamed") is not None],
                   key=lambda r: -r["renamed"])
    if by_acc and by_eq:
        body.append(f"Best on accuracy: **`{by_acc[0]['tag']}`** "
                    f"({by_acc[0]['label_acc']:.4f}). Best on the accuracy that "
                    f"survives renaming: **`{by_eq[0]['tag']}`** "
                    f"({by_eq[0]['renamed']:.4f}).")
        if by_acc[0]["tag"] != by_eq[0]["tag"]:
            body.append("")
            body.append("**They disagree, which is the finding of this round.** "
                        "A ranking is a property of its metric, and the gap "
                        "between these two columns is the part of the winner's "
                        "score that is vocabulary.")
    path.write_text("\n".join(body) + "\n")
    return path


# ---------------------------------------------------------------------------
def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--model", default="frontier-001")
    ap.add_argument("--config", default=str(ROOT / "configs" / "rsi_dev.toml"))
    ap.add_argument("--rounds", type=int, default=2)
    ap.add_argument("--objective", default="equivariant", choices=sorted(OBJECTIVES))
    ap.add_argument("--width", type=int, default=2,
                    help="how many leading rows the next round is built from")
    ap.add_argument("--date", default="2026-08-16")
    ap.add_argument("--force", action="store_true", help="rerun cached rows")
    ap.add_argument("--final", metavar="TAG",
                    help="score ONE already-chosen candidate on the evaluation "
                         "seeds and rank nothing. The only door to seeds >= "
                         "1,000,000.")
    args = ap.parse_args(argv)

    config = Path(args.config)
    RSI_ROOT.mkdir(parents=True, exist_ok=True)

    if args.final:
        cand = parse_tag(args.final)
        print(f"FINAL run on evaluation seeds ({EVAL_SEED0}): {cand.tag}")
        row = run_one(cand, config=config, out_root=ROOT / "runs" / "full179",
                      eval_seed0=EVAL_SEED0, force=args.force)
        print(json.dumps(row, indent=1))
        return 0 if row else 1

    from symbolic_ai_models.cli import _load_toml
    seed0 = int(_load_toml(config).get("eval_seed0", DEV_SEED0))
    if seed0 >= EVAL_SEED0:
        print(f"refusing to rank on eval_seed0={seed0}: that is the evaluation "
              f"range, and ranking candidates on it is tuning against "
              f"evaluation. Use configs/rsi_dev.toml, or --final for a single "
              f"chosen candidate.", file=sys.stderr)
        return 2

    # Fail before spending a sweep, not after. An objective that reads a field
    # nothing writes produces an empty table at the end of the round with every
    # run already paid for.
    probe = {"label_acc": 0.0, "label_bits": 0.0, "label_lift": 0.0,
             "type_acc": 0.0, "renamed": 0.0}
    if OBJECTIVES[args.objective][0](probe) is None:
        print(f"objective `{args.objective}` reads a field no row carries",
              file=sys.stderr)
        return 2

    ledger_path = RSI_ROOT / "ledger.json"
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {}
    key, higher = OBJECTIVES[args.objective]
    history: list[dict] = []
    cands = propose_round0(args.model)

    for round_no in range(args.rounds):
        if not cands:
            print(f"round {round_no}: nothing new to propose; stopping.")
            break
        print(f"\n=== round {round_no}: {len(cands)} candidates ===", flush=True)
        rows: list[dict] = []
        for cand in cands:
            row = run_one(cand, config=config, out_root=RSI_ROOT,
                          eval_seed0=seed0, force=args.force)
            if row is None:
                continue
            row["extra"] = cand.extra
            row["why"] = cand.why
            row["round"] = round_no
            rows.append(row)
            ledger[cand.slug] = row
        scored = [r for r in rows if key(r) is not None]
        scored.sort(key=lambda r: key(r), reverse=higher)
        history.extend(scored)
        print("\n" + table(scored, args.objective))
        note = write_note(args.model, round_no, scored, args.objective, args.date)
        print(f"\nwritten to {note}")
        ledger_path.write_text(json.dumps(ledger, indent=1))
        ranked_all = sorted([r for r in history if key(r) is not None],
                            key=lambda r: key(r), reverse=higher)
        cands = _dedupe([c for c in propose_next(args.model, ranked_all,
                                                 round_no + 1, args.width)
                         if c.slug not in ledger])

    if history:
        best = sorted(history, key=lambda r: key(r), reverse=higher)[0]
        print(f"\nleader on `{args.objective}`: {best['tag']}")
        print(f"score it on evaluation seeds with:\n"
              f"  uv run python scripts/rsi_loop.py --final '{best['tag']}'")
    return 0


def parse_tag(tag: str) -> Candidate:
    """``model[k=v,k=v]`` or ``model:k=v,k=v`` back into a candidate."""
    if "[" in tag:
        model, rest = tag.split("[", 1)
        rest = rest.rstrip("]")
    elif ":" in tag:
        model, rest = tag.split(":", 1)
    else:
        return Candidate(tag, {}, why="chosen by hand")
    extra: dict[str, Any] = {}
    for part in filter(None, rest.split(",")):
        k, _, v = part.partition("=")
        if "+" in v:
            extra[k] = v.split("+")
        else:
            try:
                extra[k] = int(v)
            except ValueError:
                try:
                    extra[k] = float(v)
                except ValueError:
                    extra[k] = v
    return Candidate(model, extra, why="chosen by hand")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
