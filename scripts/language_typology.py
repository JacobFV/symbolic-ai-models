"""Grade the induced language representation against WALS, and against script.

``scripts/language_clustering.py`` asked whether the languages cluster by
descent and answered it against a four-point genealogy hand-typed into its own
source. This asks the same question against
`site-languages.db` — 640 rows of WALS coding over 46 languages, `family`,
`macroarea` and `script` per language, none of it written for this repo.

Run it against a finished ``omegaclaw_textlang-002``::

    uv run python scripts/language_typology.py runs/full179_wals42/omegaclaw_textlang-002 \\
        --out runs/full179_wals42/typology.json

The design, and the four things it refuses to let you get away with, are in
``notes/decisions/2026-08-13-typology-oracle-preregistration.md``. The ones that
live in this file:

**The generator is a function of the oracle, so the oracle is split in two.**
``symbolic_ai_data/grammar/typology.py::derive_profile`` builds a derived
grammar's word order out of WALS. Recovering *those* features from *that*
grammar's prose is arithmetic, not a finding. So every correlation is reported
twice: against the 14 features the renderer consumes (``T_read``, a positive
control) and against the 4 it never reads (``T_heldout``, the honest test).
Getting this backwards would turn a tautology into a headline.

**Two representations, not one.** ``R_claw`` is the incumbent — the fourteen
claws' per-language firing and hit rates, re-derived here and asserted equal to
the fitted model's own ``claw_evidence`` before anything is computed from it.
``R_order`` is the proposal: which of two graph nodes the prose mentions first,
per structural relation. The graph is byte-identical across languages, so that
quantity is a direct measurement of linearisation and nothing else.

**Distance-matrix entries are not independent.** Every p-value here is a Mantel
permutation over the language labels, rows and columns together. A Spearman
rho over 528 correlated pairs with a t-test p-value would read as decisive at
almost any effect size, and is not computed.

**Script is controlled for twice, once binary and once measured.** Same script
or not is the crude version. The graded version is each language's *verbatim
label rate* — the share of graph labels that survive into its prose — which is
what the previous clustering turned out to have recovered. A typological
correlation that dies under the graded control was orthography.
"""

from __future__ import annotations

import argparse
import collections
import functools
import itertools
import json
import math
import re
import sys
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

#: Languages whose ISO code is shadowed by a verified hand-written grammar.
#: Rendering four of the forty-six through a different pipeline would put a
#: pipeline difference inside the distance matrix. See the config header.
SHADOWED = frozenset({"spa", "tur", "swh", "cmn"})

#: The coding thresholds that decide which languages the *correlations* run on.
#: Fixed before any correlation existed; the languages they drop are dropped for
#: thin WALS rows, never for their score, and they stay in the signal test and
#: the dendrogram.
MIN_READ_FEATURES = 8
MIN_HELDOUT_FEATURES = 2

#: A relation must be observed this often in **every** language to enter
#: ``R_order``. Uniform support across languages is what stops per-language
#: coverage — which is orthography — leaking in as an imputed value.
MIN_KEY_SUPPORT = 30

#: The subset of the renderer-read features that code **linear order**, which
#: is the only thing ``R_order`` can possibly carry. Reported separately from
#: the full read set, which also contains gender counts, article inventories,
#: classifiers and case alignment — facts a linearisation vector has no channel
#: for, and which therefore only dilute the positive control.
ORDER_WALS_FEATURES = ("81A", "87A", "85A", "86A", "88A", "89A", "93A", "143A")


# ---------------------------------------------------------------------------
# R_order: which of two nodes the prose mentions first
# ---------------------------------------------------------------------------
@functools.lru_cache(maxsize=4096)
def _matcher(words: tuple[str, ...], boundary: bool) -> "re.Pattern[str]":
    """One alternation over a label set, compiled once per label set.

    The same seed and lesson produce the **same graph** in all 42 languages, so
    without this cache the pattern for a given episode is compiled 42 times.
    Longest first, so ``o1`` cannot win inside ``o10``.
    """
    body = "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True))
    return re.compile((r"\b(" + body + r")\b") if boundary else body, re.IGNORECASE)


