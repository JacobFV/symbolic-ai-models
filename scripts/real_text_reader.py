"""The learned reader on real prose, fitted from distant supervision only.

Every number the learned reader has produced came from generated surfaces with
**exact span→claim alignment**. The status note named that as the expensive
input: not rules, but aligned spans. This asks whether the alignment is
necessary, on 168 Wikipedia company intros whose gold facts come from Wikidata
and whose spans nobody has ever marked.

Distant supervision: a sentence is labelled with relation `p` if it *contains* a
gold filler for `p`, and with nothing otherwise. No span is given, no role is
given, and the label is wrong whenever the string occurs for an unrelated
reason — which it does. That is the supervision a real corpus can actually
supply.

Three relations from the same 168 articles: `parent` (Wikidata P749 chains),
`country` (P17) and `headquarters` (P159). Mentions are proposed by capitalised
runs — knowledge of English, in the same category as the tokenizer — because a
name here is *Ministry of Communications*, three tokens with a lowercase one in
the middle and no shape to generalise.

Scored per document at strict, case-insensitive string equality against any gold
filler, over 4-fold cross-validation so every article is held out exactly once.

Predicted before running:

- **Distant supervision works at all** — the headline question. `parent` correct
  in 0.30–0.45, i.e. comparable to the hand-written state-first reader's 0.393
  and not obviously better, because that reader had a session of tuning against
  this corpus and this one sees 126 training articles per fold.
- **Coverage higher, precision lower** than the hand reader's 0.601 / 0.653: a
  classifier emits something for almost every article, while four patterns
  abstain.
- **`country` and `headquarters` are much easier than `parent`** — both are
  stated in the first sentence in a fixed frame (*headquartered in New Delhi,
  India*), so correct above 0.5, while a parent is stated anywhere or nowhere.
- Refuted if `parent` correct comes out below 0.15, which would mean the span
  alignment was carrying the earlier results and real corpora cannot supply what
  this reader needs.

Run: uv run python -u scripts/real_text_reader.py
"""

from __future__ import annotations

import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

from symbolic_ai_core.reader.learned import (CapitalisedMentions,
                                             LearnedSpanReader, Unit, _units)
from symbolic_ai_core.world import Claim, EntityRef

#: `--corpus <path>` swaps the article set. The default is the 168-article file
#: every published real-text number is measured on and it is never written to.
PARENTS = Path(sys.argv[sys.argv.index("--corpus") + 1]
               if "--corpus" in sys.argv
               else "data/artifacts/wikipedia_parents.jsonl")
RELATIONS = Path("data/artifacts/company_relations.jsonl")
OUT = Path("runs/real_text_reader.json")
FOLDS = 4
#: Multi-instance pruning: refit on one positive sentence per (article,
#: relation), chosen by the first pass. Set from the command line.
MIL = "--mil" in sys.argv
#: Hand the classifier WordNet supersenses. The hand-written pattern reader wins
#: on this corpus because it keys on RELATION WORDS, a tiny high-precision
#: feature set that 126 articles cannot supply. Supersenses are the external,
#: untuned way to get the same generalisation: `subsidiary`, `division` and
#: `unit` are all `noun.group`, and `owned` is `verb.possession`.
WORDNET = "--wordnet" in sys.argv
#: The claim the WordNet null left standing: what the hand reader knows is not
#: that `subsidiary` is a group noun but that "X is a subsidiary of Y" puts Y in
#: a slot. A FRAME is the token path BETWEEN two mentions, and it is derived from
#: this corpus rather than written down -- no relation word appears in the source.
FRAMES = "--frames" in sys.argv
#: Down-weight the negative class, chosen per outer fold by inner
#: cross-validation on the TRAINING articles only. The reader emits 0.54 parent
#: claims per document and its oracle over its own proposals is 0.107 against an
#: argmax of 0.101 -- it is not mis-ranking, it is abstaining, which is what an
#: order-of-magnitude class imbalance does to a margin-based classifier.
BALANCE = "--balance" in sys.argv
NONE_WEIGHTS = (1.0, 0.5, 0.25, 0.12, 0.06)
#: Longest gold string first, so `New Delhi, India` prefers the more specific
#: relation when two fillers both occur in one sentence.
RELS = ("parent", "headquarters", "country")


