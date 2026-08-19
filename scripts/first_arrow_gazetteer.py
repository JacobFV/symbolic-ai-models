"""Does the extraction gap close with knowledge rather than with a better matcher?

The corrected finding
(`notes/findings/2026-08-18-the-first-arrow-is-cheap-and-bad.md`, §D bis)
localised the first arrow's failure precisely:

* the label **is** a function of the input — a memoriser handed verbatim-seen
  strings scores **98.2% exact**, so there is essentially no irreducible noise;
* **91.6%** of held-out authorship strings were never seen verbatim;
* the best learned extractor reaches **48.9%** of that ceiling.

So the entire residual is generalising to an unseen *wording* of an institution.
That is a **knowledge** problem before it is an algorithm problem: the dictionary
only knows institutions that turned up in 3,500 training works, while ROR
publishes **135,710** of them with 449,658 name variants — labels, aliases,
acronyms, multilingual — CC0 and unauthenticated.

This repo's stated principle is that **external resources are givens**: use the
real standard rather than re-deriving it. The extraction arrow is the first place
that principle can be tested on something that matters, so:

    v4  gazetteer only     — ZERO-SHOT. No training split, no learned
                             dictionary. What the registry alone buys.
    v5  v3 + gazetteer     — external knowledge narrows the candidates, local
                             statistics disambiguate among them.

v4 is the scientifically interesting rung: an extractor with no training data at
all. If it is competitive, the learned dictionary was never the point.

**Fairness, stated rather than implied.** Using ROR's own names to predict ROR
ids is not cheating — it is what a symbolic system *should* do with an
authoritative registry, and OpenAlex almost certainly does the same. But it does
make v4 a registry lookup rather than a general text-to-entity method, and the
result must be read as such.

Run: uv run python -u scripts/first_arrow_gazetteer.py
"""

from __future__ import annotations

import json
import random
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable

from scripts.first_arrow_ladder import Index, measure_ceiling, v0, v3
from scripts.first_arrow_prose import (SEED, SRC, TRAIN_FRAC, components, load,
                                       norm, score)

ROR = Path("data/sources/ror/ror-v2.11-2026-08-03/names.jsonl")
OUT = Path("runs/first_arrow_gazetteer.json")

#: Name types that are safe to match on directly. Acronyms are held out: they
#: are short, wildly ambiguous ("MIT", "UCL", "CAS"), and after casefolding they
#: collide with ordinary words. They get their own index and a stricter rule.
SAFE_TYPES = {"label", "ror_display", "alias"}


class Gazetteer:
    """Normalised institution name -> the ROR ids that carry it."""

    def __init__(self, path: Path) -> None:
        self.by_name: dict[str, set[str]] = defaultdict(set)
        self.by_acronym: dict[str, set[str]] = defaultdict(set)
        self.by_token: dict[str, set[str]] = defaultdict(set)
        self._name_tokens: dict[str, frozenset[str]] = {}
        self.n_orgs = 0
        self.n_names = 0
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            org = json.loads(line)
            if org.get("status") not in (None, "active"):
                continue
            self.n_orgs += 1
            for n in org["names"]:
                v = norm(n["v"])
                if not v:
                    continue
                self.n_names += 1
                types = set(n["t"])
                if types & SAFE_TYPES:
                    self.by_name[v].add(org["id"])
                    tk = frozenset(v.split())
                    self._name_tokens[v] = tk
                    # Index each name under its rarest-looking token later; for
                    # now record every token, and prune after the pass.
                    for t in tk:
                        self.by_token[t].add(v)
                if "acronym" in types:
                    self.by_acronym[v].add(org["id"])

    def lookup(self, component: str) -> set[str]:
        return self.by_name.get(component, set())

    def contained_in(self, component: str) -> set[str]:
        """Registry names whose tokens are all present in this component.

        "department of physics university of tokyo" contains "university of
        tokyo" and should resolve to it. Candidates are found through the
        component's RAREST token, so this is a lookup rather than a scan, and
        the longest containing name wins because it is the most specific.
        """
        toks = set(component.split())
        if not toks:
            return set()
        rare = min(toks, key=lambda t: len(self.by_token.get(t, ())) or 10**9)
        best: tuple[int, set[str]] = (0, set())
        for name in self.by_token.get(rare, ()):
            nt = self._name_tokens[name]
            if len(nt) >= 2 and nt <= toks and len(nt) > best[0]:
                best = (len(nt), self.by_name[name])
        return best[1] if len(best[1]) == 1 else set()

    def lookup_acronym(self, component: str) -> set[str]:
        # Only unambiguous acronyms, and only when the component IS the acronym
        # rather than containing it. A three-letter component that names two
        # institutions names neither.
        hits = self.by_acronym.get(component, set())
        return hits if len(hits) == 1 else set()