def _first_positions(prompt: str, labels: Iterable[str], *, boundary: bool = False
                     ) -> dict[str, int]:
    """First offset of each label in the prompt, longest match first.

    **No word boundary by default.** ``Surface`` in the model uses ``\\b``, and
    Python's ``\\b`` never fires between an ASCII identifier and a CJK
    character — which is the entire reason Chinese sat at a 0.285 verbatim rate
    and the whole previous clustering came out orthographic. Requiring a
    boundary inside ``R_order`` would guarantee the order representation is
    orthographic too and make the comparison between the two vacuous.
    ``boundary=True`` reproduces the model's own gate, which is what
    :func:`verbatim_rates` measures.
    """
    words = tuple(sorted({w for w in labels if len(w) >= 2}))
    if not words or not prompt:
        return {}
    out: dict[str, int] = {}
    for match in _matcher(words, boundary).finditer(prompt):
        out.setdefault(match.group(0).lower(), match.start())
    return out


def _order_records(episodes: Sequence) -> tuple[np.ndarray, np.ndarray, np.ndarray,
                                                list[tuple], list[str]]:
    """``(episode index, relation id, first-node-came-first)`` per ordered pair.

    Returned as three parallel integer arrays plus the key table, rather than a
    list of tuples: the full corpus yields several million records and the
    signal control re-buckets all of them a hundred times, which is a
    ``np.bincount`` and not a Python loop.

    Two relation families, both defined on the graph alone so that the *set* of
    keys is identical in every language and only the answers move:

    * ``("pc", parent type, child type, child slot)`` — does the head precede
      its dependent;
    * ``("sib", parent type, earlier-slot type, later-slot type, both slots)`` —
      do two dependents of one head come out in slot order.

    Pairs whose two nodes share a label are skipped: they share a first mention,
    so they carry no order information at all.
    """
    key_id: dict[tuple, int] = {}
    idx_out: list[int] = []
    key_out: list[int] = []
    before_out: list[int] = []
    languages: list[str] = []
    for index, ep in enumerate(episodes):
        languages.append(ep.language)
        g = ep.graph
        found = _first_positions(ep.prompt, (l for l in g.labels if l))
        pos = [found.get((g.labels[i] or "").lower()) for i in range(len(g))]
        kids: dict[int, list[int]] = {}
        for i, p in enumerate(g.parent):
            if p >= 0:
                kids.setdefault(p, []).append(i)
        for p, children in kids.items():
            tp = g.types[p] or "?"
            if pos[p] is not None:
                for c in children:
                    if pos[c] is None or pos[c] == pos[p]:
                        continue
                    key = ("pc", tp, g.types[c] or "?", min(g.slot[c], 6))
                    k = key_id.setdefault(key, len(key_id))
                    idx_out.append(index)
                    key_out.append(k)
                    before_out.append(pos[p] < pos[c])
            ordered = sorted(children, key=lambda c: (g.slot[c], c))
            for a, b in itertools.combinations(ordered, 2):
                if pos[a] is None or pos[b] is None or pos[a] == pos[b]:
                    continue
                key = ("sib", tp, g.types[a] or "?", g.types[b] or "?",
                       min(g.slot[a], 6), min(g.slot[b], 6))
                k = key_id.setdefault(key, len(key_id))
                idx_out.append(index)
                key_out.append(k)
                before_out.append(pos[a] < pos[b])
    table = [k for k, _ in sorted(key_id.items(), key=lambda kv: kv[1])]
    return (np.asarray(idx_out, dtype=np.int32),
            np.asarray(key_out, dtype=np.int32),
            np.asarray(before_out, dtype=np.int8), table, languages)


def order_vectors(records, langs: Sequence[str], assignment: Sequence[str],
                  columns: Sequence[int] | None = None,
                  min_support: int = MIN_KEY_SUPPORT
                  ) -> tuple[np.ndarray, list[int]]:
    """One row per language: P(first node mentioned first), per relation.

    ``columns`` fixes the relations; when ``None`` they are chosen as every
    relation with ``min_support`` observations in **every** language — uniform
    support, so no cell is imputed and per-language coverage (which is
    orthography) cannot enter through the back door.
    """
    idx, key, before, table, _ = records
    where = {l: i for i, l in enumerate(langs)}
    lang_of = np.fromiter((where[l] for l in assignment), dtype=np.int32,
                          count=len(assignment))
    n_keys, n_langs = len(table), len(langs)
    cell = lang_of[idx] * n_keys + key
    total = np.bincount(cell, minlength=n_langs * n_keys).reshape(n_langs, n_keys)
    hits = np.bincount(cell, weights=before.astype(np.float64),
                       minlength=n_langs * n_keys).reshape(n_langs, n_keys)
    if columns is None:
        columns = [int(c) for c in np.flatnonzero(total.min(axis=0) >= min_support)]
    cols = list(columns)
    with np.errstate(invalid="ignore", divide="ignore"):
        rate = np.where(total[:, cols] > 0, hits[:, cols] / total[:, cols], 0.5)
    return rate, cols