def supersense_features(u, mentions) -> list[str]:
    """One feature per supersense present, plus the pairs with the frame.

    Deliberately NOT tuned to this corpus: no list of relation words is written
    down anywhere here. WordNet is consulted for every token, and which senses
    matter is left to the fit -- which is the difference between using an
    external standard as a given and hand-writing patterns with extra steps.
    """
    from symbolic_ai_generators.wordnet import noun_supersenses, verb_supersenses
    inside = {i for m in mentions for i in range(m.start, m.end)}
    senses: set[str] = set()
    for t in u.tokens:
        if t.kind != "word" or t.start in inside:
            continue
        for ss in noun_supersenses(t.text) | verb_supersenses(t.text):
            senses.add(ss)
    out = [f"ss={x}" for x in sorted(senses)]
    out += [f"ss2={a}|{b}" for i, a in enumerate(sorted(senses))
            for b in sorted(senses)[i + 1:]][:60]
    return out


#: Function words carry no relation. Removing them is what turns a frame from a
#: string that occurs once into one that occurs repeatedly -- measured below.
STOP = frozenset("a an the of in to for and or is was are were be been by on at "
                 "as its it his her their this that with from".split())


def frame_features(u, mentions) -> list[str]:
    """The abstracted token path between consecutive mentions.

    A bag of n-grams over a sentence knows which words occur; a frame knows which
    words sit BETWEEN the two things being related. `is a subsidiary of` and
    `is a division of` are the same shape with one word changed, and both are
    invisible to a window feature that never anchors on the mentions.

    Paths are capped at six tokens because a longer one is not a frame, it is a
    sentence, and it would fire once in the corpus and never again.
    """
    if not mentions:
        return []
    ment = sorted(mentions, key=lambda m: m.start)
    words = [t for t in u.tokens if t.kind in ("word", "num")]
    inside = {i for m in ment for i in range(m.start, m.end)}
    out: list[str] = []
    for a, b in zip(ment, ment[1:]):
        gap = [t.text.lower() for t in words
               if a.end <= t.start < b.start and t.start not in inside]
        if len(gap) > 8:
            continue
        content = [w for w in gap if w not in STOP]
        # The full path is a singleton 91% of the time and its type inventory
        # grows almost as fast as the data (Heaps 0.83), so it is kept only as a
        # last resort and the CONTENT words carry the feature (Heaps 0.64).
        out.append(f"fr.tail={'_'.join(gap[-2:])}")
        if content:
            out += [f"fr.cw={content[-1]}", f"fr.cw2={'_'.join(content[-2:])}"]
            out += [f"fr.cwany={w}" for w in dict.fromkeys(content[-4:])]
    first = ment[0]
    lead = [t.text.lower() for t in words if t.start < first.start][:3]
    out.append(f"fr.lead={'_'.join(lead)}")
    out.append(f"fr.n={min(len(ment), 5)}")
    return out


def role_frame_features(pred, role, cands, j, u) -> list[str]:
    """What sits between this candidate and the mention before it.

    The ranker's version of a frame, and the place the idea belongs: *X is a
    subsidiary of Y* says which SLOT Y fills, not which kind of sentence this is.

    The **last content word** is the feature that matters, and finding that out
    cost an arm. Keyed on the full token path, a `parent` frame is a singleton
    91.2% of the time and its Heaps exponent is 0.830 -- the inventory grows
    almost as fast as the data, so no corpus makes it repeat. Dropping to the
    last content word before the mention takes singletons to 0.741, the top-5
    share from 0.179 to 0.463, and the exponent to 0.641. Same corpus, same
    sentences: the representation was the problem, not the amount of text.
    """
    t = cands[j]
    words = [w for w in u.tokens if w.kind in ("word", "num")]
    before = [w.text.lower() for w in words if w.end <= t.start]
    after = [w.text.lower() for w in words if w.start >= t.end]
    prev_m = max((c.end for c in cands if c.end <= t.start), default=u.start)
    left = [w.text.lower() for w in words if prev_m <= w.start < t.start]
    content = [w for w in left if w not in STOP]
    out = [f"lead={'_'.join(before[:3])}", f"tail={'_'.join(after[:2])}",
           f"nleft={min(len(left), 6)}", f"path={'_'.join(left[-2:])}"]
    if content:
        out += [f"cw={content[-1]}", f"cw2={'_'.join(content[-2:])}",
                f"cw.gap={content[-1]}|{min(len(left) - len(content), 3)}"]
    else:
        out.append("cw=<none>")
    # Content words anywhere to the left, not only the last -- a relation stated
    # early in a long sentence is otherwise invisible to an adjacency feature.
    out += [f"cwany={w}" for w in dict.fromkeys(content[-4:])]
    return out


