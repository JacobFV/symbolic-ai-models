"""Cluster the languages by what each rule is worth in them, and test the shape.

The prediction this answers is stated in
``notes/questions/2026-08-13-selective-rule-application-by-language.md``: a rule
reliable in every language is universal, a rule reliable only in a subset is
family-specific, so **clustering languages by their per-rule reliability vectors
should recover real language families** — and if it does not, the rules are
being fitted per language independently and conditioning bought nothing that
bucketing would not.

Run it against a finished `omegaclaw_textlang-002`::

    uv run python scripts/language_clustering.py runs/full179_multilingual/omegaclaw_textlang-002

Three things it will not let you get away with
----------------------------------------------
**It re-derives the table and then checks the re-derivation.** The vectors need
per-language *denominators*, which the shipped ``claw_evidence`` does not carry
— it holds ``(fired, right)`` and not "how many nodes were asked about". So the
observation pass is run again here. A second implementation of a fitted model's
statistics is exactly the kind of scratch script this repo has twice had
contradict the sweep, so the re-derivation is asserted to reproduce
``model.claw_evidence`` cell for cell before anything is computed from it. If
that assertion fails the script refuses to print numbers.

**The shuffle control is exact, not resampled.** Shuffling the language labels
does not change which claws fired on which node — it changes only which bucket
each episode's records land in. So one observation pass is taken, records are
tagged with their episode, and the permutations re-bucket them. That makes a
thousand controls cost what one costs, and makes every control run against
*identical* observations rather than merely comparable ones.

**It separates the dimensions that can carry a signal from the ones that
cannot.** ``Lesson.structured`` takes no language: the term graph is
byte-identical across all seven packs, so the eleven graph claws must have the
same reliability everywhere by construction, and every scrap of between-language
variance has to come from the three claws that read the prose. The report prints
that split. A clustering whose variance lives in the graph dimensions would mean
the harness is leaking something, not that grammar was learned.
"""

from __future__ import annotations

import argparse
import collections
import itertools
import json
import math
import sys
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np

#: Genealogy, for the six natural packs. `symbols` is a formal notation and is
#: excluded from the family test, though it is kept in the clustering because
#: where a notation lands is informative about what the vectors encode.
#:
#: This is a thin basis for a family claim and the thinness is the point:
#: `symbolic_ai_data` renders five natural languages, one of which
#: (`english_synonym`) is English again. That is **one** family with more than
#: one member. The test below is therefore reported as a rank among the twenty
#: possible triples rather than dressed up as a p-value.
FAMILY = {
    "english": "Indo-European",
    "english_synonym": "Indo-European",
    "spanish": "Indo-European",
    "chinese": "Sino-Tibetan",
    "turkish": "Turkic",
    "swahili": "Atlantic-Congo",
    "symbols": "(not a natural language)",
}


# ---------------------------------------------------------------------------
# observation
# ---------------------------------------------------------------------------
def observe(model, episodes, tok, max_nodes: int
            ) -> tuple[list[tuple[int, tuple[str, ...]]], list[str]]:
    """``(episode index, claws that were right / that fired)`` per asked node.

    Mirrors :meth:`OmegaClaw._observe` — same views, same seed, same example cap
    — but keeps the episode each record came from instead of the context key,
    which is what makes the permutation control possible. The return is a list of
    ``(episode_index, fired_names, right_names)`` flattened into two aligned
    tuples per record, plus the language of every episode.
    """
    from symbolic_ai_models.models.omegaclaw import Scan

    claws = model.claws()
    languages = [ep.language for ep in episodes]
    records: list[tuple[int, tuple[str, ...], tuple[str, ...]]] = []
    seen = 0
    for view, targets, index in model.training_views(
            episodes, tok, max_nodes=max_nodes, with_index=True):
        scan = Scan(view)
        for node, (label_id, _) in targets.items():
            if label_id < 0 or seen >= model.max_examples:
                continue
            seen += 1
            fired: list[str] = []
            right: list[str] = []
            for name, claw in claws.items():
                claim = claw(scan, node)
                if claim is None:
                    continue
                fired.append(name)
                if claim.symbol == label_id:
                    right.append(name)
            if fired:
                records.append((index, tuple(fired), tuple(right)))
    return records, languages


def tally(records, languages: Sequence[str], assignment: Sequence[str]
          ) -> tuple[dict[str, int], dict[tuple[str, str], list[int]]]:
    """``(records per language, (language, claw) -> [fired, right])``.

    ``assignment`` is the language attributed to each episode, which is
    ``languages`` for the real table and a permutation of it for a control.
    """
    asked: dict[str, int] = collections.Counter()
    cells: dict[tuple[str, str], list[int]] = {}
    for index, fired, right in records:
        lang = assignment[index]
        asked[lang] += 1
        for name in fired:
            cells.setdefault((lang, name), [0, 0])[0] += 1
        for name in right:
            cells[(lang, name)][1] += 1
    return dict(asked), cells


