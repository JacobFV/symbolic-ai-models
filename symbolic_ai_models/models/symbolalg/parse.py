"""A deliberately weak text parser.

Ported from symbolic-ai-001 (`agents/base_symbolic_agent_002/parse.py`), unchanged
except where marked. It is the formal-grammar half of that project's claim: the
agent recovers structure from the sentence itself rather than being handed the
generator's tree.

The environments describe themselves in prose. An agent that wants to induce
over structure has to recover some, and this is the recovery: clause splitting,
word/number tokenization, and a guess at which token names the relation. It is
weak on purpose, and it is *ours* -- an agent-side hypothesis about how the
sentence is put together, not the generator's tree handed back.

    "Agent at (0, 3)."  ->  (at agent 0 3)  and  (agent at 0 3)

Both readings are emitted because the parser genuinely does not know which token
is the predicate. Sorting that out is induction's job, which is the whole point:
the ambiguity belongs to the learner, not to the interface.

Nothing here knows about any environment.
"""

from __future__ import annotations

import re
from typing import Any, Iterable, Sequence

from .symbols import Ident, Lst, Num, Pred, Rec, Str, Symbol

__all__ = ["clauses", "tokens", "words", "numbers", "facts_from_text", "scalars_from_text",
           "question_of", "options_from_text", "parse_text"]

_CLAUSE = re.compile(r"[.;\n]+|(?<=[?!])\s+")
_TOKEN = re.compile(r"-?\d+(?:\.\d+)?|[A-Za-z_][A-Za-z0-9_'\-]*")
_NUM = re.compile(r"^-?\d+(?:\.\d+)?$")
# "Options: a, b, c" / "Answer with one of: a | b" / "Choices: ..."
# CHANGED from the 001 original: `legal actions` added to the alternation. It is
# the same convention under a different word — an env spelling out its answer
# vocabulary inline — and without it this parser is blind to every game env here.
_OPTIONS = re.compile(r"(?:options?|choices?|legal\s+actions?|answer(?:\s+with)?"
                      r"(?:\s+exactly)?(?:\s+one\s+of)?|one\s+of)\s*[:\-]\s*(.+)",
                      re.IGNORECASE)
_SPLIT_OPTS = re.compile(r"\s*[,|/]\s*|\s+or\s+")


def clauses(text: str) -> list[str]:
    """Sentences, list items and lines -- whatever the writer separated."""
    parts: list[str] = []
    for raw in _CLAUSE.split(str(text)):
        if raw is None:
            continue
        for piece in raw.split(","):
            s = piece.strip()
            if s:
                parts.append(s)
    return parts


def tokens(text: str) -> list[Any]:
    """Words and numbers, in order, with numbers coerced."""
    out: list[Any] = []
    for t in _TOKEN.findall(str(text)):
        out.append(_number(t) if _NUM.match(t) else t)
    return out


def _number(t: str) -> int | float:
    f = float(t)
    return int(f) if f.is_integer() else f


def words(text: str) -> list[str]:
    return [t for t in tokens(text) if isinstance(t, str)]


def numbers(text: str) -> list[int | float]:
    return [t for t in tokens(text) if not isinstance(t, str)]


def _atom(t: Any) -> Symbol:
    return Ident(t) if isinstance(t, str) else Num(t)


def facts_from_text(text: str, *, max_facts: int = 96) -> list[Symbol]:
    """Ground facts, one or two per clause, under both head readings."""
    out: list[Symbol] = []
    for c in clauses(text):
        ts = tokens(c)
        if not ts:
            continue
        head = ts[0]
        if isinstance(head, str):
            out.append(Pred(head.lower(), *[_atom(t) for t in ts[1:]]))
        if len(ts) >= 2 and isinstance(ts[1], str):
            # the second reading: "<subject> <relation> <args>", which is how
            # English usually puts it and how the fact languages here are shaped
            out.append(Pred(ts[1].lower(), _atom(ts[0]), *[_atom(t) for t in ts[2:]]))
        if len(out) >= max_facts:
            break
    return out[:max_facts]


def scalars_from_text(text: str, *, max_scalars: int = 16) -> dict[str, int | float]:
    """Quantities: a clause of words ending in one number states one.

    "grid size 5" is read as ``grid_size = 5``. It is a guess like everything
    else here -- and a weak one, since it cannot tell a quantity from a sentence
    that happens to end in a digit -- but a learner that never gets to see a
    scalar cannot express a law like "the world stops at its own size".
    """
    out: dict[str, int | float] = {}
    for c in clauses(text):
        ts = tokens(c)
        if len(ts) < 2 or isinstance(ts[-1], str):
            continue
        if any(not isinstance(t, str) for t in ts[:-1]):
            continue
        name = "_".join(t.lower() for t in ts[:-1])
        if name and name not in out:
            out[name] = ts[-1]
        if len(out) >= max_scalars:
            break
    return out


def question_of(text: str) -> str:
    """The clause that asks something: a question mark, else a goal/question
    marker, else the last clause. A guess, and it is allowed to be wrong."""
    cs = clauses(text)
    if not cs:
        return ""
    for c in cs:
        if c.rstrip().endswith("?"):
            return c
    for c in cs:
        low = c.lower()
        if low.startswith(("goal", "question", "query", "which", "what", "is the", "how many")):
            return c
    return cs[-1]


def options_from_text(text: str) -> tuple[str, ...]:
    """An answer vocabulary the text spells out, if it spells one out."""
    for line in str(text).splitlines():
        m = _OPTIONS.search(line)
        if not m:
            continue
        raw = [o.strip().strip(".").strip() for o in _SPLIT_OPTS.split(m.group(1))]
        opts = tuple(o for o in raw if o)
        if len(opts) >= 2:
            return opts
    return ()


def parse_text(text: str, *, max_facts: int = 96) -> Symbol:
    """Text -> the agent's own record: the facts it thinks it read, the clause it
    thinks is the question, and the text itself so nothing is thrown away."""
    q = question_of(text)
    terms = [_atom(t) for t in tokens(q)]
    fields: dict[str, Symbol] = {
        "facts": Lst(facts_from_text(text, max_facts=max_facts)),
        "query": Pred("ask", *terms) if terms else Ident("ask"),
        "utterance": Str(q),
        "text": Str(str(text)[:4000]),
    }
    for name, v in scalars_from_text(text).items():
        fields.setdefault(name, Num(v))
    return Rec(**fields)
