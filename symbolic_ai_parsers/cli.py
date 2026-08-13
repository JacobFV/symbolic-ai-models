"""``symbolic-ai-parsers`` — list the parsers, or run the authority sweep."""

from __future__ import annotations

import argparse

from . import REGISTRY, build, parser_names
from .evaluate import LANGUAGES, ParserReport, floor_row, run_sweep
from .scoring import METRICS


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="symbolic-ai-parsers", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="every registered parser")

    sw = sub.add_parser("sweep", help="fit on English train, score every language")
    sw.add_argument("--parsers", default=None,
                    help="comma-separated; default every registered parser")
    sw.add_argument("--lessons", default=None,
                    help="lesson selector; default every implemented lesson")
    sw.add_argument("--n-train", type=int, default=16)
    sw.add_argument("--n-eval", type=int, default=4)
    sw.add_argument("--languages", default=",".join(LANGUAGES))
    sw.add_argument("--max-nodes", type=int, default=128)
    sw.add_argument("--out", default=None, help="write the full report as JSON")

    args = ap.parse_args(argv)

    if args.cmd == "list":
        for name in parser_names():
            cls = REGISTRY[name]
            kind = "learned" if cls.learned else "written"
            print(f"{name:<18}{kind:<9}{cls.summary}")
        return 0

    names = [s.strip() for s in args.parsers.split(",")] if args.parsers else None
    langs = [s.strip() for s in args.languages.split(",") if s.strip()]
    print(ParserReport.header(), flush=True)
    reports = run_sweep(parsers=names, lessons=args.lessons,
                        n_train=args.n_train, n_eval=args.n_eval,
                        languages=langs, max_nodes=args.max_nodes, out=args.out)
    if reports:
        print(floor_row(reports[0].floors, "-"))
        print("\nlift over the constant floor, (score - floor) / (1 - floor)")
        print(ParserReport.header())
        for r in reports:
            print(r.lift_row())
    return 0


if __name__ == "__main__":                                    # pragma: no cover
    raise SystemExit(main())
