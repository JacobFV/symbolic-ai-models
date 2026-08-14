"""Grade the induced language representation against WALS, family and script.

`scripts/wals_perlang.py` fits one model per language and writes its claw
reliabilities; this reads them and asks whether the distances between languages
in *our* representation line up with distances nobody here authored.

**The oracle is split before any number exists, and that split is the whole
design.** `symbolic_ai_data.grammar.typology.derive_profile` builds a derived
grammar's word order *out of WALS*, so recovering those features from derived
prose is arithmetic rather than learning. The 14 features the renderer consumes
are a **positive control** -- they say the instrument can detect typological
signal when it is there by construction. The 4 it never reads are the test.

Distance-matrix entries are not independent, so every correlation is a Mantel
test with a permutation p-value, and the one that decides the reading is the
*partial* Mantel controlling for script: if induced distance tracks typology
only through orthography, we learned to read alphabets.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path

import numpy as np

import symbolic_ai_core.data.langdb as L


def _rank(v):
    order = v.argsort()
    out = np.empty_like(order, dtype=float)
    out[order] = np.arange(len(v))
    return out


def mantel(A, B, iu, n, perms=5000, seed=0):
    a, b = _rank(A[iu]), _rank(B[iu])
    obs = float(np.corrcoef(a, b)[0, 1])
    rng = np.random.default_rng(seed)
    hits = sum(abs(np.corrcoef(a, _rank(B[np.ix_(p, p)][iu]))[0, 1]) >= abs(obs)
               for p in (rng.permutation(n) for _ in range(perms)))
    return obs, (hits + 1) / (perms + 1)


def partial_mantel(A, B, C, iu, n, perms=5000, seed=1):
    """Mantel of A vs B with C partialled out of both, by rank residuals."""
    def resid(M):
        m, c = _rank(M[iu]), _rank(C[iu])
        return m - (np.cov(m, c)[0, 1] / np.var(c)) * c
    ra = resid(A)
    obs = float(np.corrcoef(ra, resid(B))[0, 1])
    rng = np.random.default_rng(seed)
    hits = sum(abs(np.corrcoef(ra, resid(B[np.ix_(p, p)]))[0, 1]) >= abs(obs)
               for p in (rng.permutation(n) for _ in range(perms)))
    return obs, (hits + 1) / (perms + 1)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("run", nargs="?", default="runs/wals46_perlang")
    ap.add_argument("--perms", type=int, default=5000)
    ap.add_argument("--out", default="")
    args = ap.parse_args(argv)

    L.enable()
    db = L.connect()
    per = {p.stem: json.loads(p.read_text(encoding="utf-8"))
           for p in sorted(Path(args.run).glob("*.json"))}
    codes = sorted(per)
    claws = sorted(set().union(*(set(v["reliability"]) for v in per.values())))
    X = np.array([[per[c]["reliability"].get(k, 0.0) for k in claws]
                  for c in codes])
    X = X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-12)
    induced = 1.0 - X @ X.T

    meta = {r[0]: r for r in
            db.execute("select code,name,family,macroarea,script from language")}
    typ: dict[str, dict[str, int]] = {}
    for code, param, value in db.execute("select code,param,value from typology"):
        typ.setdefault(code, {})[param] = value

    def feature_distance(features):
        D = np.zeros((len(codes), len(codes)))
        for i, a in enumerate(codes):
            for j, b in enumerate(codes):
                fa, fb = typ.get(a, {}), typ.get(b, {})
                shared = [f for f in features if f in fa and f in fb]
                D[i, j] = 1.0 - (sum(fa[f] == fb[f] for f in shared) / len(shared)
                                 if shared else 0.5)
        return D

    def category_distance(column):
        idx = {"family": 2, "macroarea": 3, "script": 4}[column]
        v = [meta.get(c, (None,) * 5)[idx] for c in codes]
        return np.array([[0.0 if (x is not None and x == y) else 1.0 for y in v]
                         for x in v])

    oracles = {
        "wals_rendered_control": feature_distance(L.RENDERED_WALS_FEATURES),
        "wals_heldout_test": feature_distance(L.HELDOUT_WALS_FEATURES),
        "family": category_distance("family"),
        "macroarea": category_distance("macroarea"),
        "script": category_distance("script"),
    }
    n = len(codes)
    iu = np.triu_indices(n, 1)
    report = {"languages": n, "pairs": len(iu[0]), "claws": len(claws),
              "mantel": {}, "partial_script": {}}
    for name, D in oracles.items():
        r, p = mantel(induced, D, iu, n, args.perms)
        report["mantel"][name] = {"r": r, "p": p}
    for name in ("wals_rendered_control", "wals_heldout_test", "family"):
        r, p = partial_mantel(induced, oracles[name], oracles["script"], iu, n,
                              args.perms)
        report["partial_script"][name] = {"r": r, "p": p}

    print(f"{n} languages, {len(iu[0])} pairs, {len(claws)} claws\n")
    print(f"{'oracle':34}{'Mantel r':>10}{'p':>9}")
    for k, v in report["mantel"].items():
        print(f"{k:34}{v['r']:>+10.4f}{v['p']:>9.4f}")
    print(f"\n{'partial, script controlled':34}{'r':>10}{'p':>9}")
    for k, v in report["partial_script"].items():
        print(f"{k:34}{v['r']:>+10.4f}{v['p']:>9.4f}")
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
