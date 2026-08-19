"""Paraphrase against interleaving: does any reader survive both?

Two structural crutches have now come off the flood surface. The section
headings turned out to be worth nothing, and paragraph ORDER -- which
`read_signature` consumed through its ``pi ==`` branches -- was replaced by
paragraph CO-OCCURRENCE at no cost. That leaves one template property standing:
**grouping**. This generator puts every road in one paragraph and every flood
report in another, and a real report does not.

`interleave` destroys grouping too, keeping each pronoun glued to its antecedent
so every sentence stays true. Crossed with phrasing variation this is a 2x2, and
the point is that the two readers should fail on **opposite** axes:

- the rules arm matches whole phrasings, so it does not care where a sentence
  sits -- and dies under paraphrase;
- the signature arms read entity types, so they do not care how a sentence is
  worded -- and lean on structure.

If no arm holds both cells, the empty cell is the honest frontier, and directive
19's answer applies: **emit** the ambiguity rather than collapse it. So the
sound enumerating arm is measured alongside, on soundness and decidedness rather
than accuracy.

Run: uv run python -u scripts/interleaved_surface.py
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood.flow import solve
from symbolic_ai_generators.flood.read_surface import (read_lexical,
                                                       read_signature,
                                                       read_signature_roles,
                                                       read_surface,
                                                       signature_worlds,
                                                       VALUE_REGISTRY)
from symbolic_ai_generators.flood.surface import render_observation
from symbolic_ai_generators.flood.unsaturate import interleave, unsaturate

OUT = Path("runs/interleaved_surface.json")
N = 60
VARIANTS = (1, 4)

READERS = (
    ("signature/index", read_signature),
    ("signature/roles", read_signature_roles),
    ("rules", read_surface),
    ("lexical", read_lexical),
)


def surfaces(case):
    """(name, text) for one case, at each level of scramble."""
    obs = render_observation(case)
    flat = unsaturate(obs, drop_headings=True, shuffle=False)
    return (("grouped", unsaturate(obs).text),
            ("interleaved", interleave(flat).text))


def main() -> None:
    cases = [generate(s) for s in range(N)]
    truth = [solve(c.world)[0] for c in cases]
    nonempty = [i for i, t in enumerate(truth) if t]
    print(f"{N} cases, {len(nonempty)} with a non-empty answer\n")

    rows: dict = {}
    hdr = f"{'V':>2} {'surface':<13} {'reader':<17} {'acc|non-empty':>14}"
    print(hdr)
    print("-" * len(hdr))
    for V in VARIANTS:
        texts: dict[str, list[str]] = {"grouped": [], "interleaved": []}
        for c in cases:
            obs = render_observation(c, variants=V)
            flat = unsaturate(obs, drop_headings=True, shuffle=False)
            texts["grouped"].append(unsaturate(obs).text)
            texts["interleaved"].append(interleave(flat).text)
        for sname in ("grouped", "interleaved"):
            for rname, fn in READERS:
                ok = []
                for i in nonempty:
                    try:
                        ans = solve(fn(texts[sname][i]))[0]
                    except Exception:
                        ans = ()
                    ok.append(ans == truth[i])
                rows[(V, sname, rname)] = statistics.mean(ok)
                print(f"{V:>2} {sname:<13} {rname:<17} "
                      f"{statistics.mean(ok):>14.3f}", flush=True)
            print()

    # --- the constructive answer in the cell where collapsing fails
    print("\nemitting instead of collapsing, on the hardest cell "
          "(V=4, interleaved):\n")
    # The ablation ladder, because the registry is DECLARED external knowledge
    # and switching it off is a different arm, not the same one. An earlier run
    # of this passed registry=None and reported 72 worlds as though it were the
    # arm's number; it is the number with the knowledge removed.
    ladder = (("signature only", dict(registry=None, adjacency=False)),
              ("+ value registry", dict(registry=VALUE_REGISTRY,
                                        adjacency=False)),
              ("+ adjacency", dict(registry=VALUE_REGISTRY, adjacency=True)))
    emit: dict = {}
    print(f"  {'arm':<18} {'n':>4} {'sound':>7} {'decided':>8} {'worlds':>8}")
    print("  " + "-" * 48)
    for label, kw in ladder:
        sound = decided = counted = 0
        sizes = []
        for i in nonempty:
            obs = render_observation(cases[i], variants=4)
            flat = unsaturate(obs, drop_headings=True, shuffle=False)
            worlds = signature_worlds(interleave(flat).text,
                                      truth=cases[i].world, **kw)
            if not worlds:
                continue
            counted += 1
            sizes.append(len(worlds))
            answers = {solve(w)[0] for w in worlds}
            sound += truth[i] in answers
            decided += len(answers) == 1
        emit[label] = {"n": counted,
                       "sound": sound / counted if counted else None,
                       "decided": decided / counted if counted else None,
                       "median_worlds": statistics.median(sizes) if sizes
                       else None}
        e = emit[label]
        if counted:
            print(f"  {label:<18} {counted:>4} {e['sound']:>7.3f} "
                  f"{e['decided']:>8.3f} {e['median_worlds']:>8.1f}", flush=True)
        else:
            print(f"  {label:<18} {0:>4} {'--':>7} {'--':>8} {'refused':>8}")

    best_hard = max((rows[(4, 'interleaved', r)], r) for r, _ in READERS)
    print(f"\n-> hardest cell (V=4, interleaved): best collapsing reader is "
          f"{best_hard[1]} at {best_hard[0]:.3f}.")
    if best_hard[0] < 0.1:
        print(f"   NO arm survives both axes. The two mechanisms fail on "
              f"opposite ones -- rules on\n   paraphrase, signature on "
              f"structure -- and this cell is the honest frontier.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {"n": N, "n_nonempty": len(nonempty),
         "rows": {f"V{v}|{s}|{r}": a for (v, s, r), a in rows.items()},
         "emit": emit},
        indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
