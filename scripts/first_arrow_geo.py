"""Two views over one candidate set: names propose, geography disposes.

`notes/findings/2026-08-18-a-zero-shot-registry-beats-a-learned-dictionary-and-both-plateau-at-62-percent.md`
diagnosed the extraction residual and the diagnosis is not what the six rungs
before it were built for:

* **one** string in 6,489 produced no candidate at all;
* 38.2% of true institutions are never proposed, because a **near-identical
  sibling** was proposed instead;
* "University of Wisconsin" names thirteen ROR campuses, and the string carries
  exactly what separates them — *Madison*, *Lancaster*, *Karlsruhe*.

So the failure is **choosing**, not finding, and the discriminating evidence is
geography sitting unread in the input. ROR ships `city`, `country_subdivision`
and `country` per organization.

This is built deliberately as a **composition** rather than as a better matcher,
because that is the claim being tested:

    NAME view      proposes every ROR id whose registry name matches a
                   component — *including the ambiguous ones that v4–v6 threw
                   away by abstaining*, which is where the recall went.
    GEO view       disposes, by scoring each candidate's recorded location
                   against the places named in the same string.

One view's result changes what the other does. That is the multi-kernel claim on
a problem that needs it, rather than on one arranged to need it.

**The control that decides whether this is a composition or a decoration:** how
often geography *overrides* the name view's own first choice, and how often it is
**right** when it does. A view that changes many answers and is no better than
chance on them is decoration, and this repo has published decoration before.

Run: SYMBOLIC_AI_PROSE_SNAPSHOT=openalex-prose-2026-08-18-authorship \\
     uv run python -u scripts/first_arrow_geo.py
"""

from __future__ import annotations

import json
import random
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable

from scripts.first_arrow_gazetteer import ROR, SAFE_TYPES, expand, v6
from scripts.first_arrow_ladder import Index, measure_ceiling, v3
from scripts.first_arrow_prose import (TRAIN_FRAC, components, load, norm,
                                       score)

OUT = Path("runs/first_arrow_geo.json")
SEEDS = (20260818, 777001, 1234567)


