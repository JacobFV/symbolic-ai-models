"""What the learned reader is actually doing: two controls, one of which must fail.

`scripts/learned_reader.py` reports 1.000 claim F1 and 1.000 end-to-end on all
three domains, above every hand-written reader. A number like that is the point
at which this repo has historically been wrong, so before it goes anywhere:

**Control 1 -- renaming.** Every entity in the held-out documents is renamed to a
form the reader has never seen (`region_3` -> `zone_512`), consistently in the
text, the world and the case. The reader's induced lexicon has **9 memorised
forms and no productive shapes**, so the prediction is a collapse to near zero:
the reader learned the vocabulary, not the language. If F1 survives renaming,
the prediction is wrong and the lexicon is doing more than it looks like.

**Control 2 -- unseen phrasings.** Train on 2 phrasing variants per claim kind
and test on 4, so half the test sentences are worded in a way the fit never saw.
Prediction: a partial collapse, 0.5-0.8, because the classifier keeps its
signature features (how many entities, numbers and dates) when its n-grams stop
firing -- which is precisely the hand readers' entire basis, reached as a
fallback rather than as a design.

**Arm 3 -- renaming in training.** Train on documents whose entities are renamed
per document, so the shape `a_9` appears with hundreds of distinct fillers and
becomes *productive*. Prediction: control 1 now passes at close to its unrenamed
value, because nothing else about the reader keys on the identity of a name. If
that holds, the cost of identity generalisation is one augmentation and the
result is real; if it does not, something else is memorising and the 1.000 is
not what it appears to be.

The third arm is the one that decides whether the headline stands.

Run: uv run python -u scripts/reader_survives.py
"""

from __future__ import annotations

import json
import random
import re
import statistics
from dataclasses import fields, is_dataclass, replace
from pathlib import Path

from symbolic_ai_core.reader.learned import LearnedSpanReader, supervise
from symbolic_ai_core.world import Claim, Entity, EntityRef, WorldSnapshot

from symbolic_ai_generators import flood, scheduling, solvency
from symbolic_ai_generators.flood.flow import solve as flood_solve
from symbolic_ai_generators.flood.surface import render_observation as flood_obs
from symbolic_ai_generators.scheduling.surface import (
    render_observation as sched_obs)
from symbolic_ai_generators.solvency.surface import (
    render_observation as solv_obs)

from scripts.learned_reader import (auc, canonical, induce_schema, key, prf,
                                    world_from_claims, _sched_answer)

OUT = Path("runs/reader_survives.json")
N_TRAIN = 400
N_TEST = 60

#: Name stems the corpora do not use, so a renamed entity is genuinely unseen.
STEMS = ("zone", "lorry", "unit", "holdco", "plant", "task", "site", "rig")


# ------------------------------------------------------------------ renaming
def _ids(world: WorldSnapshot) -> list[str]:
    out = {v.id for c in world.claims for v in c.roles.values()
           if isinstance(v, EntityRef)}
    return sorted(out | set(world.entities))


def mapping_for(world: WorldSnapshot, rng: random.Random) -> dict[str, str]:
    """A fresh name per entity, with a stem the corpus never uses.

    The number is drawn high so that even the *shape* of the index differs from
    training, and the stem is drawn per world so two documents do not agree on
    what `zone_512` is -- which is the point: nothing about the reader may be
    allowed to key on the identity of a name.
    """
    out = {}
    for i, e in enumerate(_ids(world)):
        out[e] = f"{rng.choice(STEMS)}_{rng.randrange(200, 999)}{i}"
    return out


def _remap(obj, m: dict[str, str]):
    if isinstance(obj, str):
        return m.get(obj, obj)
    if isinstance(obj, EntityRef):
        return EntityRef(m.get(obj.id, obj.id))
    if isinstance(obj, Entity):
        return Entity(m.get(obj.id, obj.id), types=obj.types,
                      facets={k: _remap_facet(f, m) for k, f in
                              obj.facets.items()})
    if isinstance(obj, Claim):
        return replace(obj, roles={k: _remap(v, m) for k, v in
                                   obj.roles.items()})
    if isinstance(obj, WorldSnapshot):
        return WorldSnapshot(
            entities={m.get(k, k): _remap(v, m) for k, v in
                      obj.entities.items()},
            claims=tuple(_remap(c, m) for c in obj.claims))
    if isinstance(obj, dict):
        return {k: _remap(v, m) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set, frozenset)):
        vals = [_remap(v, m) for v in obj]
        return type(obj)(vals) if not isinstance(obj, tuple) else tuple(vals)
    if is_dataclass(obj):
        return replace(obj, **{f.name: _remap(getattr(obj, f.name), m)
                               for f in fields(obj)})
    return obj


def _remap_facet(f, m):
    return type(f)(f.profile, {k: _remap(v, m) for k, v in f.values.items()})


def rename_text(text: str, m: dict[str, str]) -> str:
    """Longest-first, on word boundaries.

    `region_1` is a prefix of `region_10`; replacing shortest-first renames half
    of `region_10` and leaves a token that is in neither vocabulary.
    """
    for k in sorted(m, key=len, reverse=True):
        text = re.sub(rf"\b{re.escape(k)}\b", m[k], text)
    return text


