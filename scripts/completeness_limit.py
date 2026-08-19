"""Where does completeness stop winning?

`notes/findings/2026-08-18-the-extractor-that-wins-on-facts-loses-on-every-answer.md`
found that the extractor with the *worse* fact-level F1 builds the *better*
world: `collaborators` +0.085, `works_at` +0.058, count error halved, against a
fact-level loss of 0.121. Aggregate queries pay for **completeness**.

But every query there is a set **union** over an inverted index, and unions
reward over-generation almost by construction. So the design consequence is
either general or an artefact of one query family, and this decides which.

Four classes chosen to **punish** over-generation:

    works_at_both(A, B)          intersection over the inverted index —
                                 spurious co-occurrence is quadratic in
                                 over-generation
    common_institutions(w1, w2)  intersection of two works' institution sets
    institutions_unique_to(w1,w2) set difference — a NEGATIVE claim
    is_single_institution(work)  a boolean UNIVERSAL — "no other institution"

**The mechanism actually under test.** Intersection is a natural filter for
*uncorrelated* noise: if the high-recall extractor's false positives were random,
intersecting two noisy sets would kill most of them and completeness would keep
winning. They are not random — they are the thirteen University of Wisconsins,
the *siblings* of the true answer. When two works both say "University of
Wisconsin", both get all thirteen and the intersection keeps all thirteen.
**Correlated errors survive intersection**, and that is what this measures.

Run: SYMBOLIC_AI_PROSE_SNAPSHOT=openalex-prose-2026-08-18-authorship \\
     uv run python -u scripts/completeness_limit.py
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from scripts.first_arrow_gazetteer import ROR, v4
from scripts.first_arrow_geo import GeoGazetteer
from scripts.first_arrow_prose import load, score
from scripts.two_arrows_end_to_end import build_worlds, collaborators, v4_recall

OUT = Path("runs/completeness_limit.json")
SEED = 20260818
N = 3000


def boolean_scores(pairs) -> dict[str, Any]:
    """Accuracy, and the two error directions, for a yes/no answer.

    Accuracy alone hides which way a wrong answer went, and for a universal
    claim the two directions mean opposite things: saying "single" when it is
    not is asserting an absence that does not hold.
    """
    n = len(pairs)
    right = sum(1 for p, t in pairs if p == t)
    false_yes = sum(1 for p, t in pairs if p and not t)
    false_no = sum(1 for p, t in pairs if t and not p)
    base = max(sum(1 for _, t in pairs if t), n - sum(1 for _, t in pairs if t))
    return {"n": n, "accuracy": right / max(1, n),
            "majority_floor": base / max(1, n),
            "false_yes": false_yes / max(1, n),
            "false_no": false_no / max(1, n)}


def main() -> None:
    rng = random.Random(SEED)
    gz = GeoGazetteer(ROR)
    works = load()
    ids = [w["id"] for w in works]

    built = {}
    for label, fn in (("v4  abstains", v4), ("v4r high recall", v4_recall)):
        ref, ext, inv_ref, inv_ext, _ = build_worlds(works, gz, fn)
        built[label] = (ref, ext, inv_ref, inv_ext)
    ref = built["v4  abstains"][0]
    inv_ref = built["v4  abstains"][2]
    real = sorted({i for v in ref.values() for i in v})
    print(f"{len(works):,} works, {len(real):,} reference institutions\n",
          flush=True)

    # Query instances are drawn ONCE and shared, so the two worlds answer
    # exactly the same questions.
    work_pairs = [(rng.choice(ids), rng.choice(ids)) for _ in range(N * 4)]
    work_pairs = [(a, b) for a, b in work_pairs if a != b][:N]
    # Institution pairs are drawn from those that actually co-occur, or the
    # intersective query is trivially empty everywhere and measures nothing.
    inst_pairs = []
    while len(inst_pairs) < N:
        a = rng.choice(real)
        cos = sorted(collaborators(ref, inv_ref, a))
        if cos:
            inst_pairs.append((a, rng.choice(cos)))
    single_works = rng.sample(ids, min(N, len(ids)))

    rows: dict[str, dict[str, Any]] = {}
    for label, (_, ext, _, inv_ext) in built.items():
        r: dict[str, Any] = {}

        r["works_at_both(A,B)"] = score([
            (inv_ext.get(a, set()) & inv_ext.get(b, set()),
             inv_ref.get(a, set()) & inv_ref.get(b, set()))
            for a, b in inst_pairs])

        pairs = [(ext[a] & ext[b], ref[a] & ref[b]) for a, b in work_pairs]
        pairs = [(p, t) for p, t in pairs if t]        # skip empty truths
        r["common_institutions(w1,w2)"] = score(pairs)

        pairs = [(ext[a] - ext[b], ref[a] - ref[b]) for a, b in work_pairs]
        pairs = [(p, t) for p, t in pairs if t]
        r["institutions_unique_to(w1,w2)"] = score(pairs)

        r["is_single_institution(work)"] = boolean_scores([
            (len(ext[w]) == 1, len(ref[w]) == 1) for w in single_works])
        rows[label] = r

    order = ["works_at_both(A,B)", "common_institutions(w1,w2)",
             "institutions_unique_to(w1,w2)"]
    hdr = (f"{'query class':<32} {'extractor':<17} {'n':>6} {'F1':>7} "
           f"{'Jaccard':>9} {'prec':>7} {'rec':>7}")
    print(hdr)
    print("-" * len(hdr))
    for q in order:
        for label in rows:
            x = rows[label][q]
            print(f"{q if label.startswith('v4 ') else '':<32} {label:<17} "
                  f"{x['n']:>6,} {x['f1']:>7.3f} {x['jaccard']:>9.3f} "
                  f"{x['precision']:>6.1%} {x['recall']:>6.1%}")
        a = rows["v4  abstains"][q]["f1"]
        b = rows["v4r high recall"][q]["f1"]
        print(f"{'':<32} {'-> winner':<17} "
              f"{'v4r (completeness)' if b > a else 'v4 (precision)':<20} "
              f"{b-a:+.3f}\n")

    q = "is_single_institution(work)"
    print(f"{q}  (boolean universal)")
    for label in rows:
        x = rows[label][q]
        print(f"   {label:<17} accuracy {x['accuracy']:>6.1%}  "
              f"floor {x['majority_floor']:.1%}  "
              f"false-yes {x['false_yes']:>5.1%}  false-no {x['false_no']:>5.1%}")
    a = rows["v4  abstains"][q]["accuracy"]
    b = rows["v4r high recall"][q]["accuracy"]
    print(f"   -> winner: "
          f"{'v4r (completeness)' if b > a else 'v4 (precision)'} {b-a:+.3f}")

    wins_r = sum(1 for q in order
                 if rows["v4r high recall"][q]["f1"] > rows["v4  abstains"][q]["f1"])
    print(f"\ncompleteness wins {wins_r}/{len(order)} of the set-valued classes "
          f"here, against 2/2 of the UNION classes in the previous finding")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"seed": SEED, "n": N, "rows": rows}, indent=2))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
