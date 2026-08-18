"""The multilingual protocol: train on a mixture, score languages held out of it.

:mod:`symbolic_ai_parsers.evaluate` fits on English and scores four languages,
which answers "did what it learned in English transfer". That question has an
answer — ``cky-001`` keeps 0.06 of its English bracket F1 in Chinese — and the
answer is what this module exists to move. The question here is the other one:
**can one rule set be fitted on many languages at once and still work on a
language it was never shown.**

The corpus makes that unusually clean. ``langdb.enable()`` renders 58 languages,
46 of them WALS-coded, and the graph is **byte-identical across every one of
them**: an exact parallel corpus, 46 languages wide. So the target never moves,
the input is translated, and every difference is attributable.

The protocol
------------

``mixture``
    Fit on all 46 languages, score all 46. The in-sample reference, and the
    denominator retention is measured against — same language, same eval
    episodes, only the training mixture changed.

``fold``
    **Leave eight languages out, six folds, every language held out exactly
    once.** Stated that way rather than as "leave-one-language-out" because it
    is not: the training mixture is 38 languages, not 45. Folds are stratified
    by script, so each one holds out roughly two non-Latin languages and six
    Latin ones, and the assignment is deterministic.

Grouping is not a shortcut around cost — it is stricter. Holding several
languages out together means the parser cannot lean on a near neighbour that
happened to survive into training.

Script, which is the confound
-----------------------------

Thirty-four of the 46 are Latin-script; the other twelve are the sole
representative of their script in the corpus. So for those twelve, being held
out means **the script is absent from training entirely**, and for the other
thirty-four it does not. The script test therefore needs no extra protocol: it
is the difference in *retention* between the two groups, where retention is a
language's held-out score over its own in-sample score, so "non-Latin languages
are harder anyway" is divided out rather than argued about.

The oracle, declared
--------------------

The conditioned arms are handed the language at parse time, from episode
metadata. That is an oracle and this repo's standing rule is that a supplied
signal must be measured as its own head with its own floor.
:func:`language_id_head` does it — nearest centroid on ``shape_features``,
floor 1/46 — and the number belongs beside any conditioned result.
"""

from __future__ import annotations

import json
import pathlib
import tomllib
from dataclasses import dataclass, field
from typing import Any, Sequence

import numpy as np

from symbolic_ai_core.data.curriculum import Episode, generate, resolve_lessons
from symbolic_ai_core.data.term_graph import TermGraph

from .base import Parser, build
from .evaluate import EVAL_SEED0
from .features import shape_features, standardise
from .floors import fit_floor
from .scoring import METRICS, Scores, macro_scores, score_graph

__all__ = ["WALS46", "ARMS", "N_FOLDS", "folds", "languages_of", "draw",
           "fit_floors", "evaluate_on", "language_id_head", "run_step"]

#: The 46 WALS-coded languages, read from the config rather than copied, so the
#: corpus this measures is the corpus that file names.
CONFIG = (pathlib.Path(__file__).resolve().parents[1]
          / "configs" / "full179_wals46.toml")

#: Every arm of the family, in the order the table should read: the parser, then
#: the controls that turn one knob back each, then the two references from the
#: existing package.
ARMS = ("polycky-001", "polycky-002", "polycky-crc", "polycky-1class",
        "polycky-literal", "polycky-v1seg", "polycky-hapax",
        "cky-001", "template-002")

N_FOLDS = 6


def languages_of(path: pathlib.Path = CONFIG) -> list[str]:
    cfg = tomllib.loads(path.read_text(encoding="utf-8"))
    return [s.strip() for s in cfg["languages"].split(",") if s.strip()]


WALS46 = languages_of()


def scripts(codes: Sequence[str]) -> dict[str, str]:
    """``code -> ISO 15924 script``, from the database's own metadata."""
    from symbolic_ai_core.data import langdb

    rows = langdb.language_rows()
    return {c: str(rows.get(c, {}).get("script", "?")) for c in codes}


def folds(codes: Sequence[str] = WALS46, n: int = N_FOLDS) -> list[list[str]]:
    """Stratify by script, then deal round-robin. Deterministic, no rng.

    Stratifying matters: twelve of the 46 are the only language in the corpus
    written in their script, and dealing them into one fold would make that
    fold's result a statement about novel scripts and the other five folds'
    results a statement about Latin.
    """
    sc = scripts(codes)
    rare = sorted(c for c in codes if sc[c] != "Latn")
    common = sorted(c for c in codes if sc[c] == "Latn")
    out: list[list[str]] = [[] for _ in range(n)]
    for i, c in enumerate(rare + common):
        out[i % n].append(c)
    return [sorted(f) for f in out]