def extra() -> object:
    """Whichever feature sources the flags asked for, composed."""
    parts = ([supersense_features] if WORDNET else []) + \
            ([frame_features] if FRAMES else [])
    if not parts:
        return None
    return lambda u, m: [f for fn in parts for f in fn(u, m)]


def fit_reader(train_docs, none_weight: float | None):
    from symbolic_ai_core.reader.learned import NONE
    w = None if none_weight is None else {
        NONE: none_weight, **{r: 1.0 for r in RELS}}
    return LearnedSpanReader(
        mentions=CapitalisedMentions(), extra_features=extra(), weights=w,
        extra_role_features=role_frame_features if FRAMES else None).fit(
        [supervise_distant(d) for d in train_docs])


def correct_share(reader, docs) -> float:
    hit = n = 0
    for d in docs:
        got = answers(reader, d)
        for rel in RELS:
            gold = [g.lower() for g in (d.get(rel) or [])]
            if not gold:
                continue
            n += 1
            hit += rel in got and got[rel].lower() in gold
    return hit / max(1, n)


def choose_none_weight(train_docs) -> float:
    """Inner 3-fold CV on the TRAINING articles. Never touches the outer test.

    Selecting this on the evaluation would be the repo's oldest mistake wearing a
    hyperparameter's clothes.
    """
    best, best_score = 1.0, -1.0
    for w in NONE_WEIGHTS:
        score = 0.0
        for k in range(3):
            inner_te = [d for i, d in enumerate(train_docs) if i % 3 == k]
            inner_tr = [d for i, d in enumerate(train_docs) if i % 3 != k]
            score += correct_share(fit_reader(inner_tr, w), inner_te)
        if score > best_score:
            best, best_score = w, score
    return best


def corpus() -> list[dict]:
    """Articles with their intro and every gold filler we have for them."""
    intros = {}
    for line in PARENTS.read_text().splitlines():
        r = json.loads(line)
        intros[r["qid"]] = {"qid": r["qid"], "title": r["title"],
                            "intro": r["intro"], "parent": list(r["current"]),
                            "country": [], "headquarters": []}
    if not RELATIONS.exists():
        return [d for d in intros.values() if d["intro"]]
    for line in RELATIONS.read_text().splitlines():
        r = json.loads(line)
        if r["qid"] in intros:
            intros[r["qid"]]["country"] = list(r.get("country") or [])
            intros[r["qid"]]["headquarters"] = list(r.get("headquarters") or [])
    return [d for d in intros.values() if d["intro"]]


def label(sentence: str, gold: dict) -> tuple[str, str] | None:
    """Which relation this sentence is distant-supervised for, and by which
    string. Longest match wins, so a sentence naming both a city and a country
    is labelled for the more specific one rather than by dictionary order."""
    best = None
    for rel in RELS:
        for filler in gold.get(rel) or ():
            if filler and filler in sentence:
                if best is None or len(filler) > len(best[1]):
                    best = (rel, filler)
    return best


def supervise_distant(doc: dict) -> list[Unit]:
    """Units labelled by string containment. No spans, no roles, no oracle.

    The claim carries ONE read role -- the filler. The article's subject is not
    read from the sentence because it is not usually in it: the intro says *"It
    is an organisation under the Ministry of Communications"*, and the child of
    that relation is the document, not a mention.
    """
    units = _units(doc["intro"])
    for u in units:
        hit = label(u.text, doc)
        if hit is None:
            continue
        rel, filler = hit
        u.claim = Claim(predicate=rel, roles={"value": EntityRef(filler)})
    return units