#: Expansions chosen from what an affiliation string IS -- a postal-style path
#: through abbreviations -- and not from reading scores. Recall was 43-54% at v4
#: and v5 because "univ of tokyo" is not "university of tokyo" and a component
#: carrying a department plus an institution matches neither exactly.
ABBREV = {
    "univ": "university", "universite": "university", "universitat": "university",
    "dept": "department", "dep": "department", "depto": "department",
    "inst": "institute", "instituto": "institute", "natl": "national",
    "nat": "national", "lab": "laboratory", "labs": "laboratories",
    "sci": "science", "tech": "technology", "technol": "technology",
    "med": "medical", "hosp": "hospital", "res": "research", "ctr": "center",
    "cntr": "center", "centre": "center", "acad": "academy", "coll": "college",
    "sch": "school", "eng": "engineering", "engn": "engineering",
    "coll.": "college", "coop": "cooperative", "coorp": "corporation",
    "corp": "corporation", "assoc": "association", "coe": "college",
}


def expand(component: str) -> str:
    """Rewrite abbreviations, so a component can meet a registry name."""
    return " ".join(ABBREV.get(t, t) for t in component.split())


def v6(ix: Index, gz: Gazetteer, raw: str) -> set[str]:
    """v5, plus abbreviation expansion and containment matching.

    The last rung. Recall was the shortfall at v4 and v5 — nearly half of the
    true institutions were never proposed — and the two causes are surface, not
    knowledge: an abbreviated wording, and a component that *contains* an
    institution name alongside a department. Both are fixed by rewriting and by
    matching a registry name whose tokens are a subset of the component's.
    """
    hit = ix.full.get(norm(raw))
    if hit:
        return set(hit)
    out: set[str] = set()
    for c0 in components(raw):
        c = expand(c0)
        for cand in (c, c0):
            hits = gz.lookup(cand)
            if len(hits) == 1:
                out |= hits
                break
            if len(hits) > 1:
                votes = ix.comp.get(c0)
                ranked = ([(n, r) for r, n in votes.items() if r in hits]
                          if votes else [])
                if ranked:
                    out.add(max(ranked)[1])
                    break
        else:
            got = gz.contained_in(c)
            if len(got) == 1:
                out |= got
            elif not got:
                out |= gz.lookup_acronym(c0)
    return out or v5(ix, gz, raw)


def v4(gz: Gazetteer, raw: str) -> set[str]:
    """Zero-shot: match components against the registry, and nothing else.

    No training data is consulted. A component that names exactly one
    institution is evidence; one that names several is ambiguous and is
    discarded rather than guessed at, because this repo's measured lesson is
    that abstaining beats guessing.
    """
    out: set[str] = set()
    for c in components(raw):
        hits = gz.lookup(c)
        if len(hits) == 1:
            out |= hits
        elif not hits:
            out |= gz.lookup_acronym(c)
    return out


def v5(ix: Index, gz: Gazetteer, raw: str) -> set[str]:
    """Registry narrows, local statistics disambiguate, learned extractor fills.

    The composition the repo's thesis actually predicts: authoritative external
    structure supplies the candidate set, and cheap local computation picks
    among candidates it could not have enumerated itself.
    """
    hit = ix.full.get(norm(raw))
    if hit:
        return set(hit)
    out: set[str] = set()
    for c in components(raw):
        hits = gz.lookup(c)
        if len(hits) == 1:
            out |= hits
        elif len(hits) > 1:
            # Ambiguous in the registry: let training frequency choose, but only
            # among the candidates the registry allows.
            votes = ix.comp.get(c)
            if votes:
                ranked = [(n, r) for r, n in votes.items() if r in hits]
                if ranked:
                    out.add(max(ranked)[1])
        else:
            out |= gz.lookup_acronym(c)
    return out or v3(ix, raw)