class GeoGazetteer:
    """Registry names, and where each organization actually is."""

    def __init__(self, path: Path) -> None:
        self.by_name: dict[str, set[str]] = defaultdict(set)
        self.by_acronym: dict[str, set[str]] = defaultdict(set)
        self.by_token: dict[str, set[str]] = defaultdict(set)
        self._name_tokens: dict[str, frozenset[str]] = {}
        #: ror id -> the normalised place words that identify it
        self.places: dict[str, set[str]] = {}
        self._cities: dict[str, set[str]] = {}
        self._subs: dict[str, set[str]] = {}
        self._countries: dict[str, set[str]] = {}
        self.n_orgs = 0
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
                types = set(n["t"])
                if types & SAFE_TYPES:
                    self.by_name[v].add(org["id"])
                    tk = frozenset(v.split())
                    self._name_tokens[v] = tk
                    for t in tk:
                        self.by_token[t].add(v)
                if "acronym" in types:
                    self.by_acronym[v].add(org["id"])
            place: set[str] = set()
            for loc in (org.get("loc") or []):
                for key in ("city", "sub", "country"):
                    val = norm(loc.get(key) or "")
                    if val:
                        place.add(val)
                cc = norm(loc.get("cc") or "")
                sc = norm(loc.get("subcode") or "")
                # Subdivision codes arrive as "US-WI"; the useful half is "wi".
                for code in (cc, sc.split(" ")[-1] if sc else ""):
                    if code:
                        place.add(code)
            self.places[org["id"]] = place
            self._cities[org["id"]] = {norm(l.get("city") or "")
                                       for l in (org.get("loc") or [])
                                       if l.get("city")}
            self._subs[org["id"]] = {v for l in (org.get("loc") or [])
                                     for v in (norm(l.get("sub") or ""),
                                               norm((l.get("subcode") or "").split("-")[-1]))
                                     if v}
            self._countries[org["id"]] = {v for l in (org.get("loc") or [])
                                          for v in (norm(l.get("country") or ""),
                                                    norm(l.get("cc") or ""))
                                          if v}

    def phrase_match(self, phrase: str) -> set[str]:
        """Registry names contained in the WHOLE string, longest first.

        Component matching fails in a way the silent tier made visible: ROR's
        canonical name for Purdue's main campus is "Purdue University West
        Lafayette", the affiliation component is "Purdue University", and
        `_contained` asks whether the registry name's tokens are a subset of the
        *component's* — which they are not, because the city that completes the
        name sits three components later in the same string. Matching against
        the whole phrase asks the question the other way round and recovers
        35.9% of the silent tier.
        """
        toks = set(phrase.split())
        # Candidates come through the rarest token that ANY registry name
        # contains. Picking the rarest token outright -- which the component
        # version does -- lands on a postcode or a street number in a long
        # address, `by_token` has no entry for it, and the lookup returns
        # nothing. That alone left 188 of the 287 recoverable silent strings
        # still silent after the first attempt at this fix.
        known = [t for t in toks if t in self.by_token]
        if not known:
            return set()
        # Candidates through the K RAREST known tokens, not one. Going through a
        # single token requires the gold name to contain THAT token, and it
        # usually does not: the rarest known token in "Departments of
        # Epidemiology and Biostatistics, University of California, San
        # Francisco" is "departments", while the answer is "university of
        # california san francisco". Measured: that alone accounted for 28.2% of
        # the strings still falling silent after the phrase fallback was added.
        known.sort(key=lambda t: len(self.by_token[t]))
        best: tuple[int, set[str]] = (0, set())
        seen: set[str] = set()
        for t in known[:8]:
            for name in self.by_token[t]:
                if name in seen:
                    continue
                seen.add(name)
                nt = self._name_tokens[name]
                if len(nt) >= 2 and nt <= toks and len(nt) > best[0]:
                    best = (len(nt), set(self.by_name[name]))
        return best[1]

    # -- the NAME view ---------------------------------------------------
    def propose(self, raw: str) -> list[set[str]]:
        """One candidate set per component. Ambiguity is KEPT, not discarded.

        v4–v6 returned only components that named exactly one institution and
        abstained on the rest. That abstention is precisely the recall this is
        trying to recover, so the ambiguous sets come through and the geo view
        is asked to settle them.
        """
        out: list[set[str]] = []
        for c0 in components(raw):
            c = expand(c0)
            hits = self.by_name.get(c) or self.by_name.get(c0) or set()
            if not hits:
                hits = self._contained(c)
            if not hits:
                hits = self.by_acronym.get(c0, set())
            if hits:
                out.append(set(hits))
        if not out:
            # Nothing matched component-wise. Before falling silent -- which is
            # the tier that sets `f`, and therefore the price -- ask the whole
            # string.
            whole = self.phrase_match(norm(raw))
            if whole:
                out.append(whole)
        return out

    # The three the earlier rungs call. GeoGazetteer builds the same indexes as
    # `Gazetteer` plus locations, so v6 can run against it unchanged and the
    # comparison is between VIEWS rather than between two different gazetteers.
    def lookup(self, component: str) -> set[str]:
        return self.by_name.get(component, set())

    def lookup_acronym(self, component: str) -> set[str]:
        hits = self.by_acronym.get(component, set())
        return hits if len(hits) == 1 else set()

    def contained_in(self, component: str) -> set[str]:
        got = self._contained(component)
        return got if len(got) == 1 else set()

    def _contained(self, component: str) -> set[str]:
        toks = set(component.split())
        if not toks:
            return set()
        rare = min(toks, key=lambda t: len(self.by_token.get(t, ())) or 10**9)
        best: tuple[int, set[str]] = (0, set())
        for name in self.by_token.get(rare, ()):
            nt = self._name_tokens[name]
            if len(nt) >= 2 and nt <= toks and len(nt) > best[0]:
                best = (len(nt), set(self.by_name[name]))
        return best[1]

    # -- the GEO view ----------------------------------------------------
    def geo_score(self, ror: str, said: set[str], phrase: str) -> int:
        """How much of this organization's recorded location the string names."""
        place = self.places.get(ror) or set()
        if not place:
            return 0
        hits = len(place & said)
        # Multi-word places ("new south wales", "rio de janeiro") never appear
        # as single tokens, so check them as phrases too.
        hits += sum(1 for p in place if " " in p and p in phrase)
        return hits

    def geo_strength(self, ror: str, said: set[str], phrase: str) -> int:
        """Graded evidence: a city is worth far more than a country.

        Flat overlap counts "usa" the same as "madison", and every US
        institution matches "usa" — which is why the first version of this view
        scored as decoration. The grade is 3 for a city, 2 for a subdivision,
        1 for a country, and the admission rule below requires at least 2.
        """
        best = 0
        for kind, weight in ((self._cities, 3), (self._subs, 2),
                             (self._countries, 1)):
            for p in kind.get(ror, ()):  # type: ignore[union-attr]
                if p in said or (" " in p and p in phrase):
                    best = max(best, weight)
        return best


