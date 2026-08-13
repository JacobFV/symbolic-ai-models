"""Fit on English training episodes, score on eval episodes in four languages.

The cross-language run is the first-class evaluation here, not an appendix, and
the reason is a property of this corpus that took a test to establish and is
worth restating because it is unusual. ``langcurriculum`` takes a language when
it *renders* and does not take one when it *structures*, so the same seed gives
a different string in every language and **byte-identical graph** — pinned by
``tests/test_language.py::test_the_graph_does_not_change_with_the_language``.

For the masked-node task in the other package that is a disappointment: it means
a cross-language node experiment measures nothing. For a parser it is the ideal
experiment. The target is fixed, the input is translated, and so the drop from
English to Chinese is a clean measurement of how much of a parser's score was
resting on English words rather than on the grammar of the document. There is no
confound to argue about, because there is nothing else that changed.

Three languages beside English, chosen before any of this was run, for what they
are rather than for what they score: Chinese translates the most and shares no
script; Turkish reorders (the predicate moves to the end of the clause) and
leaves a good deal of English in place; Swahili translates the content words and
keeps most of the frame. So a parser that survives Chinese and a parser that
survives only Swahili are making different claims, and the table can tell them
apart.

Everything is macro-averaged over lessons and run over **every** lesson
``lesson_ids()`` returns. Small slices have produced confident wrong readings in
this repo six times; a slice is available here (``--lessons``) and any number it
produces is labelled with the slice in the report, but the default is all of
them.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from symbolic_ai_models.data.curriculum import Episode, generate, resolve_lessons

from .base import Parser, build, parser_names
from .floors import ConstantFloor, fit_floor
from .scoring import METRICS, SHORT, Scores, macro_scores, score_graph

__all__ = ["ParserReport", "evaluate_parser", "run_sweep", "LANGUAGES",
           "EVAL_SEED0"]

#: Seeds at or above this are evaluation only, everywhere in this repo.
EVAL_SEED0 = 1_000_000

#: English first; the rest in the order they are argued about above.
LANGUAGES = ("english", "chinese", "turkish", "swahili")


@dataclass
class ParserReport:
    """One parser, one language, every metric with the floor it is read against."""

    parser: str
    learned: bool
    language: str
    n_episodes: int
    n_lessons: int
    scores: dict[str, float] = field(default_factory=dict)
    floors: dict[str, float] = field(default_factory=dict)
    size_ratio: float = 0.0
    #: share of parses whose retrieved neighbour came from the right lesson.
    #: ``nan`` for parsers that do not retrieve — an absent mechanism is not a
    #: zero.
    retrieval_acc: float = float("nan")
    parameters: int = 0
    #: the lesson selector this row was measured on, carried so that a number
    #: quoted out of the table still says what it was measured on
    lessons_spec: str = "all"

    def lift(self, metric: str) -> float:
        s, f = self.scores.get(metric, 0.0), self.floors.get(metric, 0.0)
        room = 1.0 - f
        return 0.0 if room < 1e-12 else (s - f) / room

    def to_dict(self) -> dict[str, Any]:
        d = dict(self.__dict__)
        d["lifts"] = {m: self.lift(m) for m in METRICS}
        return d

    @staticmethod
    def header() -> str:
        cols = (f"{'parser':<17}{'lang':<9}{'retr':>7}{'size':>6}"
                + "".join(f"{SHORT[m]:>8}" for m in METRICS))
        return cols + "\n" + "-" * len(cols)

    def row(self) -> str:
        r = "  n/a" if self.retrieval_acc != self.retrieval_acc else f"{self.retrieval_acc:>7.3f}"
        return (f"{self.parser:<17}{self.language:<9}{r:>7}{self.size_ratio:>6.2f}"
                + "".join(f"{self.scores.get(m, float('nan')):>8.3f}" for m in METRICS))

    def lift_row(self) -> str:
        return (f"{self.parser:<17}{self.language:<9}{'':>7}{'':>6}"
                + "".join(f"{self.lift(m):>8.3f}" for m in METRICS))


def floor_row(floors: dict[str, float], language: str) -> str:
    return (f"{'FLOOR (constant)':<17}{language:<9}{'':>7}{'':>6}"
            + "".join(f"{floors.get(m, float('nan')):>8.3f}" for m in METRICS))


def evaluate_parser(parser: Parser, episodes: Sequence[Episode],
                    floors: dict[str, float], *, language: str,
                    lessons_spec: str = "all") -> ParserReport:
    """Parse every episode and score it. The parser is already fitted."""
    rows: list[Scores] = []
    lessons = [ep.lesson_id for ep in episodes]
    hits = tries = 0
    for ep in episodes:
        try:
            pred = parser.parse(ep.prompt)
        except Exception:
            # A parser that raises must still be scored on that episode.
            # Dropping it would silently exclude exactly the inputs it cannot
            # handle and report the rest as if they were the whole set.
            from symbolic_ai_models.data.graph import Graph
            pred = Graph()
        rows.append(score_graph(pred, ep.graph))
        got = getattr(parser, "last_lesson", None)
        if got is not None:
            tries += 1
            hits += got == ep.lesson_id
    m = macro_scores(rows, lessons)
    return ParserReport(
        parser=parser.name, learned=parser.learned, language=language,
        n_episodes=len(episodes), n_lessons=len(set(lessons)),
        scores={k: m[k] for k in METRICS}, floors=dict(floors),
        size_ratio=m["size_ratio"],
        retrieval_acc=(hits / tries) if tries else float("nan"),
        parameters=parser.n_parameters(), lessons_spec=lessons_spec)


def run_sweep(*, parsers: Sequence[str] | None = None,
              lessons: str | Sequence[str] | None = None,
              n_train: int = 16, n_eval: int = 4,
              languages: Sequence[str] = LANGUAGES,
              max_nodes: int = 128, out: str | Path | None = None,
              verbose: bool = True) -> list[ParserReport]:
    """The authority. Fit on English train; score on eval in every language.

    One fit per parser, reused across languages, because a parser refitted per
    language would be answering a different question — "can it learn Chinese"
    rather than "did what it learned in English transfer".
    """
    names = list(parsers or parser_names())
    lesson_names = resolve_lessons(lessons)
    spec = "all" if lessons in (None, "all") else str(lessons)

    train = list(generate(lesson_names, n=n_train, seed0=0, language="english",
                          max_nodes=max_nodes, on_error="skip"))
    evals = {lang: list(generate(lesson_names, n=n_eval, seed0=EVAL_SEED0,
                                 language=lang, max_nodes=max_nodes,
                                 on_error="skip"))
             for lang in languages}

    floor: ConstantFloor = fit_floor(train)
    # The floor is text-blind, so it is the *same* number in every language --
    # the graphs do not change. Computed once on the English eval set and
    # reused, and asserted by a test rather than trusted.
    floors = floor.evaluate(evals[languages[0]])

    reports: list[ParserReport] = []
    for name in names:
        parser = build(name)
        parser.fit(train)
        for lang in languages:
            r = evaluate_parser(parser, evals[lang], floors, language=lang,
                                lessons_spec=spec)
            reports.append(r)
            if verbose:
                print(r.row(), flush=True)

    if out:
        p = Path(out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({
            "lessons": lesson_names, "n_lessons": len(lesson_names),
            "n_train": n_train, "n_eval": n_eval, "eval_seed0": EVAL_SEED0,
            "max_nodes": max_nodes, "languages": list(languages),
            "floor_sources": floor.sources, "floor_train": floor.train_scores,
            "floors": floors,
            "reports": [r.to_dict() for r in reports],
        }, indent=2), encoding="utf-8")
    return reports