def main() -> None:
    print(f"loading gazetteer {ROR} ...", flush=True)
    t0 = time.perf_counter()
    gz = Gazetteer(ROR)
    print(f"  {gz.n_orgs:,} active organizations, {gz.n_names:,} name variants, "
          f"{len(gz.by_name):,} distinct normalised names, "
          f"{len(gz.by_acronym):,} acronyms ({time.perf_counter()-t0:.0f}s)",
          flush=True)
    amb = sum(1 for v in gz.by_name.values() if len(v) > 1)
    print(f"  {amb:,} names ({amb/max(1,len(gz.by_name)):.1%}) are ambiguous "
          f"across institutions and are discarded rather than guessed",
          flush=True)

    rng = random.Random(SEED)
    works = load()
    idx = list(range(len(works)))
    rng.shuffle(idx)
    cut = int(len(idx) * TRAIN_FRAC)
    train = [works[i] for i in idx[:cut]]
    test = [works[i] for i in idx[cut:]]
    ix = Index(train)

    pairs = [(a["raw"], set(a["rors"])) for w in test for a in w["affiliations"]
             if a["rors"]]
    unseen = [p for p in pairs if norm(p[0]) not in ix.full]
    ceiling = measure_ceiling(ix, pairs)
    print(f"\n{SRC.parent.name}: {len(pairs):,} held-out, {len(unseen):,} never "
          f"seen ({len(unseen)/len(pairs):.1%}); ceiling F1 {ceiling['f1']:.3f}",
          flush=True)

    rungs: list[tuple[str, Callable[[str], set[str]]]] = [
        ("v0  component vote (learned)", lambda r: v0(ix, r)),
        ("v3  best learned rung", lambda r: v3(ix, r)),
        ("v4  gazetteer only (ZERO-SHOT)", lambda r: v4(gz, r)),
        ("v5  v3 + gazetteer", lambda r: v5(ix, gz, r)),
        ("v6  + abbrev & containment", lambda r: v6(ix, gz, r)),
    ]

    hdr = (f"{'rung':<34} {'F1 unseen':>10} {'% ceiling':>10} {'prec':>7} "
           f"{'rec':>7} {'F1 all':>8} {'ns/str':>9}")
    print()
    print(hdr)
    print("-" * len(hdr))
    rows = {}
    for name, fn in rungs:
        t = time.perf_counter_ns()
        u = score([(fn(raw), truth) for raw, truth in unseen])
        ns = (time.perf_counter_ns() - t) / max(1, len(unseen))
        a = score([(fn(raw), truth) for raw, truth in pairs])
        rows[name] = {"unseen": u, "all": a,
                      "frac_of_ceiling": u["f1"] / ceiling["f1"],
                      "ns_per_string": ns}
        print(f"{name:<34} {u['f1']:>10.3f} "
              f"{u['f1']/ceiling['f1']:>9.1%} {u['precision']:>6.1%} "
              f"{u['recall']:>6.1%} {a['f1']:>8.3f} {ns:>8,.0f}")
    print(f"{'ceiling (measured)':<34} {ceiling['f1']:>10.3f} {1.0:>9.1%} "
          f"{ceiling['precision']:>6.1%} {ceiling['recall']:>6.1%}")

    learned = rows["v3  best learned rung"]["unseen"]["f1"]
    zero = rows["v4  gazetteer only (ZERO-SHOT)"]["unseen"]["f1"]
    both = rows["v5  v3 + gazetteer"]["unseen"]["f1"]
    print(f"\nzero-shot registry alone reaches {zero:.3f} against the best "
          f"learned rung's {learned:.3f} "
          f"({'BETTER' if zero > learned else 'worse'}, {zero-learned:+.3f}), "
          f"using no training data at all")
    print(f"registry + learned statistics: {both:.3f}, "
          f"{both/ceiling['f1']:.1%} of the ceiling "
          f"({both-learned:+.3f} over learned alone)")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "seed": SEED, "source": str(SRC), "ror": str(ROR),
        "gazetteer": {"orgs": gz.n_orgs, "names": gz.n_names,
                      "distinct_normalised": len(gz.by_name),
                      "ambiguous": amb},
        "ceiling": ceiling, "rungs": rows,
        "n_unseen": len(unseen), "n_all": len(pairs)}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
