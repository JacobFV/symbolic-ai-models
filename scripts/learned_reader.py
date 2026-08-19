"""The first learned reader, against the hand-written ones, on all three domains.

Every reader this repo has is a pattern set someone wrote while looking at the
surface it reads. That answers *can a person write patterns for this* and leaves
the actual question open. `symbolic_ai_core.reader.learned` has no domain lexicon
in it at all: it is given aligned `(sentence, claim)` pairs and induces the
predicate inventory, the names, the role signatures, the units and the temporal
envelope. One implementation, fitted three times.

What is being measured, and what is predicted before it runs
------------------------------------------------------------

1. **Claim F1 on held-out documents**, learned against handcrafted.
   Predicted: solvency highest (two predicates, disjoint shapes), scheduling
   next, flood lowest -- flood is the only surface with pronominal reference, and
   a role stated as *"the same vehicle"* is not in the sentence to be ranked.
   Predicted band 0.85-0.98 for solvency/scheduling, 0.70-0.90 for flood.

2. **End-to-end accuracy through the real kernels**, learned world against
   oracle world against handcrafted reader. Predicted: the learned reader loses
   to the handcrafted one on flood and roughly ties on the other two, because
   the handcrafted readers were written against these exact phrasings and the
   learned one sees 4 variants of each.

3. **Does claim F1 predict end-to-end success?** This is the one that matters.
   On real text, extraction metrics ranked a correct answer ahead of a wrong one
   at AUC 0.506 -- chance -- while critical error mass ranked at 0.946. That was
   measured without a gold world. Here there IS a gold world, so the same
   question can be asked exactly: per document, the F1 of the reading and
   whether the kernel then got the answer right.
   Predicted: AUC(F1 -> correct) well above chance but well below 1.0 -- 0.75 to
   0.90 -- because F1 counts every claim equally and the kernels do not. If it
   comes out near 1.0 the sensitivity-weighted objective has nothing to buy and
   step 6 should be dropped; if it comes out near 0.5 the case for it is as
   strong as it was on real text.

Run: uv run python -u scripts/learned_reader.py
"""

from __future__ import annotations

import json
import re
import statistics
from dataclasses import replace
from pathlib import Path

from collections import Counter, defaultdict

from symbolic_ai_core.reader.learned import LearnedSpanReader, supervise
from symbolic_ai_core.world import (Entity, EntityRef, Facet, Quantity,
                                    WorldSnapshot)

from symbolic_ai_generators import flood, scheduling, solvency
from symbolic_ai_generators.flood.flow import solve as flood_solve
from symbolic_ai_generators.flood.read_surface import read_content_roles
from symbolic_ai_generators.flood.surface import render_observation as flood_obs
from symbolic_ai_generators.scheduling import feasible_by_search
from symbolic_ai_generators.scheduling.read_surface import (
    read_signature as sched_signature)
from symbolic_ai_generators.scheduling.surface import (
    render_observation as sched_obs)
from symbolic_ai_generators.solvency.read_surface import (
    decide_reading, read_signature as solv_signature)
from symbolic_ai_generators.solvency.surface import (
    render_observation as solv_obs)

OUT = Path("runs/learned_reader.json")
N_TRAIN = 400
N_TEST = 60
V = 4


# ---------------------------------------------------------------- schema
def induce_schema(train) -> tuple[dict, dict]:
    """`(predicate, role) -> entity type` and `type -> facet template`.

    A reader recovers **claims**. Which profile an entity carries, and that a
    vehicle declares a `payload` variable for the SMT step, are facts about the
    domain's schema and appear in no sentence -- the hand reader has them
    hard-coded, which is not reading either. They are induced here from the
    training worlds, so the learned arm is given exactly what the hand arm was
    given and the comparison is about the text.

    Facet values that are the entity's own id are re-substituted, so a template
    taken from `region_0` yields `name: region_7` rather than `name: region_0`.
    """
    role_type: dict[tuple[str, str], Counter] = defaultdict(Counter)
    template: dict[tuple[str, ...], tuple[str, dict]] = {}
    for c, _ in train:
        for claim in c.world.claims:
            for r, v in claim.roles.items():
                if isinstance(v, EntityRef):
                    e = c.world.entities.get(v.id)
                    if e is not None:
                        role_type[(claim.predicate, r)][e.types] += 1
        for e in c.world.entities.values():
            template.setdefault(e.types, (e.id, e.facets))
    return ({k: v.most_common(1)[0][0] for k, v in role_type.items()}, template)