def verbatim_rates(episodes: Iterable, langs: Sequence[str]) -> dict[str, float]:
    """Share of graph labels appearing verbatim in the prose, per language.

    The measured orthographic confound: this column is what the previous
    clustering turned out to be monotone in. Computed with the model's own
    ``\\b``-gated matching, because that is the gate whose failure the column
    describes.
    """
    hit: dict[str, list[int]] = {l: [0, 0] for l in langs}
    for ep in episodes:
        if ep.language not in hit:
            continue
        cell = hit[ep.language]
        # length >= 2 in numerator and denominator alike: a one-character
        # label is matched too unreliably to be evidence either way, and
        # counting it only in the denominator would depress every language by
        # a different amount.
        labels = [l for l in ep.graph.labels if len(l) >= 2]
        found = _first_positions(ep.prompt, labels, boundary=True)
        cell[0] += len(labels)
        cell[1] += sum(1 for l in labels if l.lower() in found)
    return {l: (v[1] / v[0] if v[0] else 0.0) for l, v in hit.items()}


# ---------------------------------------------------------------------------
# oracle distances
# ---------------------------------------------------------------------------
def hamming(typ: Mapping[str, Mapping[str, str]], langs: Sequence[str],
            params: Sequence[str]) -> tuple[np.ndarray, int]:
    """Share of jointly coded features on which two languages disagree.

    Returns the matrix and how many pairs had **no** jointly coded feature and
    were therefore filled with the mean of the ones that did. That count is
    printed rather than hidden: with only four held-out features, two languages
    coded for two each can share none, and a matrix that quietly imputed those
    would be reporting an artefact of coverage as a typological distance.
    """
    n = len(langs)
    out = np.zeros((n, n))
    undefined: list[tuple[int, int]] = []
    for i, j in itertools.combinations(range(n), 2):
        a, b = typ.get(langs[i], {}), typ.get(langs[j], {})
        shared = [p for p in params if p in a and p in b]
        if not shared:
            undefined.append((i, j))
            continue
        out[i, j] = out[j, i] = sum(a[p] != b[p] for p in shared) / len(shared)
    if undefined:
        mask = np.ones((n, n), dtype=bool)
        for i, j in undefined:
            mask[i, j] = mask[j, i] = False
        np.fill_diagonal(mask, False)
        fill = float(out[mask].mean())
        for i, j in undefined:
            out[i, j] = out[j, i] = fill
    return out, len(undefined)


def categorical(values: Sequence, ) -> np.ndarray:
    """0 where two languages share the value, 1 where they do not."""
    n = len(values)
    out = np.zeros((n, n))
    for i, j in itertools.combinations(range(n), 2):
        out[i, j] = out[j, i] = 0.0 if values[i] == values[j] else 1.0
    return out


def absolute(values: Sequence[float]) -> np.ndarray:
    v = np.asarray(values, dtype=float)
    return np.abs(v[:, None] - v[None, :])


def euclid(vecs: np.ndarray) -> np.ndarray:
    diff = vecs[:, None, :] - vecs[None, :, :]
    return np.sqrt((diff ** 2).sum(-1))


# ---------------------------------------------------------------------------
# Mantel, partial Mantel, and their permutation tests
# ---------------------------------------------------------------------------
def _upper(m: np.ndarray) -> np.ndarray:
    return m[np.triu_indices(m.shape[0], 1)]


def _rank(x: np.ndarray) -> np.ndarray:
    order = np.argsort(x, kind="mergesort")
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(len(x), dtype=float)
    # average ties, so that a coarse Hamming distance with many ties is not
    # given a spurious ordering by argsort's stability
    _, inv, counts = np.unique(x, return_inverse=True, return_counts=True)
    sums = np.zeros(len(counts))
    np.add.at(sums, inv, ranks)
    return (sums / counts)[inv]


