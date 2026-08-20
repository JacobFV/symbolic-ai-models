"""Is `occupation`'s 0.615 reading, or a vocabulary lookup?

The second-domain arm found the learned reader reads `occupation` end-to-end at
**0.615** -- 2.7x the best figure the company arm produced -- and the finding
recorded it `status: provisional` for one reason: the proposer is
`PhraseMentions.induce`d from training fillers, and occupations are a small closed
set. This repo has one control that has killed a headline before (ensemble-001's
1.14 bits went to 0.038 under permutation), and it had not been run.

Two controls, because they ask different questions and this arm's own prediction
is that they **disagree**:

    renamed      every occupation string is replaced by an invented token,
                 consistently in the intro text, the gold, and the training
                 fillers. Vocabulary is destroyed; the syntactic frame is
                 untouched. A reader that reads POSITION survives.

    unseen       the vocabulary is split. Test only on articles whose gold
                 occupation never appears in training. Nothing is renamed; the
                 frame is untouched too. A reader that has MEMORISED a closed
                 set collapses, and the four-factor decomposition says which
                 component did the collapsing.

The registered prediction, before the run: renamed survives above 0.40, unseen
collapses below 0.10, and the collapse lands on **proposal** rather than on the
classifier -- because a proposer induced from training fillers cannot offer a
filler it has never seen. If that holds, 0.615 is genuine frame-reading over a
closed vocabulary, which is a real capability with a named and measured limit.

Run: uv run python -u scripts/occupation_control.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from symbolic_ai_core.reader.learned import (LearnedSpanReader, PhraseMentions,
                                             _units)
from symbolic_ai_core.world import EntityRef

import scripts.real_text_reader as R
from scripts.multi_relation_world import norm
from scripts.people_decomposition import CORPUS, RELATIONS, corpus

OUT = Path("runs/occupation_control.json")
FOLDS = 4
REL = "occupation"
#: Invented tokens, deterministic, and deliberately not English words. The point
#: is to leave the frame and destroy the lexeme.
SYLL = ("vor", "kel", "mus", "tar", "zin", "pel", "dor", "gan", "riv", "sut")


def coin(i: int) -> str:
    a, b = SYLL[i % len(SYLL)], SYLL[(i // len(SYLL)) % len(SYLL)]
    return f"{a}{b}{i // 100}" if i >= 100 else f"{a}{b}"


def rename(docs: list[dict]) -> list[dict]:
    """Replace every occupation string consistently, text and gold alike.

    Renaming by string substitution is what shifted span offsets and read as a
    catastrophic reader failure last time. Here the substitution IS the case --
    the text is rewritten and the gold is rewritten with it, so offsets are
    recomputed from the rewritten text by `_units`, never carried across.
    """
    vocab = sorted({v for d in docs for v in (d.get(REL) or [])})
    table = {v: coin(i) for i, v in enumerate(vocab)}
    out = []
    for d in docs:
        e = dict(d)
        text = d["intro"]
        # longest first, so 'film director' is not clipped by 'director'
        for v in sorted(vocab, key=len, reverse=True):
            if v in text:
                text = text.replace(v, table[v])
        e["intro"] = text
        e[REL] = [table[v] for v in (d.get(REL) or [])]
        out.append(e)
    return out, table


def score(train: list[dict], test: list[dict]) -> dict:
    """End-to-end rate plus the four factors, on one train/test split."""
    fillers = [v for d in train for v in (d.get(REL) or [])]
    if not fillers:
        return {}
    prop = PhraseMentions.induce(fillers)
    reader = LearnedSpanReader(
        mentions=prop, extra_features=R.frame_features,
        extra_role_features=R.role_frame_features).fit(
        [R.supervise_distant(d) for d in train])
    c_n = c_k = p_n = p_k = f_n = f_k = r_n = r_k = ok = n = 0
    for d in test:
        gold = [x for x in (d.get(REL) or []) if x]
        if not gold:
            continue
        n += 1
        units = _units(d["intro"])
        c_n += 1
        hits = [(u, g) for u in units for g in gold if g in u.text]
        c_k += bool(hits)
        if hits:
            p_n += 1
            proposed = [(u, g) for u, g in hits
                        if any(m.text == g for m in prop.find(u))]
            p_k += bool(proposed)
            if proposed:
                f_n += 1
                lab = []
                for u, g in proposed:
                    u.query = d.get("title", "")
                    pred, _ = reader.clf.predict(reader.features(u))
                    if pred == REL:
                        lab.append((u, g))
                f_k += bool(lab)
                if lab:
                    r_n += 1
                    got = False
                    for u, g in lab:
                        roles, _, _ = reader._fill(
                            u, REL, [], [m.text for m in prop.find(u)])
                        v = roles.get("value")
                        got = got or (isinstance(v, EntityRef) and v.id == g)
                    r_k += got
        res = reader.run(d["intro"], query=d.get("title", ""))
        best = None
        for i, c in enumerate(res.claims):
            v = c.roles.get("value")
            if c.predicate == REL and isinstance(v, EntityRef):
                if best is None or res.confidence_of(i) > best[0]:
                    best = (res.confidence_of(i), v.id)
        ok += bool(best) and norm(best[1]) in [norm(x) for x in gold]
    return {"containment": c_k / max(1, c_n), "proposal": p_k / max(1, p_n),
            "classifier": f_k / max(1, f_n), "ranker": r_k / max(1, r_n),
            "measured": ok / max(1, n), "n": n}


def pooled(rows: list[dict]) -> dict:
    keys = ("containment", "proposal", "classifier", "ranker", "measured")
    tot = sum(r["n"] for r in rows) or 1
    out = {k: sum(r[k] * r["n"] for r in rows) / tot for k in keys}
    out["n"] = tot
    out["product"] = (out["containment"] * out["proposal"]
                      * out["classifier"] * out["ranker"])
    return out


def main() -> None:
    R.RELS = RELATIONS
    docs = [d for d in corpus() if d.get(REL)]
    print(f"{len(docs)} biographies with an occupation")
    vocab = sorted({v for d in docs for v in d[REL]})
    print(f"{len(vocab)} distinct occupation values "
          f"({len(vocab) / len(docs):.3f} per article) -- a closed set is the "
          f"alternative being tested")

    out = {}

    # --- arm 1: base, reproducing the arm's own 0.615 on this exact slice
    rows = []
    for fold in range(FOLDS):
        te = [d for i, d in enumerate(docs) if i % FOLDS == fold]
        tr = [d for i, d in enumerate(docs) if i % FOLDS != fold]
        rows.append(score(tr, te))
    out["base"] = pooled(rows)

    # --- arm 2: consistent renaming, vocabulary destroyed, frame intact
    ren, table = rename(docs)
    rows = []
    for fold in range(FOLDS):
        te = [d for i, d in enumerate(ren) if i % FOLDS == fold]
        tr = [d for i, d in enumerate(ren) if i % FOLDS != fold]
        rows.append(score(tr, te))
    out["renamed"] = pooled(rows)
    print(f"\nrenamed {len(table)} occupation strings, e.g. "
          f"{list(table.items())[:3]}")

    # --- arm 3: unseen-value holdout, vocabulary split, nothing renamed
    rows = []
    for fold in range(FOLDS):
        held = {v for i, v in enumerate(vocab) if i % FOLDS == fold}
        te = [d for d in docs if all(v in held for v in d[REL])]
        tr = [d for d in docs if not any(v in held for v in d[REL])]
        if te and tr:
            rows.append(score(tr, te))
    out["unseen"] = pooled(rows) if rows else {}

    print(f"\n{'arm':<10}{'contain':>9}{'propose':>9}{'clf':>7}{'rank':>7}"
          f"{'product':>9}{'measured':>10}{'n':>7}")
    for k in ("base", "renamed", "unseen"):
        v = out.get(k)
        if not v:
            print(f"{k:<10}  (no split had both sides)")
            continue
        print(f"{k:<10}{v['containment']:9.3f}{v['proposal']:9.3f}"
              f"{v['classifier']:7.3f}{v['ranker']:7.3f}{v['product']:9.3f}"
              f"{v['measured']:10.3f}{v['n']:7d}")

    b = out["base"]["measured"]
    print(f"\n--- the verdict")
    for k in ("renamed", "unseen"):
        v = out.get(k)
        if not v:
            continue
        keep = v["measured"] / b if b else 0.0
        fac = {x: v[x] for x in ("containment", "proposal", "classifier",
                                 "ranker")}
        lo = min(fac, key=fac.get)
        print(f"{k:<10} {v['measured']:.3f} vs base {b:.3f} "
              f"= {keep:.1%} retained; binding factor {lo} at {fac[lo]:.3f}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