def world_from_claims(claims, schema) -> WorldSnapshot:
    role_type, template = schema
    types: dict[str, tuple[str, ...]] = {}
    for c in claims:
        for r, v in c.roles.items():
            if isinstance(v, EntityRef) and (c.predicate, r) in role_type:
                types.setdefault(v.id, role_type[(c.predicate, r)])
    entities = {}
    for eid, ts in types.items():
        src, facets = template.get(ts, (eid, {}))
        entities[eid] = Entity(eid, types=ts, facets={
            k: Facet(f.profile, {kk: (eid if vv == src else vv)
                                 for kk, vv in f.values.items()})
            for k, f in facets.items()})
    return WorldSnapshot(entities=entities, claims=tuple(claims))


# ---------------------------------------------------------------- keys
_WORD = re.compile(r"[A-Za-z][A-Za-z0-9_]*")


def canonical(claims, text: str):
    """Rename entities the document never names, by the company they keep.

    flood's bridges exist in the world and appear in no sentence: the prose says
    *the road bridges the river*, and the id `bridge_4` is the generator's
    private bookkeeping. Any reader must invent a name, so comparing invented
    names to `bridge_4` measures whether the reader guessed the generator's
    numbering -- which the hand-written reader was told and a learned one cannot
    be. Scoring instead compares them **up to renaming of the unnamed**, by
    replacing each such id with a fingerprint of the claims it takes part in and
    the named entities in them. Applied identically to gold and to every arm.
    """
    named = set(_WORD.findall(text))
    ids = {v.id for c in claims for v in c.roles.values()
           if isinstance(v, EntityRef)}
    sub: dict[str, str] = {}
    for e in ids - named:
        sig = []
        for c in claims:
            for r, v in c.roles.items():
                if isinstance(v, EntityRef) and v.id == e:
                    others = tuple(sorted(
                        x.id for x in c.roles.values()
                        if isinstance(x, EntityRef) and x.id in named))
                    sig.append(f"{c.predicate}.{r}:{','.join(others)}")
        sub[e] = "~" + "|".join(sorted(sig))
    if not sub:
        return tuple(claims)
    out = []
    for c in claims:
        roles = {r: (EntityRef(sub.get(v.id, v.id))
                     if isinstance(v, EntityRef) else v)
                 for r, v in c.roles.items()}
        out.append(replace(c, roles=roles))
    return tuple(out)


def key(c) -> tuple:
    """What makes two claims the same claim, for scoring.

    Quantities compare at two decimals -- the domains' own precision -- and the
    transaction time is part of the key wherever the generator sets one, because
    in solvency a figure attached to the wrong date is not a near miss, it is the
    entire task.
    """
    parts = []
    for r in sorted(c.roles):
        v = c.roles[r]
        if isinstance(v, EntityRef):
            parts.append((r, v.id))
        elif isinstance(v, Quantity):
            parts.append((r, round(float(v.value), 2)))
        else:
            parts.append((r, str(v).lower()))
    return (c.predicate, tuple(parts), c.transaction_time.start)


def prf(gold: set, got: set) -> tuple[float, float, float]:
    tp = len(gold & got)
    p = tp / len(got) if got else 0.0
    r = tp / len(gold) if gold else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f


def auc(pos: list[float], neg: list[float]) -> float:
    """P(a correct document scores above an incorrect one), ties at a half."""
    if not pos or not neg:
        return float("nan")
    wins = sum((1.0 if a > b else 0.5 if a == b else 0.0)
               for a in pos for b in neg)
    return wins / (len(pos) * len(neg))


