"""Run the multilingual protocol one step per process, resumably.

    uv run python scripts/polyglot_lolo.py mixture
    uv run python scripts/polyglot_lolo.py fold 0 1 2 3 4 5
    uv run python scripts/polyglot_lolo.py fold 0 1 --arms polycky-001,polycky-wide \
        --tag beam

Each step writes ``runs/polyglot/<protocol>-<fold>.json`` the moment it
finishes and is skipped if that file already exists, so an interruption costs
one step. A single process covering all of it takes about forty minutes and is
killed at twenty, taking its process group with it -- that is measured here and
recorded in `notes/findings/2026-08-13-the-language-representation-is-orthographic.md`,
not a precaution someone invented.
"""

from __future__ import annotations

import pathlib
import sys
import time

from symbolic_ai_core.data import langdb
from symbolic_ai_parsers.polyglot import ARMS, N_FOLDS, run_step

OUT = pathlib.Path("runs/polyglot")


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    langdb.enable()
    arms, tag = list(ARMS), ""
    rest: list[str] = []
    i = 0
    while i < len(argv):
        if argv[i] == "--arms":
            arms = [s.strip() for s in argv[i + 1].split(",") if s.strip()]
            i += 2
        elif argv[i] == "--tag":
            tag = argv[i + 1] + "-"
            i += 2
        else:
            rest.append(argv[i])
            i += 1

    protocol = rest[0]
    folds = [int(a) for a in rest[1:]] or ([0] if protocol == "mixture"
                                           else list(range(N_FOLDS)))
    for fold in folds:
        dest = OUT / f"{tag}{protocol}-{fold}.json"
        if dest.exists():
            print(f"{dest.name} exists, skipping", flush=True)
            continue
        t = time.time()
        print(f"== {tag}{protocol} fold {fold}", flush=True)
        run_step(protocol, fold, out=dest, arms=arms)
        print(f"{dest.name} {time.time() - t:.0f}s", flush=True)
    return 0


if __name__ == "__main__":                                    # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