def _pearson(a: np.ndarray, b: np.ndarray) -> float:
    a = a - a.mean()
    b = b - b.mean()
    denom = math.sqrt(float((a * a).sum()) * float((b * b).sum()))
    return float((a * b).sum() / denom) if denom > 0 else 0.0


def mantel(A: np.ndarray, B: np.ndarray, *, perms: int, rng, rank: bool = True
           ) -> tuple[float, float]:
    """Correlation of two distance matrices, with a label-permutation p-value.

    ``rank=True`` makes it a Spearman-Mantel, which is what these coarse
    Hamming distances want: ``T_heldout`` takes five distinct values.
    """
    n = A.shape[0]
    iu = np.triu_indices(n, 1)
    b = _rank(B[iu]) if rank else B[iu]
    a = _rank(A[iu]) if rank else A[iu]
    r = _pearson(a, b)
    hits = 0
    for _ in range(perms):
        p = rng.permutation(n)
        ap = A[np.ix_(p, p)][iu]
        rp = _pearson(_rank(ap) if rank else ap, b)
        hits += rp >= r
    return r, (hits + 1) / (perms + 1)


def partial_mantel(A: np.ndarray, B: np.ndarray, C: np.ndarray | Sequence[np.ndarray],
                   *, perms: int, rng, rank: bool = True) -> tuple[float, float, float]:
    """Correlation of ``A`` and ``B`` with ``C`` residualised out of both.

    Returns ``(partial r, permutation p, marginal r)``. ``C`` may be several
    matrices, which is how "control for script *and* for the measured verbatim
    rate at once" is asked for.

    Residualising by least squares rather than using the three-correlation
    closed form, because the closed form does not generalise to two controls and
    two controls is the interesting case here.
    """
    n = A.shape[0]
    iu = np.triu_indices(n, 1)
    controls = [C] if isinstance(C, np.ndarray) else list(C)

    def prep(m: np.ndarray) -> np.ndarray:
        v = m[iu]
        return _rank(v) if rank else v

    X = np.column_stack([np.ones(len(iu[0]))] + [prep(c) for c in controls])

    def resid(v: np.ndarray) -> np.ndarray:
        beta, *_ = np.linalg.lstsq(X, v, rcond=None)
        return v - X @ beta

    b = resid(prep(B))
    a0 = prep(A)
    r_marg = _pearson(a0, prep(B))
    r = _pearson(resid(a0), b)
    hits = 0
    for _ in range(perms):
        p = rng.permutation(n)
        ap = A[np.ix_(p, p)]
        v = ap[iu]
        v = _rank(v) if rank else v
        hits += _pearson(resid(v), b) >= r
    return r, (hits + 1) / (perms + 1), r_marg


# ---------------------------------------------------------------------------
# reporting helpers
# ---------------------------------------------------------------------------
def average_linkage(dist: np.ndarray, names: Sequence[str]) -> list[str]:
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
        left, right = "+".join(clusters[a]), "+".join(clusters[b])
        if len(left) > 46:
            left = left[:43] + "..."
        if len(right) > 46:
            right = right[:43] + "..."
        lines.append(f"  {best_d:7.4f}   {left} | {right}")
        clusters[a] = clusters[a] + clusters[b]
        members[a] = members[a] + members[b]
        del clusters[b], members[b]
    return lines


def _table(title: str, rows: list[tuple]) -> None:
    print(f"\n{title}")
    print(f"  {'oracle':<28}{'r':>9}{'p':>8}   {'r | script':>11}{'p':>8}"
          f"   {'r | script+verbatim':>21}{'p':>8}")
    for name, rm, pm, r1, p1, r2, p2 in rows:
        print(f"  {name:<28}{rm:>9.4f}{pm:>8.4f}   {r1:>11.4f}{p1:>8.4f}"
              f"   {r2:>21.4f}{p2:>8.4f}")