# ---------------------------------------------------------------- domains
def flood_domain():
    def build(seed):
        c = flood.generate(seed)
        o = flood_obs(c, variants=V, hard_distractors=True)
        return c, o

    def answer(world, case):
        return flood_solve(world)[0]

    def truth(case):
        return flood_solve(case.world)[0]

    def hand(text, case):
        return read_content_roles(text)

    return dict(name="flood", build=build, answer=answer, truth=truth,
                hand=hand)


def solvency_domain():
    def build(seed):
        c = solvency.generate(seed)
        o = solv_obs(c, variants=V)
        return c, o

    def answer(world, case):
        """The covenant verdict from a claim set.

        The threshold and the determination date are prose, not claims -- the
        generator does not put them in the world at all -- so they are supplied
        from the case for every arm alike, including the oracle. That isolates
        what is being compared (claim recovery) and it is stated rather than
        buried: a reader that had to find them too would be measured on a
        different task.
        """
        members, filings = set(), []
        for c in world.claims:
            if c.predicate == "owns":
                child = c.roles.get("child")
                if isinstance(child, EntityRef):
                    members.add(child.id)
            elif c.predicate == "revenue":
                of, v = c.roles.get("of"), c.roles.get("value")
                if isinstance(of, EntityRef) and isinstance(v, Quantity) \
                        and c.transaction_time.start:
                    filings.append((of.id, float(v.value),
                                    c.transaction_time.start))
        members.add(case.group)
        r = solv_signature("")
        r.members, r.filings = members, filings
        r.threshold, r.decision_date = case.threshold, case.decision_date
        return decide_reading(r)

    def truth(case):
        return solvency.decide(case, as_of=case.decision_date)[0]

    def hand(text, case):
        r = solv_signature(text)
        return WorldSnapshot(claims=_reading_to_claims(r))

    return dict(name="solvency", build=build, answer=answer, truth=truth,
                hand=hand)


def _reading_to_claims(r):
    from symbolic_ai_core.artifact.value import Interval
    from symbolic_ai_core.world import Claim
    out = []
    for m in sorted(r.members):
        out.append(Claim(predicate="owns",
                         roles={"parent": EntityRef("group"),
                                "child": EntityRef(m)}))
    for e, v, k in r.filings:
        out.append(Claim(predicate="revenue",
                         roles={"of": EntityRef(e),
                                "value": Quantity(value=v, unit="USD")},
                         valid_time=Interval(start="2026Q1", end="2026Q1"),
                         transaction_time=Interval(start=k, end=k)))
    return tuple(out)


def _sched_answer(world):
    """Feasibility from a claim set, by the exact oracle rather than the kernel.

    Projected here rather than through ``build_program`` so the arms are
    compared on the same code the generator's own ground truth uses -- a
    learned reading judged by the kernel would be measuring two things.
    """
    jobs, machines, needs, has = {}, {}, {}, {}
    for c in world.claims:
        q = c.roles.get("value")
        if c.predicate == "duration" and isinstance(q, Quantity):
            jobs[c.roles["of"].id] = float(q.value)
        elif c.predicate == "capacity" and isinstance(q, Quantity):
            machines[c.roles["of"].id] = float(q.value)
        elif c.predicate == "needs_capability":
            needs[c.roles["job"].id] = str(c.roles["capability"])
        elif c.predicate == "has_capability":
            has.setdefault(c.roles["machine"].id, []).append(
                str(c.roles["capability"]))
    if not jobs or not machines:
        return None
    J = {j: (v, needs.get(j, "")) for j, v in jobs.items()}
    M = {m: (v, tuple(sorted(has.get(m, [])))) for m, v in machines.items()}
    return feasible_by_search(J, M)


def scheduling_domain():
    def build(seed):
        c = scheduling.generate(seed)
        o = sched_obs(c, variants=V, hard_distractors=True)
        return c, o

    return dict(name="scheduling", build=build,
                answer=lambda world, case: _sched_answer(world),
                truth=lambda case: _sched_answer(case.world),
                hand=lambda text, case: sched_signature(text))