def prune_to_best(reader, units_by_doc):
    """Multi-instance pruning: one positive per (article, relation).

    Distant supervision's at-least-one assumption is that *some* sentence
    containing the gold string states the relation, not that all of them do. The
    label on the others is wrong, and on this corpus there are 516 supervised
    sentences for 168 articles -- three positives per article for a fact stated
    once. Keeping only the sentence the current model scores highest is the
    standard fix and it tests the diagnosis directly: if the loss is noise, this
    helps; if it is volume, this makes it worse by discarding two thirds of the
    positives.
    """
    from symbolic_ai_core.reader.learned import _unit_features
    out = []
    for doc in units_by_doc:
        best: dict[str, tuple[float, Unit]] = {}
        for u in doc:
            if u.claim is None:
                continue
            score = reader.clf.score(reader.features(u)).get(u.claim.predicate, 0.0)
            cur = best.get(u.claim.predicate)
            if cur is None or score > cur[0]:
                best[u.claim.predicate] = (score, u)
        keep = {id(u) for _, u in best.values()}
        for u in doc:
            if u.claim is not None and id(u) not in keep:
                u.claim = None
        out.append(doc)
    return out


def answers(reader, doc: dict) -> dict[str, str]:
    """One answer per relation: the claim the reader believes most."""
    res = reader.run(doc["intro"])
    best: dict[str, tuple[float, str]] = {}
    for i, c in enumerate(res.claims):
        v = c.roles.get("value")
        if not isinstance(v, EntityRef):
            continue
        b = res.confidence_of(i)
        if c.predicate not in best or b > best[c.predicate][0]:
            best[c.predicate] = (b, v.id)
    return {k: v for k, (_, v) in best.items()}


def decomposition(docs) -> dict:
    """Where the loss is, as a product of three factors that must multiply out.

    A distantly supervised reader cannot beat the share of articles that HAVE a
    sentence containing the gold string; of those it must label the sentence;
    of those it must pick the right mention. If the product does not reproduce
    the end-to-end number, one of the three is measuring something else.
    """
    from symbolic_ai_core.reader.learned import _unit_features
    cm = CapitalisedMentions()
    ceiling, proposed, present = defaultdict(int), defaultdict(int), defaultdict(int)
    for d in docs:
        units = _units(d["intro"])
        for rel in RELS:
            if any(label(u.text, d) and label(u.text, d)[0] == rel
                   for u in units):
                ceiling[rel] += 1
            for f in (d.get(rel) or ()):
                if f in d["intro"]:
                    present[rel] += 1
                    proposed[rel] += any(t.text == f for u in units
                                         for t in cm.find(u))
    train, test = docs[42:], docs[:42]
    reader = LearnedSpanReader(
        mentions=cm, extra_features=extra(),
        extra_role_features=role_frame_features if FRAMES else None
    ).fit([supervise_distant(d) for d in train])
    clf, clf_n, rank, rank_n = (defaultdict(int) for _ in range(4))
    for d in test:
        for u in _units(d["intro"]):
            hit = label(u.text, d)
            if not hit:
                continue
            pred, _ = reader.clf.predict(reader.features(u))
            clf_n[hit[0]] += 1
            clf[hit[0]] += pred == hit[0]
            if pred != hit[0]:
                continue
            roles, _, _ = reader._fill(u, pred, [],
                                       [t.text for t in cm.find(u)])
            v = roles.get("value")
            rank_n[hit[0]] += 1
            rank[hit[0]] += v is not None and v.id == hit[1]
    return {rel: {
        "ceiling": ceiling[rel] / len(docs),
        "gold_string_proposed": proposed[rel] / max(1, present[rel]),
        "classifier_recall": clf[rel] / max(1, clf_n[rel]),
        "ranker_given_label": rank[rel] / max(1, rank_n[rel]),
        "product": (ceiling[rel] / len(docs)) * (clf[rel] / max(1, clf_n[rel]))
                   * (rank[rel] / max(1, rank_n[rel]))} for rel in RELS}


def learning_curve(docs) -> dict:
    """Is the classifier short of data or drowning in wrong labels?

    Distant supervision mislabels: a sentence naming the parent for an unrelated
    reason is a positive. If recall is still climbing at the full corpus, the
    binding constraint is 168 articles; if it has flattened, it is the noise, and
    more of this corpus would not help.
    """
    from symbolic_ai_core.reader.learned import _unit_features
    cm = CapitalisedMentions()
    train, test = docs[42:], docs[:42]
    out = {}
    for share in (0.25, 0.5, 1.0):
        part = train[:max(1, int(len(train) * share))]
        reader = LearnedSpanReader(
            mentions=cm, extra_features=extra(),
            extra_role_features=role_frame_features if FRAMES else None
        ).fit([supervise_distant(d) for d in part])
        ok, n = defaultdict(int), defaultdict(int)
        for d in test:
            for u in _units(d["intro"]):
                hit = label(u.text, d)
                if not hit:
                    continue
                pred, _ = reader.clf.predict(reader.features(u))
                n[hit[0]] += 1
                ok[hit[0]] += pred == hit[0]
        out[f"{len(part)} articles"] = {r: ok[r] / max(1, n[r]) for r in RELS}
    return out