def v7(gz: GeoGazetteer, ix: Index, raw: str, *, stats: Counter | None = None
       ) -> set[str]:
    """Names propose, geography disposes, training frequency breaks the ties."""
    hit = ix.full.get(norm(raw))
    if hit:
        return set(hit)
    phrase = norm(raw)
    said = set(phrase.split())
    out: set[str] = set()
    for cands in gz.propose(raw):
        if len(cands) == 1:
            out |= cands
            continue
        if stats is not None:
            stats["ambiguous_components"] += 1
        scored = [(gz.geo_score(r, said, phrase), r) for r in cands]
        best = max(s for s, _ in scored)
        if best == 0:
            # Geography says nothing. Fall back to what the name view alone
            # would have done, which is to abstain rather than guess.
            if stats is not None:
                stats["geo_silent"] += 1
            continue
        winners = [r for s, r in scored if s == best]
        if len(winners) == 1:
            if stats is not None:
                stats["geo_decided"] += 1
            out.add(winners[0])
        else:
            # Still tied after geography: let training frequency choose among
            # the survivors, and abstain if it has nothing to say either.
            votes = ix.comp.get("", Counter())
            ranked = [(sum(ix.comp.get(c, Counter()).get(r, 0)
                           for c in components(raw)), r) for r in winners]
            top = max(ranked)
            if top[0] > 0:
                if stats is not None:
                    stats["freq_broke_geo_tie"] += 1
                out.add(top[1])
            elif stats is not None:
                stats["still_tied"] += 1
    return out or v6(ix, gz, raw)          # type: ignore[arg-type]


def v8(gz: GeoGazetteer, ix: Index, raw: str, *, stats: Counter | None = None
       ) -> set[str]:
    """v6's abstention, kept — geography may only ADMIT, never relax.

    The ablation that produced this: relaxing abstention costs -0.036 and
    geography recovers +0.029 of it, so the view is informative and cannot pay
    for the permission it was given. So take the permission back. v6 abstains on
    an ambiguous component; here geography may overrule that abstention **only**
    when it names a unique winner on CITY or SUBDIVISION evidence — never on a
    country, which every institution in a country matches.
    """
    base = v6(ix, gz, raw)                 # type: ignore[arg-type]
    phrase = norm(raw)
    said = set(phrase.split())
    extra: set[str] = set()
    for cands in gz.propose(raw):
        if len(cands) <= 1 or cands & base:
            continue                        # v6 already committed here
        scored = [(gz.geo_strength(r, said, phrase), r) for r in cands]
        best = max(s for s, _ in scored)
        if best < 2:                        # country-only evidence is not evidence
            if stats is not None:
                stats["refused_weak_evidence"] += 1
            continue
        winners = [r for s, r in scored if s == best]
        if len(winners) == 1:
            if stats is not None:
                stats["admitted_on_city_or_region"] += 1
            extra.add(winners[0])
        elif stats is not None:
            stats["still_tied"] += 1
    return base | extra


