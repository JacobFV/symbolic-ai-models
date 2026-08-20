"""Where the sentence sits in the document — the one feature the classifier lacks.

`parent` and `founder` are both classifier-bound (0.351 and 0.376) with every
other factor above 0.73, and the four representation families tried on `parent`
moved it by at most seven articles. All four described the sentence's *contents*.
None described **where the sentence is**.

The prior exists and is modest: on 2,502 intros the chance a sentence states the
parent falls **0.156 → 0.079** from the first sentence to the sixth and beyond,
a 2.0x range. A Wikipedia intro front-loads its defining facts, and the classifier
has never been told which sentence it is looking at.

Predicted before running: **+0.005 to +0.015** on both relations. A 2x prior is
real but shallow, and the classifier already has features that correlate with
position (the first sentence has a distinctive shape). If it lands above +0.02 the
prior was carrying more than the raw distribution suggests; if it lands at zero,
position is already implicit in the n-grams.

Run: uv run python -u scripts/sentence_position.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from symbolic_ai_core.reader.learned import LearnedSpanReader, PhraseMentions
from symbolic_ai_core.world import EntityRef

import scripts.real_text_reader as R
from scripts.induced_aliases import induce_aliases
from scripts.multi_relation_world import norm
from scripts.supervise_through_proposer import supervise_via

CORPUS = Path("data/artifacts/wikipedia_parents_closed.jsonl")
RELS = Path("data/artifacts/company_relations_scale_v2.jsonl")
OUT = Path("runs/sentence_position.json")
FOLDS = 4
RELATIONS = ("parent", "founder")


def position_features(u, ments):
    """Index, bucket, first/last, and depth as a fraction of the document."""
    base = list(R.frame_features(u, ments))
    i = u.index
    n = max(1, (u.doc_text.count(". ") + 1) if u.doc_text else 1)
    base += [f"pos={min(i, 5)}", f"pos.first={int(i == 0)}",
             f"pos.early={int(i <= 1)}",
             f"pos.frac={min(int(4 * i / n), 3)}"]
    return base


def main() -> None:
    R.PARENTS, R.RELATIONS = CORPUS, RELS
    docs = R.corpus()
    rel = {json.loads(x)["qid"]: json.loads(x)
           for x in RELS.read_text().splitlines() if x.strip()}
    for d in docs:
        for r_ in RELATIONS:
            if r_ != "parent":
                d[r_] = rel.get(d["qid"], {}).get(r_) or []
    R.RELS = RELATIONS
    print(f"{len(docs)} articles\n")
    print(f"    {'relation':<12}{'arm':<14}{'coverage':>10}{'correct':>9}"
          f"{'precision':>11}{'k/n':>12}")

    out = {}
    for relation in RELATIONS:
        base_k = None
        for arm in ("baseline", "+ position"):
            ok = ans = n = 0
            for fold in range(FOLDS):
                te = [d for i, d in enumerate(docs) if i % FOLDS == fold]
                tr = [d for i, d in enumerate(docs) if i % FOLDS != fold]
                fillers = [v for d in tr for v in (d.get(relation) or [])]
                prop = PhraseMentions.induce(fillers, alias_heads=True)
                al = induce_aliases(tr, relation)
                if al:
                    prop.aliases = {**prop.aliases, **al}
                reader = LearnedSpanReader(
                    mentions=prop,
                    extra_features=(R.frame_features if arm == "baseline"
                                    else position_features),
                    extra_role_features=R.role_frame_features).fit(
                    [supervise_via(d, prop, RELATIONS) for d in tr])
                for d in te:
                    gold = [norm(x) for x in (d.get(relation) or [])]
                    if not gold:
                        continue
                    n += 1
                    res = reader.run(d["intro"], query=d.get("title", ""))
                    best = None
                    for i, c in enumerate(res.claims):
                        v = c.roles.get("value")
                        if c.predicate == relation and isinstance(v, EntityRef):
                            if best is None or res.confidence_of(i) > best[0]:
                                best = (res.confidence_of(i), v.id)
                    if best:
                        ans += 1
                        ok += norm(best[1]) in gold
            delta = "" if base_k is None else f"   {ok - base_k:+d}"
            if base_k is None:
                base_k = ok
            print(f"    {relation:<12}{arm:<14}{ans / n:10.3f}{ok / n:9.3f}"
                  f"{ok / max(1, ans):11.3f}{f'{ok}/{n}':>12}{delta}")
            out[f"{relation}:{arm}"] = {"coverage": ans / n, "correct": ok / n,
                                        "precision": ok / max(1, ans),
                                        "k": ok, "n": n}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