# ---------------------------------------------------------------------------
# drawing episodes
# ---------------------------------------------------------------------------
def draw(languages: Sequence[str], lessons: Sequence[str], *, n: int,
         seed0: int, max_nodes: int = 128) -> list[Episode]:
    out: list[Episode] = []
    for lang in languages:
        out.extend(generate(list(lessons), n=n, seed0=seed0, language=lang,
                            max_nodes=max_nodes, on_error="skip"))
    return out


def fit_floors(lessons: Sequence[str], *, n_train: int, max_nodes: int = 128,
               cache: pathlib.Path | None = None) -> dict[str, float]:
    """The constant floor, fitted on **English** training episodes only.

    Not on the mixture, and the reason is a trap rather than a preference: the
    graph is identical in every language, so a multilingual training set holds
    each graph 46 times and the floor's candidate and target halves would
    contain the same graph. The floor would be handed a free exact match and
    every lift quoted above it would be wrong in the flattering direction.

    Text-blind, so the same numbers hold in every language — asserted by
    ``tests/test_graph_parsers.py`` rather than trusted.
    """
    if cache is not None and cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    train = draw(["english"], lessons, n=n_train, seed0=0, max_nodes=max_nodes)
    evals = draw(["english"], lessons, n=2, seed0=EVAL_SEED0, max_nodes=max_nodes)
    got = fit_floor(train).evaluate(evals)
    if cache is not None:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(got, indent=2), encoding="utf-8")
    return got


# ---------------------------------------------------------------------------
# scoring
# ---------------------------------------------------------------------------
def evaluate_on(parser: Parser, episodes: Sequence[Episode]) -> dict[str, float]:
    """Macro scores over lessons, using the parser's conditioned entry point.

    ``parse_episode`` is used when a parser has one, and it reads the episode's
    *metadata* — language and instance id — never its graph. A parser without it
    gets plain ``parse``, so the references in the table are scored by exactly
    the code path they are scored by everywhere else.
    """
    rows: list[Scores] = []
    lessons = [ep.lesson_id for ep in episodes]
    conditioned = getattr(parser, "parse_episode", None)
    for ep in episodes:
        try:
            pred = conditioned(ep) if conditioned else parser.parse(ep.prompt)
        except Exception:
            pred = TermGraph()
        rows.append(score_graph(pred, ep.graph))
    m = macro_scores(rows, lessons)
    out = {k: m[k] for k in METRICS}
    out["size_ratio"] = m["size_ratio"]
    return out


def lift(score: float, floor: float) -> float:
    room = 1.0 - floor
    return 0.0 if room < 1e-12 else (score - floor) / room


# ---------------------------------------------------------------------------
# the oracle, measured as its own head
# ---------------------------------------------------------------------------
def language_id_head(train: Sequence[Episode], evals: Sequence[Episode]
                     ) -> dict[str, float]:
    """Nearest-centroid language identification on ``shape_features``.

    The conditioned arms are handed the language. This says what that oracle is
    worth: whether a cheap text-only head could have supplied it, and how far
    above chance that head is. Chance is ``1/n_languages`` because the draw is
    balanced by construction; it is computed rather than assumed.
    """
    if not train or not evals:
        return {"acc": float("nan"), "floor": float("nan"), "n_languages": 0}
    langs = sorted({ep.language for ep in train})
    idx = {l: i for i, l in enumerate(langs)}
    X = np.array([shape_features(ep.prompt) for ep in train])
    mean, scale = standardise(X)
    X = (X - mean) / scale
    cent = np.zeros((len(langs), X.shape[1]))
    for ep, row in zip(train, X):
        cent[idx[ep.language]] += row
    counts = np.zeros(len(langs))
    for ep in train:
        counts[idx[ep.language]] += 1
    cent /= np.maximum(counts, 1)[:, None]

    E = (np.array([shape_features(ep.prompt) for ep in evals]) - mean) / scale
    d = ((E[:, None, :] - cent[None, :, :]) ** 2).sum(axis=2)
    pred = d.argmin(axis=1)
    truth = np.array([idx.get(ep.language, -1) for ep in evals])
    keep = truth >= 0
    acc = float((pred[keep] == truth[keep]).mean()) if keep.any() else float("nan")
    best = max(sum(1 for ep in evals if ep.language == l) for l in langs)
    return {"acc": acc, "floor": best / max(len(evals), 1),
            "n_languages": len(langs)}


