"""Does a thesaurus close the gap the adversarial test measured?

`read_content_roles` reaches 1.000 with a hand-declared anchor vocabulary and
0.618 -- exactly its no-vocabulary floor -- against phrasings written to evade
those words. The 0.382 between them is the measured value of having the right
word, and that is what justifies reaching for a lexical resource.

The expansion procedure is fixed **before** looking at how it scores, and is
written down in ``notes/autonomy/predictions.jsonl``: every synset of every
declared anchor, plus direct hyponyms, direct hypernyms and derivationally
related forms. No hand curation.

Two numbers matter, and the second more:

- **adversarial** -- does the resource recover anything?
- **original** -- does it *misfire*? The tight vocabulary provably never fired on
  a sentence it was not written for, which is why its failure mode is silence.
  A large expanded set can lose that property, and a drop here is worse than no
  recovery there.

Run: uv run --with nltk python -u scripts/wordnet_expansion.py
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood import surface as S
from symbolic_ai_generators.flood.flow import solve
from symbolic_ai_generators.flood.read_surface import (ROLE_ANCHORS,
                                                       read_content_roles)
from symbolic_ai_generators.flood.unsaturate import interleave, unsaturate

OUT = Path("runs/wordnet_expansion.json")
N = 60

from scripts.adversarial_variants import ADVERSARIAL  # noqa: E402


def expand(anchors: dict) -> dict:
    """Synsets, direct hyponyms, direct hypernyms, derivational forms."""
    from nltk.corpus import wordnet as wn

    out: dict[str, tuple] = {}
    for role, words in anchors.items():
        got: set[str] = set(words)
        for w in words:
            for syn in wn.synsets(w):
                related = [syn] + syn.hyponyms() + syn.hypernyms()
                for s in related:
                    for lem in s.lemmas():
                        got.add(lem.name())
                        for d in lem.derivationally_related_forms():
                            got.add(d.name())
        toks = set()
        for g in got:
            for piece in g.lower().split("_"):
                if len(piece) >= 3:
                    toks.add(piece)
        out[role] = tuple(sorted(toks))
    return out


def score(anchors: dict, interleaved: bool, V: int = 4) -> float:
    ok = []
    for s in range(N):
        case = generate(s)
        want = solve(case.world)[0]
        if not want:
            continue
        obs = S.render_observation(case, variants=V)
        flat = unsaturate(obs, drop_headings=True, shuffle=False)
        text = interleave(flat).text if interleaved else unsaturate(obs).text
        try:
            got = solve(read_content_roles(text, anchors=anchors))[0]
        except Exception:
            got = ()
        ok.append(got == want)
    return statistics.mean(ok)


def main() -> None:
    tight = dict(ROLE_ANCHORS)
    wide = expand(tight)
    empty = {k: () for k in tight}
    print("vocabulary sizes after expansion:")
    for role in tight:
        print(f"  {role:<9} {len(tight[role]):>3} -> {len(wide[role]):>5} tokens")
    overlap = set(wide["depot"]) & set(wide["flooded"]) & set(wide["needs"])
    print(f"  tokens now shared by ALL THREE roles: {len(overlap)}")

    original = dict(S._VARIANTS)
    rows = {}
    try:
        for label, variants in (("original phrasings", None),
                                ("adversarial phrasings", ADVERSARIAL)):
            S._VARIANTS = dict(original)
            if variants:
                for role, forms in variants.items():
                    S._VARIANTS[role] = forms
            rows[label] = {
                name: {"grouped": score(a, False), "interleaved": score(a, True)}
                for name, a in (("empty", empty), ("tight", tight),
                                ("wordnet", wide))}
    finally:
        S._VARIANTS = original

    print(f"\n{'phrasings':<24} {'vocabulary':<10} {'grouped':>9} "
          f"{'interleaved':>12}")
    print("-" * 60)
    for label, by_vocab in rows.items():
        for name in ("empty", "tight", "wordnet"):
            r = by_vocab[name]
            print(f"{label:<24} {name:<10} {r['grouped']:>9.3f} "
                  f"{r['interleaved']:>12.3f}")
        print()

    adv = rows["adversarial phrasings"]
    orig = rows["original phrasings"]
    recovered = adv["wordnet"]["interleaved"] - adv["empty"]["interleaved"]
    misfire = orig["tight"]["interleaved"] - orig["wordnet"]["interleaved"]
    print(f"-> recovery on adversarial phrasings: "
          f"{adv['empty']['interleaved']:.3f} -> "
          f"{adv['wordnet']['interleaved']:.3f}  ({recovered:+.3f} of the "
          f"0.382 available)")
    print(f"   cost on the original phrasings:    "
          f"{orig['tight']['interleaved']:.3f} -> "
          f"{orig['wordnet']['interleaved']:.3f}  ({-misfire:+.3f})")
    if misfire > 0.05:
        print(f"\n   THE EXPANSION MISFIRES. It loses {misfire:.3f} on wording "
              f"the tight vocabulary\n   handled perfectly, because a token "
              f"shared by two roles makes _anchor_role\n   ambiguous and the "
              f"sentence falls through. A bigger lexicon is not a better one.")
    if recovered < 0.15:
        print(f"\n   AND IT RECOVERS ALMOST NOTHING ({recovered:+.3f}). The gap "
              f"is not lexical. The\n   adversarial phrasings name the roles by "
              f"CONSEQUENCE -- flooding as 'nothing gets\n   through', a depot "
              f"as where the fleet sleeps -- and a thesaurus bridges\n   "
              f"flood->inundate, not flood->nothing gets through. What is "
              f"needed is knowledge of\n   what a role DOES, which is closer to "
              f"the kernel's own semantics than to a\n   dictionary.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {"n": N, "sizes": {k: [len(tight[k]), len(wide[k])] for k in tight},
         "rows": rows}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