def main() -> None:
    print(f"loading {ROR} ...", flush=True)
    t0 = time.perf_counter()
    gz = GeoGazetteer(ROR)
    placed = sum(1 for v in gz.places.values() if v)
    print(f"  {gz.n_orgs:,} active organizations, {placed:,} "
          f"({placed/gz.n_orgs:.1%}) carry a location "
          f"({time.perf_counter()-t0:.0f}s)", flush=True)

    works = load()
    hdr = (f"{'seed':>9} {'rung':<26} {'F1 unseen':>10} {'% ceil':>8} "
           f"{'prec':>7} {'rec':>7}")
    print()
    print(hdr)
    print("-" * len(hdr))
    rows: list[dict[str, Any]] = []
    for seed in SEEDS:
        rng = random.Random(seed)
        idx = list(range(len(works)))
        rng.shuffle(idx)
        cut = int(len(idx) * TRAIN_FRAC)
        ix = Index([works[i] for i in idx[:cut]])
        test = [works[i] for i in idx[cut:]]
        pairs = [(a["raw"], set(a["rors"])) for w in test
                 for a in w["affiliations"] if a["rors"]]
        unseen = [p for p in pairs if norm(p[0]) not in ix.full]
        ceil = measure_ceiling(ix, pairs)["f1"]
        stats: Counter = Counter()
        for name, fn in (("v6  names only", lambda r: v6(ix, gz, r)),
                         ("v7  relaxed + geography",
                          lambda r: v7(gz, ix, r, stats=stats)),
                         ("v8  v6 + geo may only ADMIT",
                          lambda r: v8(gz, ix, r, stats=stats))):
            u = score([(fn(raw), t) for raw, t in unseen])
            rows.append({"seed": seed, "rung": name, "ceiling": ceil, **u})
            print(f"{seed:>9} {name:<26} {u['f1']:>10.3f} {u['f1']/ceil:>7.1%} "
                  f"{u['precision']:>6.1%} {u['recall']:>6.1%}")
        print(f"{'':>9} {'  geo view fired on':<26} "
              f"{stats['ambiguous_components']:,} ambiguous components: "
              f"decided {stats['geo_decided']:,}, silent "
              f"{stats['geo_silent']:,}, tie broken by frequency "
              f"{stats['freq_broke_geo_tie']:,}")

    # --- the control: is geography choosing, or decorating?
    print("\ncontrol — when the two views DISAGREE, which one is right?",
          flush=True)
    rng = random.Random(SEEDS[0])
    idx = list(range(len(works)))
    rng.shuffle(idx)
    cut = int(len(idx) * TRAIN_FRAC)
    ix = Index([works[i] for i in idx[:cut]])
    test = [works[i] for i in idx[cut:]]
    pairs = [(a["raw"], set(a["rors"])) for w in test
             for a in w["affiliations"] if a["rors"]]
    unseen = [p for p in pairs if norm(p[0]) not in ix.full]
    changed = geo_right = name_right = both_wrong = 0
    for raw, truth in unseen:
        a, b = v6(ix, gz, raw), v7(gz, ix, raw)
        if a == b:
            continue
        changed += 1
        ja = len(a & truth) / max(1, len(a | truth))
        jb = len(b & truth) / max(1, len(b | truth))
        if jb > ja:
            geo_right += 1
        elif ja > jb:
            name_right += 1
        else:
            both_wrong += 1
    print(f"  geography changed the answer on {changed:,}/{len(unseen):,} "
          f"({changed/len(unseen):.1%}) of unseen strings")
    if changed:
        print(f"  and it was BETTER on {geo_right:,} ({geo_right/changed:.1%}), "
              f"worse on {name_right:,} ({name_right/changed:.1%}), "
              f"neither on {both_wrong:,} ({both_wrong/changed:.1%})")
        print(f"  verdict: {'a composition' if geo_right > 2*name_right else 'DECORATION — it changes answers without improving them'}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"rows": rows, "ror": str(ROR),
                               "control": {"changed": changed,
                                           "geo_better": geo_right,
                                           "name_better": name_right,
                                           "neither": both_wrong,
                                           "n_unseen": len(unseen)}}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