def main() -> None:
    docs = corpus()
    print(f"{len(docs)} articles; gold coverage per relation: " + ", ".join(
        f"{r} {sum(1 for d in docs if d.get(r)) / len(docs):.3f}"
        for r in RELS))

    hits = defaultdict(int)
    answered = defaultdict(int)
    have = defaultdict(int)
    lenient = defaultdict(int)
    supervised = defaultdict(int)
    for fold in range(FOLDS):
        test = [d for i, d in enumerate(docs) if i % FOLDS == fold]
        train = [d for i, d in enumerate(docs) if i % FOLDS != fold]
        units = [supervise_distant(d) for d in train]
        for doc in units:
            for u in doc:
                if u.claim is not None:
                    supervised[u.claim.predicate] += 1
        if BALANCE:
            nw = choose_none_weight(train)
            print(f"    fold {fold}: NONE weight {nw} chosen by inner CV",
                  flush=True)
            reader = fit_reader(train, nw)
        else:
            reader = fit_reader(train, None)
        ex = extra()
        if MIL:
            reader = LearnedSpanReader(mentions=CapitalisedMentions(),
                                       extra_features=ex).fit(
                prune_to_best(reader, units))
        for d in test:
            got = answers(reader, d)
            for rel in RELS:
                gold = [g.lower() for g in (d.get(rel) or [])]
                if not gold:
                    continue
                have[rel] += 1
                if rel not in got:
                    continue
                answered[rel] += 1
                mine = got[rel].lower()
                hits[rel] += mine in gold
                lenient[rel] += any(mine in g or g in mine for g in gold)

    print(f"\n    {'relation':<14} {'sup.sents':>9} {'coverage':>9} "
          f"{'correct':>8} {'precision':>10} {'lenient':>8}")
    rows = {}
    for rel in RELS:
        n = have[rel]
        cov = answered[rel] / n if n else 0.0
        cor = hits[rel] / n if n else 0.0
        pre = hits[rel] / answered[rel] if answered[rel] else 0.0
        len_ = lenient[rel] / n if n else 0.0
        print(f"    {rel:<14} {supervised[rel]:9d} {cov:9.3f} {cor:8.3f} "
              f"{pre:10.3f} {len_:8.3f}")
        rows[rel] = {"n": n, "coverage": cov, "correct": cor, "precision": pre,
                     "lenient_correct": len_, "supervised_sentences":
                     supervised[rel]}

    dec = decomposition(docs)
    print(f"\n    {'relation':<14} {'ceiling':>8} {'proposed':>9} "
          f"{'clf recall':>11} {'ranker':>8} {'product':>8}")
    for rel in RELS:
        r = dec[rel]
        print(f"    {rel:<14} {r['ceiling']:8.3f} "
              f"{r['gold_string_proposed']:9.3f} "
              f"{r['classifier_recall']:11.3f} {r['ranker_given_label']:8.3f} "
              f"{r['product']:8.3f}")

    curve = learning_curve(docs)
    print(f"\n    classifier recall against training size")
    for k, v in curve.items():
        print(f"    {k:<14} " + "  ".join(f"{r} {v[r]:.3f}" for r in RELS))

    print("\n    the number to beat on `parent` is the hand-written "
          "state-first reader:\n    coverage 0.601, correct 0.393, "
          "precision 0.653 -- tuned against this corpus.")
    tag = ("_mil" if MIL else "") + ("_wordnet" if WORDNET else "") + \
        ("_frames" if FRAMES else "") + ("_balance" if BALANCE else "")
    if PARENTS.name != "wikipedia_parents.jsonl":
        tag += "_" + PARENTS.stem.replace("wikipedia_parents", "").strip("_")
    out_path = OUT.with_name(f"real_text_reader{tag}.json") if tag else OUT
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"n_articles": len(docs), "folds": FOLDS,
                               "multi_instance": MIL,
                               "relations": rows, "decomposition": dec,
                               "learning_curve": curve}, indent=2))
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()
