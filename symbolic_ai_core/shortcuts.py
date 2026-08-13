"""What an unthinking rule scores — the floor that actually matters.

A uniform-guess floor asks "what does knowing nothing get?", which is the right
question but a weak version of it. The stronger question is what a *cheat* gets:
not knowing nothing, but knowing nothing about the problem while still looking
at the page. Pick the longest option. Pick the one sharing the most words with
the question. Pick the one that looks different from the others. None of these
require reading the episode, and on a generated curriculum they work far more
often than they should.

That matters twice over.

**It is a floor.** A lesson where "pick the longest option" scores 0.8 cannot
credit a model with 0.85 for understanding anything, and a uniform floor of 0.25
would have said it should. Every accuracy here is therefore reported against the
best shortcut as well as against chance.

**It is a generator audit.** A shortcut that solves a lesson outright is
evidence about the *lesson*, not the model — the distractors leak. The source
work this idea comes from found seven such defects that way, and the only reason
they were findable is that the shortcut was written down and run rather than
assumed absent.

The shortcuts here are parameter-free by construction. There is nothing fitted,
so there is no train/eval split to respect and no way for one to overfit; the
only selection is the maximum over a fixed handful of rules, which is stated
where it is used rather than hidden inside a single "floor" number.
"""

from __future__ import annotations

import collections
import re
from dataclasses import dataclass
from typing import Callable, Sequence

__all__ = ["SHORTCUTS", "Shortcut", "best_shortcut", "node_text_leak",
           "shortcut_scores",
           "shortcut_table"]

_WORD = re.compile(r"[^\W\d_]+|\d+", re.UNICODE)


def _words(text: str) -> list[str]:
    return [w.lower() for w in _WORD.findall(text)]


def _signature(option: str) -> tuple:
    """A crude shape of a string: which character classes it uses, and how long.

    Enough to notice that one option is written unlike its distractors, which is
    the classic generated-multiple-choice leak.
    """
    return (any(c.isdigit() for c in option), any(c.isupper() for c in option),
            any(c.isspace() for c in option), len(option))


def _argmax(choices: Sequence[str], key: Callable[[str], object]) -> str:
    """The first option with the maximal key.

    Tie-breaking matters more than it looks. Breaking ties on the option string
    — ``max(choices, key=lambda c: (score, c))`` — makes every shortcut prefer
    the lexicographically largest option whenever it has no signal, so
    unrelated cheats agree by accident, several of them post the same score, and
    the floor they feed is inflated by a coincidence of sort order. Falling back
    to *position* instead means "no signal" resolves the same neutral way for
    all of them, and two shortcuts agreeing then means they really did find the
    same thing.
    """
    best, best_key = choices[0], key(choices[0])
    for option in choices[1:]:
        candidate = key(option)
        if candidate > best_key:                     # strict: first max wins
            best, best_key = option, candidate
    return best


@dataclass(frozen=True)
class Shortcut:
    """A rule that picks an option while understanding nothing."""

    name: str
    why: str
    pick: Callable[[str, Sequence[str]], str]


def _longest(prompt: str, choices: Sequence[str]) -> str:
    return _argmax(choices, len)


def _shortest(prompt: str, choices: Sequence[str]) -> str:
    return _argmax(choices, lambda c: -len(c))


def _first(prompt: str, choices: Sequence[str]) -> str:
    return choices[0]


def _last(prompt: str, choices: Sequence[str]) -> str:
    return choices[-1]


def _alphabetical(prompt: str, choices: Sequence[str]) -> str:
    return min(choices)


def _overlap(prompt: str, choices: Sequence[str]) -> str:
    """The option sharing the most words with the question."""
    asked = set(_words(prompt))
    return _argmax(choices, lambda c: len(asked & set(_words(c))))


def _last_mentioned(prompt: str, choices: Sequence[str]) -> str:
    """The option the prompt mentions latest.

    Answers often appear in the text that states the problem, and "the most
    recently mentioned candidate" is a rule a reader could apply with their eyes
    shut. It catches recency leaks that word-overlap misses.
    """
    lowered = prompt.lower()
    return _argmax(choices, lambda c: lowered.rfind(c.lower()))


def _most_digits(prompt: str, choices: Sequence[str]) -> str:
    return _argmax(choices, lambda c: sum(ch.isdigit() for ch in c))


def _odd_one_out(prompt: str, choices: Sequence[str]) -> str:
    """The option written unlike the rest.

    A generator that builds distractors by one recipe and the answer by another
    leaves the answer looking different, and this finds that without knowing
    anything about the subject.
    """
    counts = collections.Counter(_signature(c) for c in choices)
    return _argmax(choices, lambda c: -counts[_signature(c)])


SHORTCUTS: tuple[Shortcut, ...] = (
    Shortcut("longest", "pick the longest option", _longest),
    Shortcut("shortest", "pick the shortest option", _shortest),
    Shortcut("first", "pick the first option offered", _first),
    Shortcut("last", "pick the last option offered", _last),
    Shortcut("alphabetical", "pick the alphabetically first option", _alphabetical),
    Shortcut("overlap", "pick the option sharing most words with the prompt", _overlap),
    Shortcut("recency", "pick the option the prompt mentions latest", _last_mentioned),
    Shortcut("digits", "pick the option with the most digits", _most_digits),
    Shortcut("odd_one_out", "pick the option written unlike the others", _odd_one_out),
)