def vectors(asked, cells, langs: Sequence[str], claws: Sequence[str]) -> np.ndarray:
    """One row per language: every claw's firing rate, then its hit rate.

    Both, rather than the hit rate alone, because *whether a rule applies here*
    is as much a fact about a language as *whether it is right when it does*.
    The surface claws refuse to fire when the prose names none of the candidate
    nodes, so in Chinese they are mostly silent — and silence is the strongest
    single thing this corpus knows about Chinese.
    """
    rows = []
    for lang in langs:
        n = max(asked.get(lang, 0), 1)
        fire = [cells.get((lang, c), (0, 0))[0] / n for c in claws]
        hit = [cells.get((lang, c), (0, 0))[1] / max(cells.get((lang, c), (0, 0))[0], 1)
               for c in claws]
        rows.append(fire + hit)
    return np.asarray(rows, dtype=float)


# ---------------------------------------------------------------------------
# clustering, by hand: seven points do not justify a dependency
# ---------------------------------------------------------------------------
def distances(vecs: np.ndarray) -> np.ndarray:
    diff = vecs[:, None, :] - vecs[None, :, :]
    return np.sqrt((diff ** 2).sum(-1))


def average_linkage(dist: np.ndarray, names: Sequence[str]) -> list[str]:
    """A text dendrogram, merging the closest pair of clusters each round."""
    clusters = {i: [n] for i, n in enumerate(names)}
    members = {i: [i] for i in range(len(names))}
    lines: list[str] = []
    while len(clusters) > 1:
        best, best_d = None, math.inf
        for a, b in itertools.combinations(sorted(clusters), 2):
            d = float(np.mean([dist[i, j] for i in members[a] for j in members[b]]))
            if d < best_d:
                best, best_d = (a, b), d
        a, b = best                                       # type: ignore[misc]
        lines.append(f"  {best_d:7.4f}   {'+'.join(clusters[a])} | {'+'.join(clusters[b])}")
        clusters[a] = clusters[a] + clusters[b]
        members[a] = members[a] + members[b]
        del clusters[b], members[b]
    return lines


def within(dist: np.ndarray, names: Sequence[str], group: Iterable[str]) -> float:
    idx = [names.index(g) for g in group]
    pairs = [dist[i, j] for i, j in itertools.combinations(idx, 2)]
    return float(np.mean(pairs)) if pairs else math.nan


