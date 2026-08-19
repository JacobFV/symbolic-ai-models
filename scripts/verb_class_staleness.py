"""Can WordNet lift the floor the cue lists cannot reach?

The declared floor of 2026-08-19 is the **uncued** stale sentence: *"sub_98 left
the group in April"* has the ownership signature exactly and carries no
cancellation cue. `notes/findings/...entropy-was-the-wrong-statistic...` says why
nothing here sees it -- a signature over (entity counts, numbers, dates) never
looks at the **verb**, and the verb is where the predicate lives.

WordNet is on disk. Three things are measured, in the order that decides whether
the idea survives:

1. **supersenses cannot separate** transition from state -- they classify by
   subject matter, so ``cease`` is *verb.stative* and ``divest`` is
   *verb.possession*, exactly like ``own``;
2. the **hypernym closure** can, on a held-out verb set, at 0.42 recall and 0.08
   false positives;
3. and at the **sentence** level it fires on half of real English, because two of
   the chosen ancestors sit near the root of the verb hierarchy and because every
   token is tested as a verb.

The third is what decides it, and it is the measurement a hand-listed negative
class of fifteen verbs could not make.

Run: uv run python -u scripts/verb_class_staleness.py
"""

from __future__ import annotations

import collections
import json
import re
import statistics
from pathlib import Path

from symbolic_ai_generators.staleness import TRANSITION_ROOTS
from symbolic_ai_generators.wordnet import (first_sense_supersense,
                                            hypernym_closure, is_verb_lemma)

OUT = Path("runs/verb_class_staleness.json")

#: Ancestors deep in the hierarchy. ``change`` and ``transfer`` are dropped
#: because nearly every transitive verb reaches them -- measured, not guessed.
DEEP_ROOTS = frozenset({"end", "discontinue", "leave", "exit", "deprive",
                        "remove"})

#: A token straight after one of these is a noun, not a verb. Closed class, and
#: the same trick that separated the two readings of ``used to``.
_NOMINAL = frozenset({"the", "a", "an", "of", "in", "for", "to", "this",
                      "that", "its", "their", "our", "any", "each", "no",
                      "some", "these", "those", "on", "by", "with", "at"})

DESIGN_STALE = ["left", "divested", "withdrawn", "resigned", "ceased",
                "cancelled", "ended", "sold", "exited", "departed", "quit",
                "dissolved", "terminated", "lapsed"]
HELD_OUT_STALE = ["relinquish", "abandon", "forfeit", "revoke", "rescind",
                  "expire", "vacate", "retire", "suspend", "annul", "disband",
                  "discharge"]
HELD_OUT_REAL = ["comprises", "contains", "belongs", "spans", "links",
                 "borders", "employs", "operates", "supplies", "serves",
                 "houses", "stocks"]


def fires(token: str, roots) -> bool:
    return bool(roots & hypernym_closure(token))


def sentence_fires(sentence: str, roots, *, nominal_filter: bool) -> bool:
    toks = re.findall(r"[A-Za-z][a-z]+", sentence)
    for i, w in enumerate(toks):
        low = w.lower()
        if nominal_filter and i and toks[i - 1].lower() in _NOMINAL:
            continue
        if is_verb_lemma(low) and fires(low, roots):
            return True
    return False


def real_sentences(limit: int = 1500) -> list[str]:
    p = Path("data/sources/openalex-prose/openalex-prose-2026-08-18/"
             "works_p0.jsonl")
    out: list[str] = []
    for line in p.read_text(errors="ignore").splitlines()[:limit]:
        try:
            rec = json.loads(line)
        except Exception:
            continue
        if rec.get("language") != "en":
            continue
        t = (rec.get("abstract") or "").strip()
        if t:
            out += [s.strip() for s in re.split(r"(?<=[.?!])\s+", t)
                    if len(s.strip()) > 20]
    return out


def main() -> None:
    out: dict = {}

    print("1. SUPERSENSES CANNOT SEPARATE TRANSITION FROM STATE")
    for group, words in (("relation verbs", ["owns", "holds", "is", "joined",
                                             "requires", "includes"]),
                         ("transition verbs", ["left", "divested", "ceased",
                                               "ended", "terminated",
                                               "sold"])):
        print(f"   {group:<18} " + ", ".join(
            f"{w}={first_sense_supersense(w).replace('verb.', '')}"
            for w in words))
    print("   `ceased` is stative and `divested` is possession, exactly like "
          "`own`.\n")

    print("2. THE HYPERNYM CLOSURE, ON VERBS")
    print(f"   {'root set':<14} {'design recall':>14} {'held-out recall':>16} "
          f"{'held-out FP':>12}")
    for name, roots in (("all 8", TRANSITION_ROOTS), ("deep 6", DEEP_ROOTS)):
        d = statistics.mean(fires(w, roots) for w in DESIGN_STALE)
        h = statistics.mean(fires(w, roots) for w in HELD_OUT_STALE)
        f = statistics.mean(fires(w, roots) for w in HELD_OUT_REAL)
        out[f"verbs/{name}"] = {"design_recall": d, "held_out_recall": h,
                                "held_out_fp": f}
        print(f"   {name:<14} {d:>14.2f} {h:>16.2f} {f:>12.2f}")
    print("   The design set reads high because the roots were chosen on it. "
          "The\n   held-out column is the number.\n")

    print("3. AND AT THE SENTENCE LEVEL, ON REAL ENGLISH")
    sents = real_sentences()
    print(f"   {len(sents)} sentences from real abstracts")
    print(f"   {'root set':<14} {'no filter':>11} {'+ nominal filter':>18}")
    for name, roots in (("all 8", TRANSITION_ROOTS), ("deep 6", DEEP_ROOTS)):
        raw = statistics.mean(sentence_fires(s, roots, nominal_filter=False)
                              for s in sents)
        filt = statistics.mean(sentence_fires(s, roots, nominal_filter=True)
                               for s in sents)
        out[f"real/{name}"] = {"raw": raw, "nominal_filtered": filt}
        print(f"   {name:<14} {raw:>11.3f} {filt:>18.3f}")
    print("   against the cancellation gate's 0.003 on the same corpus.\n")

    per = collections.Counter()
    for s in sents:
        for w in re.findall(r"[A-Za-z][a-z]+", s):
            low = w.lower()
            if is_verb_lemma(low):
                for r in TRANSITION_ROOTS & hypernym_closure(low):
                    per[r] += 1
    print("   fires per root, over all tokens -- the depth problem, measured:")
    for r, k in per.most_common():
        print(f"      {r:<14} {k}")
    out["per_root_tokens"] = dict(per)

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
