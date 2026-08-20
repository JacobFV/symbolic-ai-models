"""Does the router generalise off the relation it was found on?

Everything in the router arm is `occupation`: one relation, one frame, one value
type, one external inventory. That is exactly the assumption whose testing paid
off when the reading arm's claims were carried from company intros to
biographies, so it gets tested rather than asserted.

`employer` is the honest second case and is different in every way that matters:

    values      organisation names, not person-nouns. WordNet's `noun.person` is
                useless here, and an agentive-suffix rule has nothing to grip --
                there is no morphology that marks *Reuters* as an employer.
    frame       no obligatory opener. A biography always says *"is a X"*; it says
                *"worked for"*, *"joined"*, *"employed by"*, or nothing at all.
    proposer    capitalised runs, which is what proper-noun values need.

So the three components all change and only the **shape** is held constant:
learned reader, a zero-supervision positional floor, and a confidence router with
its threshold fitted on training documents.

Registered before running: the reader BEATS the floor here (unlike occupation,
where the floor won), because the value has no morphological signature; the router
still beats both but by less than occupation's +0.065; and the oracle headroom is
again near +0.10.

Run: uv run python -u scripts/router_second_relation.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from symbolic_ai_core.reader.learned import (CapitalisedMentions,
                                             LearnedSpanReader, _units)
from symbolic_ai_core.world import EntityRef

import scripts.real_text_reader as R
from scripts.multi_relation_world import norm
from scripts.occupation_control import FOLDS
from scripts.open_vocabulary_floor import hit
from scripts.people_decomposition import RELATIONS, corpus

OUT = Path("runs/router_second_relation.json")
REL = "employer"
#: which of the five candidate floors the router is paired against
FLOOR = "prep"
WINDOW = 40
#: FIRST ATTEMPT, kept because it is the finding. A hand list of employment
#: verbs fires in only 24% of documents and puts gold inside its window 3.6% of
#: the time -- a STRUCTURAL CEILING of 0.036, so its 0.025 was 69% of the best
#: it could ever do. The misses show why: real biographies say *"Senior
#: Investigator at X"*, *"Director-General of X"*, *"studying under Linnaeus at
#: X"* -- a bare preposition after a role noun, not an employment verb.
CUE = re.compile(r"\b(?:worked?(?:ed)?\s+(?:for|at|with)|employed\s+by|"
                 r"joined|hired\s+by|serves?\s+(?:as|at)|served\s+(?:as|at)|"
                 r"is\s+(?:a|an)\s+\w+\s+(?:at|for|with)|career\s+at)\b", re.I)
#: The fair floor: any preposition that can introduce an organisation.
PREP = re.compile(r"\b(?:at|of|for|with|by|from)\b", re.I)
#: The organisational analogue of the agentive suffix that beat the reader on
#: occupation. If a morphological rule wins there it deserves its shot here.
ORG = ("university", "institute", "laboratory", "college", "school",
       "company", "corporation", "corp", "inc", "ltd", "center", "centre",
       "academy", "association", "society", "foundation", "hospital",
       "museum", "observatory", "agency", "bureau", "commission", "council",
       "department", "ministry", "office", "bank", "group", "news", "press")


def org_like(text: str) -> bool:
    return text.lower().split()[-1] in ORG if text.split() else False


def judge(reader, prop, d) -> dict:
    gold = [g for g in d[REL] if g]
    res = reader.run(d["intro"], query=d.get("title", ""))
    best = None
    for i, c in enumerate(res.claims):
        v = c.roles.get("value")
        if c.predicate == REL and isinstance(v, EntityRef):
            if best is None or res.confidence_of(i) > best[0]:
                best = (res.confidence_of(i), v.id)
    cands = [(m.text, m.start, m.end)
             for u in _units(d["intro"]) for m in prop.find(u)]
    title = d.get("title", "")
    # the subject's own name is never the employer, and it is the most
    # frequent capitalised run in a biography
    free = [c for c in cands if c[0] not in title and title not in c[0]]

    def after(rx, pool):
        for m in rx.finditer(d["intro"]):
            near = [c for c in pool if 0 <= c[1] - m.end() <= WINDOW]
            if near:
                return min(near, key=lambda c: (c[1] - m.end(), -len(c[0])))[0]
        return None

    orgs = [c for c in free if org_like(c[0])]
    guesses = {
        "cue": after(CUE, cands),
        "prep": after(PREP, free),
        "org": orgs[0][0] if orgs else None,
        "prep_org": after(PREP, orgs) or (orgs[0][0] if orgs else None),
        "longest": (max(free, key=lambda c: len(c[0]))[0] if free else None),
    }
    guess = guesses[FLOOR]
    return {"conf": best[0] if best else 0.0,
            "r": bool(best) and norm(best[1]) in [norm(g) for g in gold],
            "f": hit(guess, gold),
            "floors": {k: hit(v, gold) for k, v in guesses.items()},
            "agree": bool(best) and guess is not None
            and norm(best[1]) == norm(guess),
            "has_f": guess is not None}


def route(rows, thr):
    return sum((x["f"] if (not x["agree"] and x["has_f"] and x["conf"] < thr)
                else x["r"]) for x in rows) / max(1, len(rows))


def main() -> None:
    R.RELS = RELATIONS
    docs = [d for d in corpus() if d.get(REL)]
    vocab = sorted({v for d in docs for v in d[REL]})
    prop = CapitalisedMentions()
    print(f"{len(docs)} biographies with an employer, "
          f"{len(vocab)} distinct employers")

    out = {}
    for slice_ in ("unseen", "seen"):
        te_rows, ho = [], []
        for fold in range(FOLDS):
            if slice_ == "seen":
                te = [d for i, d in enumerate(docs) if i % FOLDS == fold]
                tr = [d for i, d in enumerate(docs) if i % FOLDS != fold]
            else:
                held = {v for i, v in enumerate(vocab) if i % FOLDS == fold}
                te = [d for d in docs if all(v in held for v in d[REL])]
                tr = [d for d in docs if not any(v in held for v in d[REL])]
            if not (te and tr):
                continue
            reader = LearnedSpanReader(
                mentions=prop, extra_features=R.frame_features,
                extra_role_features=R.role_frame_features).fit(
                [R.supervise_distant(d) for d in tr])
            fit_rows = [judge(reader, prop, d) for d in tr[:400]]
            grid = sorted({x["conf"] for x in fit_rows} | {0.0, 1.0})
            thr = max(grid, key=lambda t: route(fit_rows, t))
            rows = [judge(reader, prop, d) for d in te]
            te_rows += rows
            ho.append((rows, thr))

        n = len(te_rows)
        if not n:
            print(f"  {slice_}: no items")
            continue
        rd = sum(x["r"] for x in te_rows) / n
        fl = sum(x["f"] for x in te_rows) / n
        orc = sum(x["r"] or x["f"] for x in te_rows) / n
        rt = sum(route(rows, t) * len(rows) for rows, t in ho) / n
        base = max(rd, fl)
        disc = [x for x in te_rows if x["r"] != x["f"]]
        allf = {k: sum(x["floors"][k] for x in te_rows) / n
                for k in te_rows[0]["floors"]}
        print(f"\n  floors on {slice_}: " + "  ".join(
            f"{k}={v:.3f}" for k, v in sorted(allf.items(),
                                              key=lambda kv: -kv[1])))
        out[slice_] = {"n": n, "reader": rd, "floor": fl, "oracle": orc,
                       "router": rt, "discordant": len(disc),
                       "headroom": orc - base, "gain": rt - base, "all_floors": allf,
                       "captured": ((rt - base) / (orc - base)
                                    if orc > base else float("nan"))}
        v = out[slice_]
        print(f"\n=== {slice_}  n={n}, discordant {len(disc)}")
        print(f"  reader {rd:.3f}   floor {fl:.3f}   oracle {orc:.3f}")
        print(f"  router {rt:.3f}   gain over best {rt - base:+.3f}   "
              f"captured {v['captured']:.1%}")

    print("\n--- against occupation")
    print(f"{'':<12}{'reader':>9}{'floor':>8}{'router':>8}{'gain':>8}")
    print(f"{'occupation':<12}{0.288:9.3f}{0.310:8.3f}{0.375:8.3f}{0.065:+8.3f}"
          f"   (unseen)")
    u = out.get("unseen")
    if u:
        print(f"{'employer':<12}{u['reader']:9.3f}{u['floor']:8.3f}"
              f"{u['router']:8.3f}{u['gain']:+8.3f}   (unseen)")
        if u["gain"] > 0:
            print("\n-> the router generalises to a second relation with "
                  "different values, a different frame and a different proposer.")
        else:
            print("\n-> the router does NOT generalise: it was a property of "
                  "occupation, not of pairing a reader with a rule.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