# ---------------------------------------------------------------------------
def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("run", help="a finished omegaclaw_textlang-002 run directory")
    ap.add_argument("--shuffles", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", help="write the numbers here as JSON")
    args = ap.parse_args(argv)

    from symbolic_ai_models.models.omegaclaw import CLAWS, SURFACE_CLAWS
    from symbolic_ai_models.train import load_data, load_run

    model, tok, cfg = load_run(args.run)
    train_eps, _ = load_data(cfg)
    print(f"{args.run}: {model.name}, {len(train_eps)} training episodes, "
          f"max_examples={model.max_examples}", flush=True)

    records, languages = observe(model, train_eps, tok, model.cfg.max_nodes)
    langs = sorted(set(languages))
    claws = list(model.claws())
    asked, cells = tally(records, languages, languages)
    print(f"{len(records)} records over {len(langs)} languages: "
          + ", ".join(f"{l}={asked.get(l, 0)}" for l in langs), flush=True)

    # --- the guard: this must be the model's own table -------------------
    # Only a model whose context key *starts* with the language can be checked
    # this way. Running against `omegaclaw_text-002` is legitimate — the same
    # clustering, from a model that was never told the language — and there the
    # marginal is simply not recoverable from `claw_evidence`, so the guard
    # steps aside and says so rather than checking something else.
    keyed_by_language = all(isinstance(ctx, tuple) and ctx and ctx[0] in set(langs)
                            for ctx, _ in model.claw_evidence)
    if keyed_by_language and model.claw_evidence:
        rebuilt: dict[tuple[str, str], list[float]] = {}
        for (ctx, name), (fired, right) in model.claw_evidence.items():
            key = (ctx[0], name)
            cell = rebuilt.setdefault(key, [0.0, 0.0])
            cell[0] += fired
            cell[1] += right
        mismatch = [k for k in set(rebuilt) | set(cells)
                    if [float(v) for v in cells.get(k, [0, 0])]
                    != [float(v) for v in rebuilt.get(k, [0, 0])]]
        if mismatch:
            print(f"REFUSING: re-derived table disagrees with the fitted model in "
                  f"{len(mismatch)} cells, e.g. {mismatch[:3]}", file=sys.stderr)
            return 1
        print("re-derivation reproduces model.claw_evidence exactly", flush=True)
    else:
        print("note: this model does not key on language, so the re-derivation "
              "cannot be checked against its own table", flush=True)

    vecs = vectors(asked, cells, langs, claws)
    dist = distances(vecs)

    print("\nper-claw firing rate (top) and hit rate (bottom), by language")
    surface = set(SURFACE_CLAWS)
    for kind, offset in (("fire", 0), ("hit", len(claws))):
        print(f"\n  {kind:<5}" + "".join(f"{c[:9]:>10}" for c in claws))
        for i, lang in enumerate(langs):
            print(f"  {lang[:14]:<16}" + "".join(
                f"{vecs[i, offset + j]:>10.3f}" for j in range(len(claws))))

    # --- where the between-language variance actually lives ---------------
    var = vecs.var(axis=0)
    graph_dims = [j for j, c in enumerate(claws * 2) if c not in surface]
    surf_dims = [j for j, c in enumerate(claws * 2) if c in surface]
    total = float(var.sum())
    print(f"\nbetween-language variance: "
          f"graph claws {float(var[graph_dims].sum()) / max(total, 1e-12):.4%}, "
          f"surface claws {float(var[surf_dims].sum()) / max(total, 1e-12):.4%}")

    print("\npairwise distance")
    print("  " + " " * 16 + "".join(f"{l[:9]:>10}" for l in langs))
    for i, lang in enumerate(langs):
        print(f"  {lang[:14]:<16}" + "".join(f"{dist[i, j]:>10.3f}" for j in range(len(langs))))

    print("\nnearest neighbour")
    for i, lang in enumerate(langs):
        order = np.argsort(dist[i])
        near = [langs[j] for j in order if j != i][0]
        print(f"  {lang:<16} -> {near:<16} ({dist[i, langs.index(near)]:.3f})"
              f"   [{FAMILY.get(lang, '?')} -> {FAMILY.get(near, '?')}]")

    print("\naverage-linkage dendrogram (merge distance, then the two clusters)")
    for line in average_linkage(dist, langs):
        print(line)

    # --- control: is there any language signal at all? --------------------
    rng = np.random.default_rng(args.seed)
    real_spread = float(np.mean(dist[np.triu_indices(len(langs), 1)]))
    shuffled: list[float] = []
    for _ in range(args.shuffles // 20 or 1):
        perm = list(rng.permutation(languages))
        a, c = tally(records, languages, perm)
        shuffled.append(float(np.mean(
            distances(vectors(a, c, langs, claws))[np.triu_indices(len(langs), 1)])))
    shuffled_arr = np.asarray(shuffled)
    print(f"\ncontrol: mean pairwise distance")
    print(f"  real                {real_spread:.4f}")
    print(f"  language labels shuffled  {shuffled_arr.mean():.4f} "
          f"+- {shuffled_arr.std():.4f}   (n={len(shuffled_arr)}, "
          f"max {shuffled_arr.max():.4f})")
    print(f"  ratio               {real_spread / max(shuffled_arr.mean(), 1e-12):.1f}x")

    # --- does the shape match genealogy? ----------------------------------
    natural = [l for l in langs if FAMILY.get(l, "").startswith(("Indo", "Sino",
                                                                "Turkic", "Atlantic"))]
    nd = distances(vecs[[langs.index(l) for l in natural]])
    ie = [l for l in natural if FAMILY[l] == "Indo-European"]
    triples = list(itertools.combinations(natural, len(ie)))
    scores = sorted((within(nd, natural, t), t) for t in triples)
    rank = [t for _, t in scores].index(tuple(ie)) + 1
    print(f"\ngenealogy: the one family with more than one member is "
          f"Indo-European = {ie}")
    print(f"  its mean within-family distance ranks {rank} of {len(triples)} "
          f"triples (1 = tightest)")
    for d, t in scores[:5]:
        mark = " <-- the real family" if tuple(t) == tuple(ie) else ""
        print(f"  {d:7.4f}  {'+'.join(t)}{mark}")

    if args.out:
        Path(args.out).write_text(json.dumps({
            "run": args.run, "languages": langs, "claws": claws,
            "vectors": vecs.tolist(), "distance": dist.tolist(),
            "asked": asked,
            "variance_share_surface": float(var[surf_dims].sum()) / max(total, 1e-12),
            "real_spread": real_spread,
            "shuffled_spread_mean": float(shuffled_arr.mean()),
            "shuffled_spread_max": float(shuffled_arr.max()),
            "genealogy_rank": rank, "genealogy_of": len(triples),
        }, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
