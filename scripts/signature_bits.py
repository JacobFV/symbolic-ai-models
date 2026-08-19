"""How much does a sentence signature actually tell you, on real English?

The signature-determinacy audit is this repo's most load-bearing instrument. It
has only ever been computed on surfaces **built to make signatures computable**:
entities are `region_0`, `machine_3`, `sub_2` -- prefix-typed identifiers -- and
each claim kind was given a shape of its own.

**The first version of this script measured the wrong thing, and the numbers said
so.** It reported the *entropy* of the signature -- 2.26 to 2.61 bits on the
generated surfaces against **3.65** on real abstracts -- and concluded nothing,
because entropy says how much a signature **varies**, not how much it
**determines**. Determinacy is a property of the joint distribution of signature
and predicate; a population can have arbitrarily high signature entropy and zero
determinacy. Entropy needs no labels, which is exactly why it cannot answer the
question labels are for.

What survives is a **lower bound on ambiguity mass**: if the largest signature
bucket holds more than one predicate, every sentence in it is ambiguous, so
ambiguity mass is at least that bucket's share. For the generated surfaces the
number of kinds per bucket is **exact** -- the spans carry them -- and that is the
whole story of why scheduling reads 0.000 and flood 0.617. For real text it rests
on the top bucket holding at least two predicates, which is demonstrated by
sampling rather than proved.

Entity detection on real prose is **crude in both directions** -- a capitalised
span that is not sentence-initial, plus all-caps acronyms. It over-counts
ordinary capitalised words and under-counts alphanumeric acronyms (``PW91``),
lowercase entities, definite descriptions and pronouns. **The conclusion does not
rest on it.** The largest bucket is the *empty* signature, and what puts a
sentence there is that a signature over (entity counts, numbers, dates) never
looks at the **verb** -- which is where a real predicate lives. A better named
entity recogniser moves sentences between buckets; it does not make
``contributed to``, ``is realized`` and ``include`` distinguishable by shape.

Run: uv run python -u scripts/signature_bits.py
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

OUT = Path("runs/signature_bits.json")

_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2} [A-Z][a-z]+ \d{4}\b")
_NUM = re.compile(r"\b\d+(?:\.\d+)?\b")
_SYNTH_ENTITY = re.compile(r"\b([a-z]+)_\d+\b|\bgroup\b")
#: A capitalised span not at the start of the sentence, or an acronym. Crude on
#: purpose, and crude in the direction that makes the result conservative.
_REAL_ENTITY = re.compile(r"(?<![.!?]\s)(?<!^)\b[A-Z][a-z]+(?: [A-Z][a-z]+)*\b"
                          r"|\b[A-Z]{2,}\b")


def signature(sentence: str, entity_re) -> tuple:
    dates = len(_DATE.findall(sentence))
    rest = _DATE.sub(" ", sentence)
    kinds: Counter = Counter()
    for m in entity_re.finditer(rest):
        named = next((g for g in m.groups() if g), None) if m.groups() else None
        kinds[named or "E"] += 1
    numbers = len(_NUM.findall(entity_re.sub(" ", rest)))
    return (tuple(sorted(kinds.items())), numbers, dates)


def entropy(counts: Counter) -> float:
    total = sum(counts.values())
    return -sum((k / total) * math.log2(k / total) for k in counts.values())


def synthetic_sentences() -> dict[str, list[str]]:
    from symbolic_ai_generators.flood import generate as fg
    from symbolic_ai_generators.flood import surface as FS
    from symbolic_ai_generators.scheduling import generate as sg
    from symbolic_ai_generators.scheduling import surface as SS
    from symbolic_ai_generators.solvency import generate as vg
    from symbolic_ai_generators.solvency import surface as VS

    def split(text):
        return [s.strip() for s in re.split(r"(?<=[.?!])\s+",
                                            text.replace("\n\n", " "))
                if s.strip()]

    out = {}
    out["flood"] = [s for i in range(60)
                    for s in split(FS.render_observation(fg(i),
                                                         variants=4).text)]
    out["scheduling"] = [s for i in range(60)
                         for s in split(SS.render_observation(
                             sg(i), variants=4).text)]
    out["solvency"] = [s for i in range(60)
                       for s in split(VS.render_observation(
                           vg(i), variants=4).text)]
    return out


def real_sentences() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    p = Path("data/sources/openalex-prose/openalex-prose-2026-08-18/"
             "works_p0.jsonl")
    if p.exists():
        sents = []
        for line in p.read_text(errors="ignore").splitlines():
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if rec.get("language") != "en":
                continue
            t = (rec.get("abstract") or "").strip()
            if t:
                sents += [s.strip() for s in re.split(r"(?<=[.?!])\s+", t)
                          if len(s.strip()) > 20]
        out["abstracts (openalex)"] = sents
    cache = Path("data/artifacts/gutenberg")
    if cache.exists():
        sents = []
        for f in sorted(cache.glob("*.txt")):
            body = f.read_text(errors="ignore")
            a, b = body.find("*** START"), body.find("*** END")
            body = body[a:b] if a != -1 and b != -1 else body
            body = re.sub(r"\s+", " ", body)
            sents += [s.strip() for s in re.split(r"(?<=[.?!])\s+", body)
                      if 40 < len(s.strip()) < 600 and len(s.split()) >= 8]
        if sents:
            out["narrative (gutenberg)"] = sents
    return out


def kinds_per_bucket() -> None:
    """How many claim kinds share the biggest signature bucket.

    Exact on the generated surfaces, because their spans carry the kind. This is
    the quantity `audit.ambiguity_mass` is built from, and it is why scheduling
    reads 0.000 while flood reads 0.617 -- not the entropy, which is nearly the
    same for both.
    """
    from symbolic_ai_generators.flood import generate as fg
    from symbolic_ai_generators.flood import surface as FS
    from symbolic_ai_generators.scheduling import generate as sg
    from symbolic_ai_generators.scheduling import surface as SS
    from symbolic_ai_generators.solvency import generate as vg
    from symbolic_ai_generators.solvency import surface as VS

    print(f"\n{'generated surface':<26} {'top bucket':>11} {'kinds in it':>12} "
          f"{'>1 kind share':>14}")
    print("-" * 66)
    for name, gen, surf in (("flood", fg, FS), ("scheduling", sg, SS),
                            ("solvency", vg, VS)):
        buckets: dict = {}
        total = 0
        for i in range(60):
            obs = surf.render_observation(gen(i), variants=4)
            for span in obs.spans:
                if span.claim is None:
                    continue
                sig = signature(obs.text[span.start:span.end], _SYNTH_ENTITY)
                buckets.setdefault(sig, Counter())[span.kind] += 1
                total += 1
        biggest = max(buckets.values(), key=lambda c: sum(c.values()))
        shared = sum(sum(c.values()) for c in buckets.values() if len(c) > 1)
        print(f"{name:<26} {sum(biggest.values()) / total:>11.3f} "
              f"{len(biggest):>12} {shared / total:>14.3f}")

    print("\nThe last column IS the ambiguity mass, recomputed here so the")
    print("comparison is like for like. A bucket can be huge and hold ONE kind,")
    print("which is what a determinate surface looks like.")


def main() -> None:
    rows = []
    for name, sents in synthetic_sentences().items():
        rows.append((f"{name} (generated)", sents, _SYNTH_ENTITY))
    for name, sents in real_sentences().items():
        rows.append((name, sents, _REAL_ENTITY))

    out = {}
    print(f"{'population':<26} {'sentences':>10} {'distinct sig':>13} "
          f"{'bits':>7} {'top bucket':>11} {'2^H':>7}")
    print("-" * 80)
    for name, sents, ent in rows:
        sigs = Counter(signature(s, ent) for s in sents)
        h = entropy(sigs)
        top = max(sigs.values()) / sum(sigs.values())
        out[name] = {"n": len(sents), "distinct": len(sigs), "bits": h,
                     "top_bucket": top, "distinguishable": 2 ** h}
        if ent is _REAL_ENTITY:
            top_sig = max(sigs, key=sigs.get)
            sample = [s for s in sents if signature(s, ent) == top_sig][:4]
            out[name]["top_bucket_sample"] = sample
            print(f"   top bucket = {top_sig}; four of its "
                  f"{sigs[top_sig]} sentences:")
            for x in sample:
                print(f"     - {x[:110]}")
        print(f"{name:<26} {len(sents):>10} {len(sigs):>13} {h:>7.2f} "
              f"{top:>11.3f} {2 ** h:>7.1f}")

    print("\nENTROPY IS THE WRONG STATISTIC and these numbers are why: real")
    print("abstracts carry MORE signature entropy (3.65 bits) than any generated")
    print("surface (2.26-2.61). A signature can vary freely and determine")
    print("nothing. What matters is how many PREDICATES share a bucket.")
    kinds_per_bucket()
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