def shortcut_scores(episodes: Sequence) -> dict[str, float]:
    """``{shortcut name: accuracy}`` over anything with ``prompt``, ``choices``
    and the gold answer.

    Accepts episodes or scored results alike — both carry the three fields this
    needs, and requiring one or the other would mean computing the audit in two
    places.
    """
    scores: dict[str, float] = {}
    usable = [e for e in episodes if getattr(e, "choices", None)]
    if not usable:
        return {s.name: float("nan") for s in SHORTCUTS}
    for shortcut in SHORTCUTS:
        hits = 0
        for episode in usable:
            gold = getattr(episode, "answer", None)
            try:
                picked = shortcut.pick(episode.prompt, list(episode.choices))
            except (ValueError, IndexError):          # pragma: no cover
                continue
            hits += picked.strip() == str(gold).strip()
        scores[shortcut.name] = hits / len(usable)
    return scores


def best_shortcut(episodes: Sequence) -> tuple[str, float]:
    """The strongest cheat and what it scores. ``("", 0.0)`` if there is nothing
    to score."""
    scores = {k: v for k, v in shortcut_scores(episodes).items() if v == v}
    if not scores:
        return "", 0.0
    name = max(scores, key=lambda k: (scores[k], k))
    return name, scores[name]


def shortcut_table(episodes: Sequence, *, limit: float = 0.0) -> str:
    """Every shortcut and what it scores, worst-case first.

    Printed in full rather than reduced to a maximum, because *which* cheat
    works says what leaked: ``recency`` scoring high means answers sit in the
    prompt, ``odd_one_out`` scoring high means the distractors are built by a
    different recipe than the answer.
    """
    scores = shortcut_scores(episodes)
    rows = sorted(scores.items(), key=lambda kv: -(kv[1] if kv[1] == kv[1] else -1))
    why = {s.name: s.why for s in SHORTCUTS}
    head = f"{'shortcut':<14}{'acc':>7}   what it exploits"
    lines = [head, "-" * max(len(head), 60)]
    for name, score in rows:
        if score == score and score >= limit:
            lines.append(f"{name:<14}{score:>7.3f}   {why[name]}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# the node task: would handing a model the prose leak the answer?
# ---------------------------------------------------------------------------
def node_text_leak(episodes: Sequence, *, mask_rate: float = 0.15,
                   max_nodes: int = 128, seed: int = 0) -> dict[str, float]:
    """How much of a hidden node's label the prompt gives away by itself.

    No model reads prose on the node task today — `collate_graph` carries no
    text. Adding it is the obvious next move for a pointer, and this decides
    whether it is admissible before anything is built on it.

    The split that matters is whether the answer is already in the graph:

    * **already visible** — the same symbol sits on an unmasked node, so the
      prompt reveals no symbol the input did not have. Nothing to leak.
    * **not in the graph** — this is the case to worry about. The prompt may
      name a symbol nothing else in the input can, while the floor is
      structure-only and cannot use it. That would move the comparison rather
      than the score, which is worse than an inflated number.

    The cheat measured is the one actually available: *the answer is a word of
    the prompt that is not already on a visible node*. Reported as its recall
    (is the answer even among those words) and its expected accuracy if it
    guesses uniformly among them, which is what "how ambiguous is it" means in
    units anyone can compare against a lift.

    Fit nothing, tune nothing: this is an audit, and it runs on whatever
    episodes it is handed.
    """
    import numpy as np

    rng = np.random.default_rng(seed)
    in_graph = out_of_graph = 0
    recalled = 0
    expected_hits = 0.0
    unique = 0

    for ep in episodes:
        g = ep.graph
        n = min(len(g), max_nodes)
        if not n:
            continue
        hidden = set(np.flatnonzero(rng.random(n) < mask_rate).tolist())
        visible = {g.labels[j] for j in range(n)
                   if j not in hidden and g.labels[j]}
        words = set(_words(ep.prompt))
        candidates = words - {v.lower() for v in visible}

        for i in sorted(hidden):
            label = g.labels[i]
            if not label:
                continue
            if label in visible:
                in_graph += 1
                continue
            out_of_graph += 1
            if label.lower() in candidates:
                recalled += 1
                expected_hits += 1.0 / max(len(candidates), 1)
                unique += len(candidates) == 1

    total = in_graph + out_of_graph
    return {
        "n_masked": float(total),
        "already_in_graph": in_graph / total if total else float("nan"),
        "not_in_graph": out_of_graph / total if total else float("nan"),
        "recall_when_absent": recalled / out_of_graph if out_of_graph else float("nan"),
        "expected_acc_when_absent": expected_hits / out_of_graph if out_of_graph else float("nan"),
        "uniquely_determined": unique / out_of_graph if out_of_graph else float("nan"),
        "expected_acc_overall": expected_hits / total if total else float("nan"),
    }
