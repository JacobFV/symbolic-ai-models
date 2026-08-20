"""Aliases induced by label association, not by morphology.

Head-stripping turns `automotive industry` into the alias `automotive` and pays
3.9x on that relation. It cannot touch `country`, whose derivations are
suppletive — `French`/`France`, `Dutch`/`Netherlands`, `British`/`United
Kingdom` — and which was measured to be stated **adjectivally-only in 29.3% of
articles**, fully explaining why a hand reader with a nationality map beats a
perfect classifier there.

Morphology cannot find those. **Label association can.** A word that appears in
articles whose gold value is `Japan`, and rarely elsewhere, is an alias for
`Japan` whatever its spelling. That is the same PMI machinery the label-aware
buckets used, applied at the level of a *value* rather than a class, and it needs
nothing external.

    alias(v) = words w with P(w | gold = v) high and P(w) low,
               requiring a minimum count so a hapax cannot become an alias

Induced per fold from training articles only, then used both to propose (reporting
the canonical value) and to supervise, since the previous finding showed the two
must move together.

Predicted before running: **`country` gains the most** — it is the relation with a
large measured alias gap that morphology cannot reach, and 29.3% is a lot of
headroom. `industry` should gain a little on top of head-stripping, and `parent`,
`headquarters` and `founder` should be near-flat, because a company or a person is
not usually referred to by a derived word.

Run: uv run python -u scripts/induced_aliases.py
"""

from __future__ import annotations

import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from symbolic_ai_core.reader.learned import (LearnedSpanReader, PhraseMentions,
                                             _units)
from symbolic_ai_core.world import EntityRef

import scripts.real_text_reader as R
from scripts.multi_relation_world import norm
from scripts.supervise_through_proposer import supervise_via

CORPUS = Path("data/artifacts/wikipedia_parents_closed.jsonl")
RELS = Path("data/artifacts/company_relations_scale_v2.jsonl")
OUT = Path("runs/induced_aliases.json")
FOLDS = 4
RELATIONS = ("parent", "country", "headquarters", "founder", "industry")
MIN_COUNT = 8
MIN_LIFT = 6.0
_TOK = re.compile(r"[a-z][a-z-]{3,}")


def induce_aliases(train_docs, relation: str) -> dict[str, str]:
    """A word strongly associated with one gold value, and rare elsewhere."""
    per_value: dict[str, Counter] = defaultdict(Counter)
    overall: Counter = Counter()
    n_with: Counter = Counter()
    docs_n = 0
    for d in train_docs:
        gold = [g for g in (d.get(relation) or []) if g]
        if not gold:
            continue
        docs_n += 1
        words = set(_TOK.findall(d["intro"].lower()))
        overall.update(words)
        for g in gold:
            n_with[g] += 1
            per_value[g].update(words)
    out: dict[str, str] = {}
    claimed: Counter = Counter()
    for value, counts in per_value.items():
        if n_with[value] < MIN_COUNT:
            continue
        for w, c in counts.items():
            if c < MIN_COUNT or w in value.lower():
                continue
            p_in = c / n_with[value]
            p_all = overall[w] / docs_n
            if p_all > 0 and p_in / p_all >= MIN_LIFT:
                # A word that is an alias for two values is an alias for
                # neither; ambiguity here would make the reader guess.
                claimed[w] += 1
                out[w] = value
    return {w: v for w, v in out.items() if claimed[w] == 1}


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
    print(f"    {'relation':<14}{'aliases':>9}{'baseline':>10}{'INDUCED':>9}"
          f"{'delta':>8}   examples")

    out = {}
    for relation in RELATIONS:
        scores = {}
        for arm in ("baseline", "induced"):
            ok = n = 0
            n_alias = 0
            shown = ""
            for fold in range(FOLDS):
                te = [d for i, d in enumerate(docs) if i % FOLDS == fold]
                tr = [d for i, d in enumerate(docs) if i % FOLDS != fold]
                fillers = [v for d in tr for v in (d.get(relation) or [])]
                al = induce_aliases(tr, relation) if arm == "induced" else {}
                if arm == "induced" and not shown and al:
                    n_alias = len(al)
                    shown = ", ".join(f"{w}->{v}" for w, v in
                                      list(al.items())[:3])
                prop = PhraseMentions.induce(fillers, alias_heads=True)
                if al:
                    prop.aliases = {**prop.aliases, **al}
                reader = LearnedSpanReader(
                    mentions=prop, extra_features=R.frame_features,
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
                    ok += bool(best) and norm(best[1]) in gold
            scores[arm] = ok / n
        d_ = scores["induced"] - scores["baseline"]
        print(f"    {relation:<14}{n_alias:9d}{scores['baseline']:10.3f}"
              f"{scores['induced']:9.3f}{d_:+8.3f}   {shown[:44]}")
        out[relation] = {"baseline": scores["baseline"],
                         "induced": scores["induced"], "delta": d_,
                         "n_aliases": n_alias}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
