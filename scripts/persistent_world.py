"""One world, many documents: does incremental update match re-reading everything?

The economic case for a persistent world is that a fact extracted once and reused
`N` times has different arithmetic from a transformer re-reading it `N` times:

    cost/query = C_ingest / N_uses + C_update + C_reason + C_generate

That part is arithmetic and is not worth an experiment. What is **not** known is
whether the incrementally maintained world is the *same world* — a persistent
store that quietly drifts from what a full re-read would say is worse than no
store, because the drift is invisible and permanent.

So: split each document into its paragraphs, deliver them one at a time, and
compare three arms after every delivery.

    re-read        run the reader on everything received so far. The ceiling,
                   and the thing whose cost grows with the corpus.
    persistent     keep one world; read each new paragraph alone and apply its
                   delta. The cheap arm.
    persistent+ctx same, but earlier paragraphs are passed as `context` --
                   scanned for **mentions only**, never for claims, so the cost
                   is a lexicon lookup per token rather than a parse.

Predicted before running:

- **`persistent` loses exactly the cross-paragraph references.** flood introduces
  a vehicle in one paragraph and says *"It can take a further N kg"* in the next;
  read alone, that sentence has no antecedent and the claim is dropped. So
  `capacity` and `demand` should be the losses, and `link`, `mass`, `flooded`
  should be untouched.
- **Latent minting survives the split**, because `~region_1|region_2` is minted
  from the mentions in its own sentence. `bridge_on` in one paragraph and
  `load_limit` in another should still agree on the identity — that is the
  property minting was built for and the split is its first real test.
- **`persistent+ctx` matches `re-read` exactly.** If it does, the mention history
  is the *entire* cross-document state this reader needs, and a persistent world
  costs a lexicon scan rather than a re-parse. If it does not, whatever is left
  over is the real specification of what `ReadResult` must carry between
  documents, which the ABI currently has no place for.

Run: uv run python -u scripts/persistent_world.py
"""

from __future__ import annotations

import json
import statistics
from collections import defaultdict
from pathlib import Path

from symbolic_ai_core.reader.learned import (LearnedSpanReader, segment,
                                             supervise)
from scripts.learned_reader import canonical, induce_schema, key
from scripts.learned_reader import world_from_claims
from scripts.reader_survives import build, domains

OUT = Path("runs/persistent_world.json")
N_TRAIN = 400
N_TEST = 40


def paragraphs(text: str) -> list[str]:
    return [p for p in text.split("\n\n") if p.strip()]


def sentences(text: str) -> list[str]:
    """The reader's own segmentation, so delivery and reading agree.

    Paragraph delivery turned out to test nothing: every reference in these
    surfaces is paragraph-local, so splitting on blank lines crosses none of
    them and all three arms agreed at 1.000. Sentence delivery is the granularity
    at which the antecedent is in a different document from the pronoun.
    """
    return [text[a:b] for a, b in segment(text)]


def main() -> None:
    results = {}
    for gran, split in (("paragraph", paragraphs), ("sentence", sentences)):
      for name, dom in domains().items():
          print(f"\n=== {name}, delivered one {gran} at a time")
          train = build(dom, range(N_TRAIN))
          schema = induce_schema([(c, o) for c, o, _ in train])
          reader = LearnedSpanReader().fit(
              [supervise(t, o.spans, c.world.claims) for c, o, t in train])
          test = build(dom, range(1_000_000, 1_000_000 + N_TEST))

          # Re-reading charges a full parse per delivery, because that is
          # what it does: N documents arrive and each arrival re-parses
          # everything received. The persistent arms charge what they run.
          cost = {"re-read": [], "persistent": [], "persistent+ctx": []}
          agree = {"persistent": [], "persistent+ctx": []}
          acc = {"re-read": [], "persistent": [], "persistent+ctx": []}
          lost: dict[str, dict[str, int]] = {"persistent": defaultdict(int),
                                             "persistent+ctx": defaultdict(int)}
          for c, o, text in test:
              paras = split(text)
              whole = reader.run(text)
              cost["re-read"].append(whole.cost_s * len(paras))
              full = {key(x) for x in canonical(whole.delta().claims, text)}
              want = dom["answer"](c.world, c)

              arms = {}
              for arm, use_ctx in (("persistent", False), ("persistent+ctx", True)):
                  claims = []
                  for i, p in enumerate(paras):
                      ctx = tuple(paras[:i]) if use_ctx else ()
                      r = reader.run(p, context=ctx)
                      cost[arm].append(r.cost_s)
                      claims.extend(r.delta().claims)
                  arms[arm] = claims
                  got = {key(x) for x in canonical(tuple(claims), text)}
                  agree[arm].append(1.0 if got == full else 0.0)
                  for k in full - got:
                      lost[arm][k[0]] += 1

              for arm, claims in (("re-read", reader.run(text).delta().claims),
                                  *arms.items()):
                  try:
                      mine = dom["answer"](world_from_claims(claims, schema), c)
                  except Exception:
                      mine = None
                  acc[arm].append(mine == want)

          ms = {k: 1000 * sum(v) / N_TEST for k, v in cost.items()}
          print(f"    {'arm':<16} {'== re-read':>11} {'end-to-end':>11} "
                f"{'ms/doc':>9} {'speedup':>8}")
          print(f"    {'re-read':<16} {1.0:11.3f} "
                f"{statistics.mean(acc['re-read']):11.3f} "
                f"{ms['re-read']:9.2f} {1.0:8.2f}x")
          for arm in ("persistent", "persistent+ctx"):
              print(f"    {arm:<16} {statistics.mean(agree[arm]):11.3f} "
                    f"{statistics.mean(acc[arm]):11.3f} {ms[arm]:9.2f} "
                    f"{ms['re-read'] / ms[arm]:8.2f}x")
              if lost[arm]:
                  print("        lost: " + ", ".join(
                      f"{k}x{v}" for k, v in sorted(lost[arm].items(),
                                                    key=lambda x: -x[1])))
          results[f"{name}/{gran}"] = {
              "chunks": statistics.mean(len(split(t)) for _, _, t in test),
              "agreement": {k: statistics.mean(v) for k, v in agree.items()},
              "acc": {k: statistics.mean(v) for k, v in acc.items()},
              "ms_per_doc": ms,
              "lost": {k: dict(v) for k, v in lost.items()}}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
