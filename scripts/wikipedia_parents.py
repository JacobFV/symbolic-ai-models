"""Does any of this work on prose nobody here wrote, with a gold answer?

`scripts/fetch_wikipedia_parents.py` pairs Wikidata's ``P749`` with the Wikipedia
intro. The task is the real-world analogue of solvency's ``owns``: read the
article, name the company's **current** parent.

Three arms, and the third is the one the experiment is for:

- **naive** -- every ownership mention the patterns find, first one wins;
- **+ sentence gate** -- drop sentences `stale_by_cancellation` flags, then read;
- **+ clause gate** -- drop only the *clause* the flag sits in.

The generated surfaces put one claim in one sentence, so a sentence-level gate is
free there. Real prose packs several claims into a sentence -- *"Formerly a
subsidiary of X, it was acquired by Y in 2015"* carries the dead parent and the
live one -- and if the sentence gate loses the answer along with the distractor,
the unit of staleness is a **clause**, not a sentence, and every gate in this repo
is built at the wrong granularity.

Run: uv run python -u scripts/wikipedia_parents.py
"""

from __future__ import annotations

import json
import re
import statistics
from pathlib import Path

from symbolic_ai_generators.staleness import stale_by_cancellation

SRC = Path("data/artifacts/wikipedia_parents.jsonl")
OUT = Path("runs/wikipedia_parents.json")

#: Surface patterns for "this company is owned by X". Deliberately plain: the
#: point is not to build a good extractor but to see what a claim-shaped rule
#: does when the text was not written to suit it.
_OWN = re.compile(
    r"\b(?:a |an |the )?(?:wholly[- ]owned |majority[- ]owned |direct )?"
    r"(?:subsidiary|division|unit|brand|arm|affiliate)\s+of\s+"
    r"(?:the\s+)?([A-Z][\w.&'-]*(?:\s+(?:[A-Z][\w.&'-]*|of|and|de|for))*)"
    r"|\bowned\s+by\s+(?:the\s+)?([A-Z][\w.&'-]*(?:\s+[A-Z][\w.&'-]*)*)"
    r"|\bacquired\s+by\s+(?:the\s+)?([A-Z][\w.&'-]*(?:\s+[A-Z][\w.&'-]*)*)"
    r"|\bpart\s+of\s+(?:the\s+)?([A-Z][\w.&'-]*(?:\s+[A-Z][\w.&'-]*)*)")

_STOP = re.compile(r"\s+(?:in|since|from|until|after|before|which|that|and|"
                   r"following|when|where)\b.*$")
#: A candidate name must stop at the end of its own clause. Without this the
#: regex runs past a full stop and picks up the next sentence's first word,
#: which changes nothing about who was named and everything about how the arms
#: compare -- the clause arm inserts its own separators.
_END = re.compile(r"[.,;:]")


def sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text)
    return [s.strip() for s in re.split(r"(?<=[.?!])\s+(?=[A-Z(])", text)
            if s.strip()]


def clauses(sentence: str) -> list[str]:
    return [c.strip().rstrip(".") for c in
            re.split(r"[,;:]|\s+(?:but|although|though)\s+", sentence)
            if c.strip()]


def candidates(text: str) -> list[str]:
    out = []
    for m in _OWN.finditer(text):
        name = next((g for g in m.groups() if g), "")
        name = _END.split(name)[0]
        name = _STOP.sub("", name).strip(" .,'")
        if len(name) > 2:
            out.append(name)
    return out


def _norm(s: str) -> str:
    s = s.lower()
    s = re.sub(r"\b(the|inc|inc\.|corp|corp\.|corporation|company|co|co\.|"
               r"ltd|ltd\.|limited|plc|group|holdings|holding|sa|nv|ag|llc)\b",
               " ", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def hit(guess: str, gold: str) -> bool:
    g, t = _norm(guess), _norm(gold)
    if not g or not t:
        return False
    return g == t or g in t or t in g


def read(text: str, mode: str) -> str:
    if mode == "sentence":
        text = " ".join(s for s in sentences(text)
                        if not stale_by_cancellation(s))
    elif mode == "clause":
        kept = []
        for s in sentences(text):
            if stale_by_cancellation(s):
                kept += [c for c in clauses(s) if not stale_by_cancellation(c)]
            else:
                kept.append(s)
        text = ". ".join(kept)
    cands = candidates(text)
    return cands[0] if cands else ""


def _names(text: str, names: list[str]) -> bool:
    t = _norm(text)
    return any(_norm(n) and _norm(n) in t for n in names)


def main() -> None:
    if not SRC.exists():
        print(f"{SRC} missing -- run scripts/fetch_wikipedia_parents.py")
        return
    rows = [json.loads(x) for x in SRC.read_text().splitlines() if x.strip()]
    print(f"{len(rows)} articles with a gold current parent\n")

    # --- controls, because precision means nothing without them -----------
    ceiling = statistics.mean(_names(r["intro"], r.get("current") or
                                     [r["parent"]]) for r in rows)
    have_former = [r for r in rows if r.get("former")]
    names_former = [r for r in have_former if _names(r["intro"], r["former"])]
    flagged = [r for r in rows
               if any(stale_by_cancellation(s) for s in sentences(r["intro"]))]
    print(f"CEILING: the current parent is named in the intro on "
          f"{ceiling:.3f} of articles.")
    print(f"Wikidata lists a FORMER parent for {len(have_former)} "
          f"({len(have_former) / len(rows):.3f}); the intro actually names one "
          f"on {len(names_former)} ({len(names_former) / len(rows):.3f}).")
    print(f"The cancellation gate flags a sentence on "
          f"{len(flagged) / len(rows):.3f} of articles.\n")

    out = {"n": len(rows), "ceiling": ceiling,
           "has_former": len(have_former) / len(rows),
           "names_former": len(names_former) / len(rows),
           "flagged_share": len(flagged) / len(rows)}

    print(f"{'arm':<12} {'answers':>8} {'correct':>8} {'precision':>10} "
          f"{'picks a FORMER parent':>22}")
    print("-" * 66)
    for mode in ("naive", "sentence", "clause"):
        guesses = [(r, read(r["intro"], mode)) for r in rows]
        answered = [(r, g) for r, g in guesses if g]
        correct = [1 for r, g in answered
                   if _names(g, r.get("current") or [r["parent"]])
                   or hit(g, r["parent"])]
        picks_former = [1 for r, g in answered
                        if r.get("former") and _names(g, r["former"])
                        and not hit(g, r["parent"])]
        out[mode] = {
            "answer_rate": len(answered) / len(rows),
            "accuracy": len(correct) / len(rows),
            "precision": len(correct) / len(answered) if answered else 0.0,
            "picks_former": len(picks_former) / len(rows)}
        print(f"{mode:<12} {out[mode]['answer_rate']:>8.3f} "
              f"{out[mode]['accuracy']:>8.3f} {out[mode]['precision']:>10.3f} "
              f"{out[mode]['picks_former']:>22.3f}")

    print("\n'picks a FORMER parent' is the error a staleness gate exists to")
    print("remove: Wikidata says that ownership ENDED and the reader named it")
    print("anyway. It is the only column where the gate can show a gain.")

    print("\nfour articles where the sentence gate and the clause gate differ:")
    shown = 0
    for r in rows:
        a, b = read(r["intro"], "sentence"), read(r["intro"], "clause")
        if a != b and shown < 4:
            shown += 1
            print(f"  {r['title']}  current={r.get('current')} "
                  f"former={r.get('former')}")
            print(f"     sentence -> {a!r}\n     clause   -> {b!r}")

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
