"""Where the reading loss actually is, with the proposer measured rather than assumed.

Every decomposition in this session was **ceiling x classifier x ranker**. The
phrase-proposer finding showed there is a fourth factor nobody had measured: a
candidate the proposer cannot produce is an answer the reader cannot give, and on
`industry` that factor was **zero** while the other three looked ordinary.

This measures all four, on the same articles, for both proposers:

    containment   the gold string appears somewhere in the article
    proposal      given it appears, it is PROPOSED as a candidate
    classifier    given a sentence containing it, that sentence is labelled
    ranker        given the sentence is labelled, the right candidate is chosen

Their product should land near the measured end-to-end rate. Where it does not,
the gap is document-level aggregation — several sentences get a vote and the
best-believed claim wins, which can recover what any single sentence loses.

Predicted before running: for `parent` under `CapitalisedMentions`, **proposal is
high** (company names are capitalised, so ~0.8–0.9) and therefore is *not* the
binding factor — which is what the vocabulary-prior finding implies and this would
confirm from the other side. For `industry` it is near zero under capitalised runs
and is the entire story. The binding factor for `parent` should remain the
classifier.

Run: uv run python -u scripts/four_factor_decomposition.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from symbolic_ai_core.reader.learned import (CapitalisedMentions,
                                             LearnedSpanReader, PhraseMentions,
                                             _units)
from symbolic_ai_core.world import EntityRef

import scripts.real_text_reader as R
from scripts.multi_relation_world import norm

CORPUS = Path("data/artifacts/wikipedia_parents_closed.jsonl")
RELS = Path("data/artifacts/company_relations_scale_v2.jsonl")
OUT = Path("runs/four_factor_decomposition.json")
FOLDS = 4
#: All five relations with gold on the same 2,502 articles. Four rows established
#: that the product reproduces the rate; ten test whether it generalises, which is
#: the limit that note names for itself.
RELATIONS = ("parent", "country", "headquarters", "founder", "industry")


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
    print(f"{len(docs)} articles")

    out = {}
    for relation in RELATIONS:
        print(f"\n=== {relation}")
        print(f"    {'proposer':<22}{'contain':>9}{'propose':>9}{'clf':>7}"
              f"{'rank':>7}{'product':>9}{'measured':>10}")
        for name in ("CapitalisedMentions", "PhraseMentions"):
            c_n = c_k = p_n = p_k = f_n = f_k = r_n = r_k = 0
            ok = n = 0
            for fold in range(FOLDS):
                te = [d for i, d in enumerate(docs) if i % FOLDS == fold]
                tr = [d for i, d in enumerate(docs) if i % FOLDS != fold]
                prop = (CapitalisedMentions() if name == "CapitalisedMentions"
                        else PhraseMentions.induce(
                            [v for d in tr for v in (d.get(relation) or [])]))
                reader = LearnedSpanReader(
                    mentions=prop, extra_features=R.frame_features,
                    extra_role_features=R.role_frame_features).fit(
                    [R.supervise_distant(d) for d in tr])
                for d in te:
                    gold = [x for x in (d.get(relation) or []) if x]
                    if not gold:
                        continue
                    n += 1
                    units = _units(d["intro"])
                    # 1. containment
                    c_n += 1
                    hits = [(u, g) for u in units for g in gold if g in u.text]
                    c_k += bool(hits)
                    if not hits:
                        continue
                    # 2. proposal, given containment
                    p_n += 1
                    proposed = [(u, g) for u, g in hits
                                if any(m.text == g for m in prop.find(u))]
                    p_k += bool(proposed)
                    if not proposed:
                        continue
                    # 3. classifier, given a proposed sentence exists
                    f_n += 1
                    labelled = []
                    for u, g in proposed:
                        u.query = d.get("title", "")
                        pred, _ = reader.clf.predict(reader.features(u))
                        if pred == relation:
                            labelled.append((u, g))
                    f_k += bool(labelled)
                    if not labelled:
                        continue
                    # 4. ranker, given a labelled sentence
                    r_n += 1
                    picked = False
                    for u, g in labelled:
                        roles, _, _ = reader._fill(
                            u, relation, [], [m.text for m in prop.find(u)])
                        v = roles.get("value")
                        picked = picked or (isinstance(v, EntityRef)
                                            and v.id == g)
                    r_k += picked

                    res = reader.run(d["intro"], query=d.get("title", ""))
                    best = None
                    for i, c in enumerate(res.claims):
                        v = c.roles.get("value")
                        if c.predicate == relation and isinstance(v, EntityRef):
                            if best is None or res.confidence_of(i) > best[0]:
                                best = (res.confidence_of(i), v.id)
                    ok += bool(best) and norm(best[1]) in [norm(x) for x in gold]

            fac = [c_k / max(1, c_n), p_k / max(1, p_n),
                   f_k / max(1, f_n), r_k / max(1, r_n)]
            prod = fac[0] * fac[1] * fac[2] * fac[3]
            print(f"    {name:<22}{fac[0]:9.3f}{fac[1]:9.3f}{fac[2]:7.3f}"
                  f"{fac[3]:7.3f}{prod:9.3f}{ok / max(1, n):10.3f}")
            out[f"{relation}:{name}"] = {
                "containment": fac[0], "proposal": fac[1], "classifier": fac[2],
                "ranker": fac[3], "product": prod, "measured": ok / max(1, n),
                "n": n}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