# ---------------------------------------------------------------- run
def run_domain(d) -> dict:
    name = d["name"]
    print(f"\n=== {name}: {N_TRAIN} train, {N_TEST} held-out, V={V}")
    train = [d["build"](s) for s in range(N_TRAIN)]
    test = [d["build"](1_000_000 + s) for s in range(N_TEST)]

    docs = [supervise(o.text, o.spans, c.world.claims) for c, o in train]
    labelled = sum(1 for doc in docs for u in doc if u.claim is not None)
    total_claims = sum(len(c.world.claims) for c, _ in train)
    print(f"    {sum(len(x) for x in docs)} units, {labelled} carry a claim; "
          f"{labelled/total_claims:.3f} of gold claims reach a unit "
          f"(the ceiling one-claim-per-sentence imposes)")

    schema = induce_schema(train)
    reader = LearnedSpanReader(id=f"learned.{name}@1").fit(docs)
    print(f"    lexicon: {len(reader.lex.forms)} memorised forms, "
          f"productive shapes {sorted(reader.lex.productive)}")
    print(f"    predicates: {sorted(reader.specs)}")

    rows = []
    for c, o in test:
        want = d["truth"](c)
        gold = {key(x) for x in canonical(c.world.claims, o.text)}

        res = reader.run(o.text)
        got_l = {key(x) for x in canonical(res.delta().claims, o.text)}
        pl, rl, fl = prf(gold, got_l)

        hw = d["hand"](o.text, c)
        got_h = {key(x) for x in canonical(hw.claims, o.text)}
        ph, rh, fh = prf(gold, got_h)

        def ans(world):
            try:
                return d["answer"](world, c)
            except Exception:
                return None

        rows.append({
            "seed": c.seed,
            "learned": {"p": pl, "r": rl, "f1": fl,
                        "ok": ans(world_from_claims(res.delta().claims,
                                                    schema)) == want,
                        "open": len(res.factors),
                        "unresolved": len(res.unresolved)},
            "hand": {"p": ph, "r": rh, "f1": fh,
                     "ok": ans(hw) == want},
            "oracle_ok": ans(c.world) == want,
        })

    def m(arm, f):
        return statistics.mean(r[arm][f] for r in rows)

    pos = [r["learned"]["f1"] for r in rows if r["learned"]["ok"]]
    neg = [r["learned"]["f1"] for r in rows if not r["learned"]["ok"]]
    rec_pos = [r["learned"]["r"] for r in rows if r["learned"]["ok"]]
    rec_neg = [r["learned"]["r"] for r in rows if not r["learned"]["ok"]]

    out = {
        "domain": name, "n_train": N_TRAIN, "n_test": N_TEST, "variants": V,
        "unit_ceiling": labelled / total_claims,
        "learned": {"p": m("learned", "p"), "r": m("learned", "r"),
                    "f1": m("learned", "f1"), "acc": m("learned", "ok"),
                    "open_factors": m("learned", "open"),
                    "unresolved": m("learned", "unresolved")},
        "hand": {"p": m("hand", "p"), "r": m("hand", "r"),
                 "f1": m("hand", "f1"), "acc": m("hand", "ok")},
        "oracle_acc": statistics.mean(r["oracle_ok"] for r in rows),
        "auc_f1_predicts_correct": auc(pos, neg),
        "auc_recall_predicts_correct": auc(rec_pos, rec_neg),
        "rows": rows,
    }
    print(f"    {'arm':<10} {'P':>7} {'R':>7} {'F1':>7} {'end-to-end':>11}")
    for arm in ("learned", "hand"):
        a = out[arm]
        print(f"    {arm:<10} {a['p']:7.3f} {a['r']:7.3f} {a['f1']:7.3f} "
              f"{a['acc']:11.3f}")
    print(f"    {'oracle':<10} {1.0:7.3f} {1.0:7.3f} {1.0:7.3f} "
          f"{out['oracle_acc']:11.3f}")
    print(f"    AUC(claim F1 -> answer correct) = "
          f"{out['auc_f1_predicts_correct']:.3f}   "
          f"(recall {out['auc_recall_predicts_correct']:.3f})")
    print(f"    learned reader left {out['learned']['open_factors']:.2f} "
          f"XOR factors and {out['learned']['unresolved']:.2f} unresolved "
          f"units per document")
    return out


def main() -> None:
    results = [run_domain(f()) for f in
               (solvency_domain, scheduling_domain, flood_domain)]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
