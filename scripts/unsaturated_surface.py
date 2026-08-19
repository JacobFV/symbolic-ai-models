"""What the flood reader headline is worth once the template is taken away.

`read_signature` scores 1.000 on this surface and the milestone quotes it as
zero reader loss. It also branches on ``pi == 0``, ``pi == 1``, ``pi == 2``,
``pi == 3`` -- it knows the generator's five-paragraph template by **index**. So
the headline measures the harness at least as much as it measures reading, which
is what ``state.yml`` means by the surface being saturated.

Two giveaways, priced separately because a reader may lean on either:

- **section headings** (``ROAD NETWORK.``, ``OVERNIGHT.`` ...), which name the
  claim kind outright;
- **fixed paragraph order**, which is what the ``pi ==`` branches consume.

And a new arm that keeps the one structural fact surviving a reorder -- which
sentences share a paragraph -- and reads paragraph *roles* off content:
`read_signature_roles`.

Run: uv run python -u scripts/unsaturated_surface.py
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

from symbolic_ai_core.world import Quantity
from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood.flow import solve
from symbolic_ai_generators.flood.read_surface import (read_lexical,
                                                       read_signature,
                                                       read_signature_roles,
                                                       read_surface)
from symbolic_ai_generators.flood.surface import render_observation
from symbolic_ai_generators.flood.unsaturate import unsaturate

OUT = Path("runs/unsaturated_surface.json")
N = 60

SURFACES = (
    ("as published", dict(drop_headings=False, shuffle=False)),
    ("no headings", dict(drop_headings=True, shuffle=False)),
    ("shuffled only", dict(drop_headings=False, shuffle=True)),
    ("unsaturated", dict(drop_headings=True, shuffle=True)),
)

READERS = (
    ("signature/index", read_signature),
    ("signature/roles", read_signature_roles),
    ("rules", read_surface),
    ("lexical", read_lexical),
)


def claim_set(world) -> set:
    out = set()
    for c in world.claims:
        v = c.roles.get("value")
        val = round(v.value, 2) if isinstance(v, Quantity) else None
        out.add((c.predicate, tuple(sorted(c.entities())), val))
    return out


def main() -> None:
    cases = [generate(s) for s in range(N)]
    truth = [solve(c.world)[0] for c in cases]
    obs = [render_observation(c) for c in cases]
    nonempty = [i for i, t in enumerate(truth) if t]
    print(f"{N} cases, {len(nonempty)} with a non-empty answer\n")

    rows = {}
    hdr = (f"{'surface':<15} {'reader':<17} {'acc':>7} {'acc|ne':>8} "
           f"{'claim P':>8} {'claim R':>8}")
    print(hdr)
    print("-" * len(hdr))
    for sname, kw in SURFACES:
        texts = [unsaturate(o, **kw).text for o in obs]
        for rname, fn in READERS:
            ok, ok_ne, precs, recs = [], [], [], []
            for i, (case, t) in enumerate(zip(cases, truth)):
                want = claim_set(case.world)
                try:
                    world = fn(texts[i])
                    got = claim_set(world)
                    ans = solve(world)[0]
                except Exception:
                    got, ans = set(), ()
                precs.append(len(got & want) / len(got) if got else 0.0)
                recs.append(len(got & want) / len(want) if want else 0.0)
                ok.append(ans == t)
                if i in nonempty:
                    ok_ne.append(ans == t)
            rows[(sname, rname)] = {
                "acc": statistics.mean(ok),
                "acc_nonempty": statistics.mean(ok_ne),
                "claim_precision": statistics.mean(precs),
                "claim_recall": statistics.mean(recs)}
            r = rows[(sname, rname)]
            print(f"{sname:<15} {rname:<17} {r['acc']:>7.3f} "
                  f"{r['acc_nonempty']:>8.3f} {r['claim_precision']:>8.3f} "
                  f"{r['claim_recall']:>8.3f}", flush=True)
        print()

    base = rows[("as published", "signature/index")]["acc_nonempty"]
    idx = rows[("unsaturated", "signature/index")]["acc_nonempty"]
    rol = rows[("unsaturated", "signature/roles")]["acc_nonempty"]
    print(f"-> the published headline is {base:.3f}. Taking the template away "
          f"leaves the SAME reader\n   at {idx:.3f}: {base - idx:+.3f}, which is "
          f"how much of it was the harness.")
    print(f"   Reading paragraph ROLES from content instead of position "
          f"recovers {rol:.3f}\n   on the same unsaturated surface, consulting "
          f"no content word.")
    if rol >= base - 0.02:
        print(f"   Position was a CRUTCH, not a source of signal: the headline "
              f"survives without it.")
    elif rol > idx + 0.1:
        print(f"   Position was PARTLY real. The residual {base - rol:.3f} is "
              f"reader loss the\n   published table was hiding.")
    else:
        print(f"   Paragraph co-occurrence does NOT replace position; the "
              f"grouping itself carried it.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {"n": N, "n_nonempty": len(nonempty),
         "rows": {f"{s}|{r}": v for (s, r), v in rows.items()}}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