# ---------------------------------------------------------------------------
def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("run", help="a finished omegaclaw_textlang-002 run directory")
    ap.add_argument("--perms", type=int, default=9999)
    ap.add_argument("--min-support", type=int, default=MIN_KEY_SUPPORT,
                    help="observations a relation needs in EVERY language")
    ap.add_argument("--shuffles", type=int, default=100,
                    help="permutations for the is-there-any-signal control")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", help="write the numbers here as JSON")
    args = ap.parse_args(argv)

    import language_clustering as LC
    from symbolic_ai_core.data import langdb
    from symbolic_ai_models.train import load_data, load_run

    rng = np.random.default_rng(args.seed)

    model, tok, cfg = load_run(args.run)
    train_eps, _ = load_data(cfg)
    langs = sorted({ep.language for ep in train_eps})
    print(f"{args.run}: {model.name}, {len(train_eps)} training episodes, "
          f"{len(langs)} languages, max_examples={model.max_examples}", flush=True)

    # ---- the oracle ------------------------------------------------------
    rows = langdb.language_rows()
    typ = langdb.typology_rows()
    read_params = list(langdb.RENDERED_WALS_FEATURES)
    held_params = list(langdb.HELDOUT_WALS_FEATURES)

    def coded(code: str, params: Sequence[str]) -> int:
        return len(set(typ.get(code, {})) & set(params))

    analysis = [l for l in langs
                if l not in SHADOWED
                and coded(l, read_params) >= MIN_READ_FEATURES
                and coded(l, held_params) >= MIN_HELDOUT_FEATURES]
    print(f"correlations run on {len(analysis)} of {len(langs)} languages "
          f"({len(analysis) * (len(analysis) - 1) // 2} pairs); dropped for thin "
          f"WALS coding: {sorted(set(langs) - set(analysis) - SHADOWED)}", flush=True)

    # ---- R_claw ----------------------------------------------------------
    print("\nre-deriving the claw table (this is the model's own statistic)",
          flush=True)
    claw_records, claw_langs = LC.observe(model, train_eps, tok, model.cfg.max_nodes)
    claws = list(model.claws())
    asked, cells = LC.tally(claw_records, claw_langs, claw_langs)
    keyed = all(isinstance(ctx, tuple) and ctx and ctx[0] in set(langs)
                for ctx, _ in model.claw_evidence)
    if keyed and model.claw_evidence:
        rebuilt: dict[tuple[str, str], list[float]] = {}
        for (ctx, name), (fired, right) in model.claw_evidence.items():
            cell = rebuilt.setdefault((ctx[0], name), [0.0, 0.0])
            cell[0] += fired
            cell[1] += right
        mismatch = [k for k in set(rebuilt) | set(cells)
                    if [float(v) for v in cells.get(k, [0, 0])]
                    != [float(v) for v in rebuilt.get(k, [0, 0])]]
        if mismatch:
            print(f"REFUSING: re-derived table disagrees with the fitted model in "
                  f"{len(mismatch)} cells, e.g. {mismatch[:3]}", file=sys.stderr)
            return 1
        print("  re-derivation reproduces model.claw_evidence exactly", flush=True)
    else:
        print("  note: this model does not key on language; the re-derivation "
              "cannot be checked against its own table", flush=True)

    claw_vecs_all = LC.vectors(asked, cells, langs, claws)
    D_claw_all = LC.distances(claw_vecs_all)

    # Where the between-language variance lives. `Lesson.structured` takes no
    # language, so the eleven graph claws have identical reliability everywhere
    # by construction and every scrap of variance has to come from the three
    # that read the prose. The seven-pack run read 99.05% / 0.95%; a different
    # split at 42 languages would mean the harness is leaking something.
    from symbolic_ai_models.models.omegaclaw import SURFACE_CLAWS
    surface = set(SURFACE_CLAWS)
    var = claw_vecs_all.var(axis=0)
    graph_dims = [j for j, c in enumerate(list(claws) * 2) if c not in surface]
    surf_dims = [j for j, c in enumerate(list(claws) * 2) if c in surface]
    total_var = float(var.sum())
    surface_share = float(var[surf_dims].sum()) / max(total_var, 1e-12)
    print(f"  between-language variance: graph claws "
          f"{float(var[graph_dims].sum()) / max(total_var, 1e-12):.4%}, "
          f"surface claws {surface_share:.4%}", flush=True)

    # ---- R_order ---------------------------------------------------------
    print("\nbuilding the order representation", flush=True)
    order_records = _order_records(train_eps)
    order_langs = order_records[4]
    order_vecs_all, cols = order_vectors(order_records, langs, order_langs,
                                         min_support=args.min_support)
    key_table = order_records[3]
    print(f"  {len(order_records[0]):,} ordered pairs over "
          f"{len(key_table)} distinct relations; {len(cols)} of them have "
          f">= {args.min_support} observations in every language and become "
          f"the columns of R_order", flush=True)
    for c in cols[:12]:
        print(f"    {key_table[c]}")
    D_order_all = euclid(order_vecs_all)

    verbatim = verbatim_rates(train_eps, langs)
    print("\n  verbatim label rate (the measured orthographic confound)")
    for l in sorted(langs, key=lambda l: -verbatim[l]):
        print(f"    {l:<6}{verbatim[l]:.3f}  {rows.get(l, {}).get('script', '?'):<5}"
              f"{(rows.get(l, {}).get('name') or '')[:28]}")

    # ---- H1: is there a per-language signal at all? ----------------------
    print("\ncontrol: mean pairwise distance, against shuffled language labels",
          flush=True)
    signal: dict[str, dict[str, float]] = {}
    for name, records, langs_of, build in (
            ("R_claw", claw_records, claw_langs,
             lambda rec, ln, asg: LC.distances(
                 LC.vectors(*LC.tally(rec, ln, asg), langs, claws))),
            ("R_order", order_records, order_langs,
             lambda rec, ln, asg: euclid(
                 order_vectors(rec, langs, asg, columns=cols)[0]))):
        real = float(np.mean(_upper(build(records, langs_of, langs_of))))
        shuffled = []
        for _ in range(max(args.shuffles, 1)):
            perm = list(rng.permutation(langs_of))
            shuffled.append(float(np.mean(_upper(build(records, langs_of, perm)))))
        arr = np.asarray(shuffled)
        sd = float(arr.std())
        signal[name] = {"real": real, "shuffled_mean": float(arr.mean()),
                        "shuffled_sd": sd, "shuffled_max": float(arr.max()),
                        "sd_above": (real - float(arr.mean())) / sd if sd else math.inf}
        print(f"  {name:<8} real {real:.4f}   shuffled {arr.mean():.4f} "
              f"+- {sd:.4f} (max {arr.max():.4f})   "
              f"{signal[name]['sd_above']:.1f} SD")

    # ---- restrict to the analysis set -----------------------------------
    idx = [langs.index(l) for l in analysis]
    D = {"R_claw": D_claw_all[np.ix_(idx, idx)],
         "R_order": D_order_all[np.ix_(idx, idx)]}
    T_order, n_order_undef = hamming(typ, analysis, list(ORDER_WALS_FEATURES))
    T_read, n_read_undef = hamming(typ, analysis, read_params)
    T_held, n_held_undef = hamming(typ, analysis, held_params)
    print(f"\npairs with no jointly coded feature (mean-filled): "
          f"word order {n_order_undef}, renderer-reads {n_read_undef}, "
          f"held-out {n_held_undef}")
    oracle = {
        "typology (word order)": T_order,
        "typology (renderer reads)": T_read,
        "typology (held out)": T_held,
        "genealogy (family)": categorical([rows[l]["family"] for l in analysis]),
        "geography (macroarea)": categorical([rows[l]["macroarea"] for l in analysis]),
        "script": categorical([rows[l]["script"] for l in analysis]),
        "verbatim label rate": absolute([verbatim[l] for l in analysis]),
    }
    script = oracle["script"]
    verb = oracle["verbatim label rate"]

    results: dict[str, list] = {}
    for rname, Dm in D.items():
        table = []
        for oname, Om in oracle.items():
            if np.isnan(Om).any():
                print(f"  skipping {oname}: undefined pairs", file=sys.stderr)
                continue
            rm, pm = mantel(Dm, Om, perms=args.perms, rng=rng)
            if oname == "script":
                r1, p1, r2, p2 = math.nan, math.nan, math.nan, math.nan
            else:
                controls = [script] if oname != "verbatim label rate" else [script]
                r1, p1, _ = partial_mantel(Dm, Om, controls, perms=args.perms, rng=rng)
                r2, p2, _ = partial_mantel(Dm, Om, [script, verb],
                                           perms=args.perms, rng=rng)
            table.append((oname, rm, pm, r1, p1, r2, p2))
        results[rname] = table
        _table(f"{rname}: Spearman-Mantel against each oracle "
               f"({len(analysis)} languages, {len(analysis)*(len(analysis)-1)//2} pairs, "
               f"{args.perms} permutations)", table)

    # ---- the same question without a residual model ----------------------
    # A partial Mantel assumes the control enters linearly in the ranks. The
    # assumption-free version of "control for script" is to hold script fixed:
    # inside the Latin-script block orthography is close to constant, so a
    # surviving typological correlation there is not a residualisation artefact.
    latin = [l for l in analysis if rows[l]["script"] == "Latn"]
    if len(latin) >= 12:
        li = [analysis.index(l) for l in latin]
        print(f"\nLatin script only ({len(latin)} languages, "
              f"{len(latin)*(len(latin)-1)//2} pairs) — script held fixed rather "
              f"than residualised")
        print(f"  {'representation':<16}{'oracle':<28}{'r':>9}{'p':>8}")
        latin_out = []
        for rname, Dm in D.items():
            for oname in ("typology (word order)", "typology (renderer reads)",
                          "typology (held out)", "genealogy (family)",
                          "geography (macroarea)", "verbatim label rate"):
                r, pv = mantel(Dm[np.ix_(li, li)], oracle[oname][np.ix_(li, li)],
                               perms=args.perms, rng=rng)
                print(f"  {rname:<16}{oname:<28}{r:>9.4f}{pv:>8.4f}")
                latin_out.append({"representation": rname, "oracle": oname,
                                  "r": r, "p": pv})
    else:
        latin_out = []

    # ---- readable shape --------------------------------------------------
    for rname, Dm in D.items():
        print(f"\n{rname}: nearest neighbour")
        for i, l in enumerate(analysis):
            order = np.argsort(Dm[i])
            near = [analysis[j] for j in order if j != i][0]
            same_fam = rows[l]["family"] == rows[near]["family"]
            same_scr = rows[l]["script"] == rows[near]["script"]
            print(f"  {l:<6} -> {near:<6} ({Dm[i, analysis.index(near)]:.3f})"
                  f"  {'SAME FAMILY' if same_fam else '':<12}"
                  f"{'same script' if same_scr else ''}")
        print(f"\n{rname}: average-linkage dendrogram")
        for line in average_linkage(Dm, analysis):
            print(line)

    # ---- what did R_order actually recover? -----------------------------
    # A correlation matrix is hard to argue with and easy to misread. This is
    # the legible version: project the order vectors onto their first principal
    # component and group the languages by the WALS feature that codes basic
    # clause order. If the representation carries word order at all, SOV and
    # SVO have to separate here — and if they do, remember that the renderer
    # was *given* 81A, so this is the positive control passing and not a
    # discovery.
    ordered_rows = order_vecs_all[[langs.index(l) for l in analysis]]
    centred = ordered_rows - ordered_rows.mean(axis=0)
    if centred.shape[1] and np.linalg.matrix_rank(centred) > 0:
        _, _, vt = np.linalg.svd(centred, full_matrices=False)
        pc1 = centred @ vt[0]
        print("\nR_order, first principal component, grouped by WALS 81A "
              "(basic clause order)")
        clause = {"1": "SOV", "2": "SVO", "3": "VSO", "4": "VOS", "5": "OVS",
                  "6": "OSV", "7": "no dominant order"}
        groups: dict[str, list[str]] = {}
        for l, v in zip(analysis, pc1):
            groups.setdefault(clause.get(typ[l].get("81A", ""), "not coded"),
                              []).append(f"{l}:{v:+.2f}")
        for name in sorted(groups, key=lambda g: -len(groups[g])):
            vals = [float(x.split(":")[1]) for x in groups[name]]
            print(f"  {name:<20} n={len(vals):<3} mean {np.mean(vals):+.3f}   "
                  + " ".join(sorted(groups[name])))

    if args.out:
        Path(args.out).write_text(json.dumps({
            "run": args.run,
            "languages_rendered": langs,
            "languages_analysed": analysis,
            "n_pairs": len(analysis) * (len(analysis) - 1) // 2,
            "permutations": args.perms,
            "order_relations_total": len(key_table),
            "order_relations_used": [str(key_table[c]) for c in cols],
            "verbatim": verbatim,
            "claw_surface_variance_share": surface_share,
            "signal": signal,
            "mantel": {r: [{"oracle": o, "r": rm, "p": pm,
                            "partial_script_r": r1, "partial_script_p": p1,
                            "partial_script_verbatim_r": r2,
                            "partial_script_verbatim_p": p2}
                           for o, rm, pm, r1, p1, r2, p2 in t]
                       for r, t in results.items()},
            "latin_only": latin_out,
            "latin_languages": latin,
            "distance": {r: m.tolist() for r, m in D.items()},
        }, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
