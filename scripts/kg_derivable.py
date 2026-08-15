"""How many entities can anchor a *derivable* slot? The number that gates the line.

A derivability curriculum needs an entity that satisfies two conditions at once:

1. it can be **anchored** — something says what it is, so a lesson can bind it
   (`is-a` / `instance-of`);
2. at least one attribute of it is **determined** — something says what follows
   from being that, so the attribute slot need not be drawn
   (`has-property`, `capable-of`, `used-for`, `made-of`, `causes`, or the ATOMIC
   if-then block).

Either alone is useless. An entity with a type and no consequences gives a slot
nothing to derive; an entity with properties and no type cannot be anchored by a
lesson. **The intersection is the population, and its size is the ceiling on how
much of the curriculum can carry a derived slot at all.**

This is deliberately measured *before* any model is built, because the previous
KG arm returned a null that was uninterpretable, and the arm before that spent a
sweep on a treatment whose reach nobody had priced. Coverage first is the rule
this line keeps having to relearn.

The output is a `stats.json`, which `.gitignore` tracks, so the number survives a
clone even though the 98 MB it was computed from does not.
"""

from __future__ import annotations

import argparse
import gzip
import json
from collections import Counter, defaultdict
from pathlib import Path

#: Relations that let a lesson *bind* an entity to a class.
ANCHOR = {"is-a", "instance-of"}

#: Relations whose object is *determined* by the subject — the thing that makes
#: a slot derivable rather than drawn. The ATOMIC block is included because an
#: if-then consequence is exactly a determined slot, which is the whole point.
DERIVE = {"has-property", "capable-of", "used-for", "made-of", "causes", "has-a",
          "desires", "not-desires", "manner-of", "defined-as",
          "agent-attribute", "agent-effect", "agent-wants", "agent-needs",
          "agent-reacts", "agent-intends", "other-wants", "other-effect",
          "other-reacts", "precondition-of", "subevent-of"}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("normalized", help="kg/normalized/vN")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    root = Path(args.normalized)
    anchored: set[str] = set()
    derivable: dict[str, Counter[str]] = defaultdict(Counter)
    per_rel: Counter[str] = Counter()
    n = 0

    for f in sorted(root.glob("*.ndjson.gz")):
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            for line in fh:
                r = json.loads(line)
                p = r["p"]
                n += 1
                if p in ANCHOR:
                    anchored.add(r["s"])
                elif p in DERIVE:
                    derivable[r["s"]][p] += 1
                    per_rel[p] += 1

    both = anchored & set(derivable)
    # An attribute is only *derivable* if the anchor determines it uniquely
    # enough to be predicted. One object per (entity, relation) is the clean
    # case; several means the lesson must pick, which is a different task.
    unique = sum(1 for e in both if all(c == 1 for c in derivable[e].values()))

    stats = {
        "triples_read": n,
        "entities_anchorable": len(anchored),
        "entities_with_a_determined_attribute": len(derivable),
        "entities_BOTH": len(both),
        "of_those_single_valued": unique,
        "note": ("`entities_BOTH` is the population a derivability curriculum can "
                 "draw from: anchorable AND carrying at least one determined "
                 "attribute. `of_those_single_valued` is the subset where every "
                 "determining relation has exactly one object, which is the clean "
                 "case -- several objects means the lesson must choose, which is a "
                 "different and harder task than deriving."),
        "determining_relations": dict(per_rel.most_common()),
    }
    out = Path(args.out or (root / "stats.json"))
    out.write_text(json.dumps(stats, indent=2, sort_keys=True), encoding="utf-8")

    print(f"triples read                     {n:>12,}")
    print(f"anchorable (is-a/instance-of)    {len(anchored):>12,}")
    print(f"with a determined attribute      {len(derivable):>12,}")
    print(f"BOTH -- the usable population    {len(both):>12,}")
    print(f"  of those, single-valued        {unique:>12,}")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