# ---------------------------------------------------------------------------
# one step of the protocol, written to its own file
# ---------------------------------------------------------------------------
@dataclass
class Step:
    protocol: str
    fold: int
    train_languages: list[str]
    eval_languages: list[str]
    parsers: list[dict[str, Any]] = field(default_factory=list)
    floors: dict[str, float] = field(default_factory=dict)
    id_head: dict[str, float] = field(default_factory=dict)
    n_train: int = 3
    n_eval: int = 2
    n_lessons: int = 0


def run_step(protocol: str, fold: int, *, out: pathlib.Path,
             arms: Sequence[str] = ARMS, lessons: Sequence[str] | None = None,
             n_train: int = 3, n_eval: int = 2, max_nodes: int = 128,
             verbose: bool = True) -> Step:
    """Fit every arm on one training mixture and score the held-out languages.

    One step per process, written to disk the moment it finishes. A single
    process covering all of this is killed at ~20 minutes and takes its process
    group with it; that is measured, not feared.
    """
    names = list(lessons) if lessons is not None else resolve_lessons(None)
    all_langs = list(WALS46)
    if protocol == "mixture":
        train_langs, eval_langs = all_langs, all_langs
    elif protocol == "fold":
        held = folds(all_langs)[fold]
        train_langs = [l for l in all_langs if l not in set(held)]
        eval_langs = held
    else:
        raise ValueError(f"unknown protocol {protocol!r}")

    step = Step(protocol=protocol, fold=fold, train_languages=train_langs,
                eval_languages=eval_langs, n_train=n_train, n_eval=n_eval,
                n_lessons=len(names))
    step.floors = fit_floors(names, n_train=n_train, max_nodes=max_nodes,
                             cache=out.parent / "floors.json")

    train = draw(train_langs, names, n=n_train, seed0=0, max_nodes=max_nodes)

    # Held only when the fold is small. All 46 languages of eval episodes beside
    # the training mixture is a couple of gigabytes, and this package's own
    # record of what killed a 46-language job says the fix was granularity.
    cache: dict[str, list[Episode]] = {}
    keep_all = len(eval_langs) <= 12

    def eval_of(lang: str) -> list[Episode]:
        if lang in cache:
            return cache[lang]
        eps = draw([lang], names, n=n_eval, seed0=EVAL_SEED0, max_nodes=max_nodes)
        if keep_all:
            cache[lang] = eps
        return eps

    if protocol == "mixture":
        probe = [ep for lang in eval_langs
                 for ep in draw([lang], names[:8], n=1, seed0=EVAL_SEED0,
                                max_nodes=max_nodes)]
        step.id_head = language_id_head(train[::7], probe)

    for name in arms:
        parser = build(name)
        parser.fit(train)
        row: dict[str, Any] = {
            "parser": name, "describe": parser.describe(),
            "parameters": parser.n_parameters(), "per_language": {},
        }
        g = getattr(parser, "grammar", None)
        for key in ("oov_known", "oov_novel", "coverage", "n_languages"):
            if hasattr(g, key):
                row[key] = getattr(g, key)
        if hasattr(g, "classes"):
            row["n_classes"] = g.classes.n_classes()
            row["n_literal"] = g.classes.n_literal()
        if g is not None:
            row["n_rules"] = len(getattr(g, "rules", []))
        for lang in eval_langs:
            sc = evaluate_on(parser, eval_of(lang))
            row["per_language"][lang] = {
                "scores": sc,
                "lifts": {m: lift(sc[m], step.floors.get(m, 0.0))
                          for m in METRICS},
            }
        step.parsers.append(row)
        if verbose:
            mean_b = np.mean([row["per_language"][l]["scores"]["bracket_f1"]
                              for l in eval_langs])
            mean_e = np.mean([row["per_language"][l]["scores"]["edge_f1"]
                              for l in eval_langs])
            print(f"  {name:<17} brack {mean_b:.3f}  edge {mean_e:.3f}",
                  flush=True)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(step.__dict__, indent=1), encoding="utf-8")
    return step