# ------------------------------------------------------------------ domains
def domains():
    return {
        "solvency": dict(
            gen=solvency.generate,
            obs=lambda c: solv_obs(c, variants=4, hard_distractors=True),
            obs_k=lambda c, v: solv_obs(c, variants=v, hard_distractors=True),
            answer=_solv_answer,
        ),
        "scheduling": dict(
            gen=scheduling.generate,
            obs=lambda c: sched_obs(c, variants=4, hard_distractors=True),
            obs_k=lambda c, v: sched_obs(c, variants=v, hard_distractors=True),
            answer=lambda w, c: _sched_answer(w),
        ),
        "flood": dict(
            gen=flood.generate,
            obs=lambda c: flood_obs(c, variants=4, hard_distractors=True),
            obs_k=lambda c, v: flood_obs(c, variants=v, hard_distractors=True),
            answer=lambda w, c: flood_solve(w)[0],
        ),
    }


def _solv_answer(world, case):
    from symbolic_ai_core.world import Quantity
    from symbolic_ai_generators.solvency.read_surface import (decide_reading,
                                                              read_signature)
    members, filings = set(), []
    for c in world.claims:
        if c.predicate == "owns" and isinstance(c.roles.get("child"), EntityRef):
            members.add(c.roles["child"].id)
        elif c.predicate == "revenue":
            of, v = c.roles.get("of"), c.roles.get("value")
            if isinstance(of, EntityRef) and isinstance(v, Quantity) \
                    and c.transaction_time.start:
                filings.append((of.id, float(v.value), c.transaction_time.start))
    members.add(case.group)
    r = read_signature("")
    r.members, r.filings = members, filings
    r.threshold, r.decision_date = case.threshold, case.decision_date
    return decide_reading(r)


# ------------------------------------------------------------------ arms
def build(dom, seeds, *, variants=None, rename=False, rng_seed=0):
    """Cases, observations and (optionally) a fresh identity vocabulary."""
    out = []
    rng = random.Random(rng_seed)
    for s in seeds:
        c = dom["gen"](s)
        if rename:
            # Rename the CASE and re-render, rather than renaming the rendered
            # text. The spans are character offsets into the document, so a
            # substitution that changes any name's length silently shifts every
            # alignment after it -- which turns the control into a measurement
            # of nothing and reads as a catastrophic reader failure. Cost: one
            # run of this script.
            c = _remap(c, mapping_for(c.world, rng))
        o = dom["obs"](c) if variants is None else dom["obs_k"](c, variants)
        out.append((c, o, o.text))
    return out


def fit_on(data):
    docs = [supervise(text, o.spans, c.world.claims) for c, o, text in data]
    return LearnedSpanReader().fit(docs), docs


def score(reader, dom, data, schema) -> dict:
    f1s, oks, rec = [], [], []
    for c, o, text in data:
        gold = {key(x) for x in canonical(c.world.claims, text)}
        res = reader.run(text)
        got = {key(x) for x in canonical(res.delta().claims, text)}
        p, r, f = prf(gold, got)
        f1s.append(f)
        rec.append(r)
        try:
            want = dom["answer"](c.world, c)
            got_a = dom["answer"](world_from_claims(res.delta().claims, schema), c)
        except Exception:
            want, got_a = object(), None
        oks.append(want == got_a)
    pos = [f for f, k in zip(f1s, oks) if k]
    neg = [f for f, k in zip(f1s, oks) if not k]
    return {"f1": statistics.mean(f1s), "recall": statistics.mean(rec),
            "acc": statistics.mean(oks), "auc": auc(pos, neg),
            "n_correct": sum(oks), "n": len(oks)}


def main() -> None:
    results = {}
    for name, dom in domains().items():
        print(f"\n=== {name}")
        train = build(dom, range(N_TRAIN))
        test = build(dom, range(1_000_000, 1_000_000 + N_TEST))
        test_renamed = build(dom, range(1_000_000, 1_000_000 + N_TEST),
                             rename=True, rng_seed=7)
        schema = induce_schema([(c, o) for c, o, _ in train])

        base, _ = fit_on(train)
        print(f"    lexicon: {len(base.lex.forms)} forms, "
              f"productive {sorted(base.lex.productive)}")
        rows = {"in_distribution": score(base, dom, test, schema),
                "renamed": score(base, dom, test_renamed, schema)}

        train2 = build(dom, range(N_TRAIN), variants=2)
        few, _ = fit_on(train2)
        rows["unseen_phrasings"] = score(few, dom, test, schema)

        train_aug = build(dom, range(N_TRAIN), rename=True, rng_seed=1)
        aug, _ = fit_on(train_aug)
        print(f"    augmented lexicon: {len(aug.lex.forms)} forms, "
              f"productive {sorted(aug.lex.productive)}")
        rows["renamed_after_augmenting"] = score(aug, dom, test_renamed, schema)
        rows["in_distribution_after_augmenting"] = score(aug, dom, test, schema)

        # Augmenting ALONE costs the names that do not follow a productive
        # shape: solvency's parent is called `group`, with no number, so once
        # every training document renames it there is nothing left to memorise
        # and it stops being an entity at all. The union is what a real fit
        # would use, and it is the arm that has to hold both ends.
        both, _ = fit_on(train + train_aug)
        print(f"    union lexicon: {len(both.lex.forms)} forms, "
              f"productive {sorted(both.lex.productive)}")
        rows["renamed_union_fit"] = score(both, dom, test_renamed, schema)
        rows["in_distribution_union_fit"] = score(both, dom, test, schema)

        print(f"    {'arm':<34} {'F1':>7} {'acc':>7} {'AUC(F1->ok)':>12}")
        for k, v in rows.items():
            a = f"{v['auc']:.3f}" if v["auc"] == v["auc"] else "  --"
            print(f"    {k:<34} {v['f1']:7.3f} {v['acc']:7.3f} {a:>12}")
        results[name] = rows

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
