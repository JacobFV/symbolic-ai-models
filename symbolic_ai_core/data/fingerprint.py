"""A hash of the curriculum, so the generator cannot move without saying so.

Every number in ``RESEARCH_LOG.md``, ``README.md`` and ``runs/*`` rests on one
property: an episode is a pure function of ``(lesson, seed, language)``. Seeds,
not split files, are what separate train from eval, so if generation shifts by
one character the old and new numbers are measurements of different corpora and
nothing in the repo says so. The failure is silent by construction — there is no
dataset file whose checksum would change.

So the corpus gets a checksum anyway. :func:`curriculum_fingerprint` draws a
fixed grid — every implemented lesson, five seeds, every language — through
:mod:`symbolic_ai_core.data.curriculum`, which is the seam the rest of the
repo generates through, and reduces it to one digest per (lesson, language) plus
a global one. ``curriculum_fingerprint.json`` records what those were when the
published runs were made, against the ``langcurriculum`` git dependency, before
the generator was vendored into :mod:`symbolic_ai_data`.

Two digests are taken per lesson rather than one, because they fail differently:

* ``raw`` hashes the generator's own ``structured()`` dict, so it moves if the
  term changes in any way at all, including parts this repo's :class:`TermGraph`
  discards;
* the per-language digests hash the whole :class:`Episode` — prompt, answer,
  choices, instance id, tags and the converted graph — so they move if either
  surface changes *or* if the handoff between them does.

The grid deliberately includes two seeds at and above 1,000,000. Those are eval
seeds and nothing may be tuned against them, but hashing is not tuning and the
published eval numbers were drawn from exactly that range: a fingerprint that
covered only training seeds would leave the eval corpus unprotected, which is
the half that every reported lift depends on.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Sequence

from . import curriculum as C

__all__ = ["GOLDEN_PATH", "SEEDS", "curriculum_fingerprint", "load_golden",
           "golden_path_for",
           "compare"]

#: Where the recorded fingerprint lives.
GOLDEN_PATH = Path(__file__).resolve().parent / "curriculum_fingerprint.json"

#: Three training seeds and two eval seeds. Both ranges matter; see the module
#: docstring on why hashing eval seeds is not tuning against them.
SEEDS: tuple[int, ...] = (0, 1, 7, 1_000_000, 1_000_003)

#: 64 bits of digest per cell. Long enough that an accidental collision is not a
#: thing that happens, short enough that the recorded file stays readable.
_WIDTH = 16


def _digest(parts: Sequence[str]) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8"))
        h.update(b"\x1f")
    return h.hexdigest()[:_WIDTH]


def _canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"))


def golden_path_for(curriculum: str = "base") -> Path:
    """Where a curriculum's recorded fingerprint lives.

    One file per curriculum, and the base one keeps its original name. A KG
    curriculum sharing the base file would be exactly the silent redefinition
    the whole module exists to prevent.
    """
    if curriculum in ("base", "", None):
        return GOLDEN_PATH
    slug = curriculum.replace(":", "-")
    return GOLDEN_PATH.with_name(f"curriculum_fingerprint.{slug}.json")


def _episodes(lesson: str, language: str, curriculum: str = "base") -> list[C.Episode]:
    """Draw the grid one seed at a time, so a gap in the middle cannot shift
    every later episode onto a different seed and hide as a total mismatch."""
    out = []
    for s in SEEDS:
        out.extend(C.generate([lesson], n=1, seed0=s, language=language,
                              curriculum=curriculum))
    return out


def curriculum_fingerprint(lessons: Sequence[str] | None = None,
                           languages: Sequence[str] | None = None,
                           curriculum: str = "base",
                           ) -> dict[str, Any]:
    """Hash the grid. Returns the structure recorded in the golden file.

    ``curriculum`` selects which one is hashed. The ``raw`` digest is taken
    through the same binder as the text one — a bound episode's ``structured``
    and ``example`` halves have to be the same world, and hashing one of them
    outside the binding would silently certify the wrong pair.
    """
    lc = C._lc()
    lessons = sorted(lessons if lessons is not None else C.lesson_ids())
    if languages is None:
        languages = sorted(lc.language_codes()) if curriculum == "base" else ["english"]
    languages = sorted(languages)
    make_binder = C._binder_factory(curriculum)
    from symbolic_ai_data.binding import using

    per_lesson: dict[str, Any] = {}
    for lid in lessons:
        L = lc.get(lid)
        raws = []
        for s in SEEDS:
            with using(make_binder(lid, s) if make_binder else None):
                raws.append(_canon(L.structured(s)))
        raw = _digest(raws)
        texts = {}
        for lang in languages:
            texts[lang] = _digest(
                [_canon(ep.to_dict()) for ep in _episodes(lid, lang, curriculum)])
        per_lesson[lid] = {"raw": raw, "text": texts}

    glob = _digest([f"{lid}|{per_lesson[lid]['raw']}|"
                    + "|".join(f"{k}:{v}" for k, v in
                               sorted(per_lesson[lid]["text"].items()))
                    for lid in lessons])
    return {
        "seeds": list(SEEDS),
        "languages": list(languages),
        "n_lessons": len(lessons),
        "global": glob,
        "lessons": per_lesson,
    }


def load_golden(path: str | Path = GOLDEN_PATH) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def compare(golden: dict[str, Any], got: dict[str, Any]) -> list[str]:
    """Every way the two differ, named. An empty list is the passing case.

    Reports the *cells* that moved rather than only the global digest, because
    "the curriculum changed" is not actionable and "these four lessons changed
    in Turkish only" says where to look.
    """
    problems: list[str] = []
    if golden["seeds"] != got["seeds"]:
        problems.append(f"seed grid: {golden['seeds']} -> {got['seeds']}")
    if golden["languages"] != got["languages"]:
        problems.append(f"languages: {golden['languages']} -> {got['languages']}")
    gone = sorted(set(golden["lessons"]) - set(got["lessons"]))
    new = sorted(set(got["lessons"]) - set(golden["lessons"]))
    if gone:
        problems.append(f"lessons no longer generated: {gone}")
    if new:
        problems.append(f"lessons that did not exist: {new}")
    for lid in sorted(set(golden["lessons"]) & set(got["lessons"])):
        a, b = golden["lessons"][lid], got["lessons"][lid]
        if a["raw"] != b["raw"]:
            problems.append(f"{lid}: term graph {a['raw']} -> {b['raw']}")
        for lang in sorted(set(a["text"]) & set(b["text"])):
            if a["text"][lang] != b["text"][lang]:
                problems.append(
                    f"{lid} [{lang}]: episode {a['text'][lang]} -> {b['text'][lang]}")
    if not problems and golden["global"] != got["global"]:   # pragma: no cover
        problems.append("global digest differs with every cell equal — the "
                        "roll-up and the cells disagree, which is a bug here")
    return problems


def main(argv: Sequence[str] | None = None) -> int:   # pragma: no cover
    import argparse
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--write", action="store_true",
                   help="record the current fingerprint as the golden one. "
                        "Only correct when the corpus is *meant* to change, "
                        "which invalidates every published number carrying the "
                        "old one.")
    p.add_argument("--path", default=None)
    p.add_argument("--curriculum", default="base",
                   help="which curriculum to hash; see "
                        "symbolic_ai_core.data.curriculum.CURRICULA")
    args = p.parse_args(argv)
    if args.path is None:
        args.path = str(golden_path_for(args.curriculum))

    got = curriculum_fingerprint(curriculum=args.curriculum)
    if args.write:
        Path(args.path).write_text(json.dumps(got, indent=1, sort_keys=True) + "\n",
                                   encoding="utf-8")
        print(f"wrote {args.path}: {got['n_lessons']} lessons, "
              f"{len(got['languages'])} languages, global {got['global']}")
        return 0
    problems = compare(load_golden(args.path), got)
    for line in problems[:40]:
        print(line)
    if len(problems) > 40:
        print(f"... and {len(problems) - 40} more")
    print(f"global {got['global']}: {'MATCH' if not problems else 'MOVED'}")
    return 1 if problems else 0


if __name__ == "__main__":   # pragma: no cover
    raise SystemExit(main())
