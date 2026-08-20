"""Does the reading arm survive a change of domain?

Every number in the reading arm comes from **company intros**: seven relations,
one register, one corpus, one gold source. The arm's three central claims are
stated generally --

    1. reading factors as containment x proposal x classifier x ranker, and the
       product reproduces the measured rate;
    2. the classifier is the binding factor;
    3. `containment < floor` proves a relation impossible before it is fitted --

and none of them has ever been asked a question outside the corpus that produced
them. A law fitted on one genre and quoted as a law is exactly the failure this
repo has recorded five times.

So: the same measurement, unchanged, on biographies. Different register (a life,
not a corporate description), different relation family (born where, did what,
worked for whom, studied where), same annotation source, so the comparison is
about the text rather than about the labels.

The predictions are registered in `notes/autonomy/predictions.jsonl` before the
fetch finished, and the interesting outcomes are the ones that break them:
`occupation` is predicted to read 0.000 under a capitalised proposer for exactly
the reason `industry` did, and the classifier is predicted to bind again.

Run: uv run python -u scripts/people_decomposition.py
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

CORPUS = Path("data/artifacts/people_relations.jsonl")
OUT = Path("runs/people_decomposition.json")
FOLDS = 4
RELATIONS = ("birthplace", "occupation", "employer", "educated_at")


#: A second fetch added 1,970 more biographies. Both files are read when the
#: extra one exists, because n was the binding constraint on every interval in
#: the router arm and the fetch was run to relieve it.
EXTRA = Path("data/artifacts/people_relations_more.jsonl")


def corpus() -> list[dict]:
    docs = []
    text = CORPUS.read_text()
    if EXTRA.exists():
        text += "\n" + EXTRA.read_text()
    for line in text.splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        d = {"qid": r["qid"], "title": r["title"], "intro": r["intro"]}
        for rel in RELATIONS:
            d[rel] = list(r.get(rel) or [])
        docs.append(d)
    seen, out = set(), []
    for d in docs:
        if d["qid"] not in seen:
            seen.add(d["qid"])
            out.append(d)
    return out


def main() -> None:
    R.RELS = RELATIONS
    docs = corpus()
    print(f"{len(docs)} biographies")
    for rel in RELATIONS:
        n = sum(1 for d in docs if d[rel])
        print(f"  {rel:<12} gold on {n:5d}  ({n / len(docs):.3f})")

    out = {}
    for relation in RELATIONS:
        print(f"\n=== {relation}")
        print(f"    {'proposer':<22}{'contain':>9}{'propose':>9}{'clf':>7}"
              f"{'rank':>7}{'product':>9}{'measured':>10}{'n':>7}")
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
                    c_n += 1
                    hits = [(u, g) for u in units for g in gold if g in u.text]
                    c_k += bool(hits)
                    if not hits:
                        continue
                    p_n += 1
                    proposed = [(u, g) for u, g in hits
                                if any(m.text == g for m in prop.find(u))]
                    p_k += bool(proposed)
                    if not proposed:
                        continue
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
                  f"{fac[3]:7.3f}{prod:9.3f}{ok / max(1, n):10.3f}{n:7d}")
            out[f"{relation}:{name}"] = {
                "containment": fac[0], "proposal": fac[1], "classifier": fac[2],
                "ranker": fac[3], "product": prod, "measured": ok / max(1, n),
                "n": n}

    print("\n--- the three claims, off-corpus")
    gaps = [abs(v["product"] - v["measured"]) for v in out.values()]
    print(f"1. product vs measured: max gap {max(gaps):.3f}, "
          f"mean {sum(gaps) / len(gaps):.3f}  "
          f"(company arm: max 0.019)")
    binds = 0
    for relation in RELATIONS:
        v = out[f"{relation}:PhraseMentions"]
        f = {k: v[k] for k in ("containment", "proposal", "classifier",
                               "ranker")}
        lo = min(f, key=f.get)
        binds += lo == "classifier"
        print(f"2. {relation:<12} binding factor {lo:<12} at {f[lo]:.3f}")
    print(f"   classifier binds in {binds}/{len(RELATIONS)} "
          f"(company arm: 7/7)")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
