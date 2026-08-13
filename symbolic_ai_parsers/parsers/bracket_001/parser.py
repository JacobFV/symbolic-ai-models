"""``bracket-001``: the document's layout, read as a record. Nothing learned.

The trivial baseline every other parser has to beat. It knows four things, all
of them written down rather than induced:

* a prompt is a record;
* a line that is not a bullet starts a block, and the text before its first
  colon names the block's field;
* bullets and semicolon-separated segments under a block are a list of items;
* an item is a predicate whose head is its first word and whose arguments are
  the rest.

Three of those four are right about this curriculum and one — head-is-first-word
— is wrong far more often than it is right (``dave outranks erin`` puts the head
second). It is left wrong on purpose: a baseline whose every rule was checked
against the answer is not a baseline, and the interesting question is how much
of the score is available from layout alone with the labels essentially random.

No language words appear anywhere in it, so it transfers across languages by
construction. That makes it the right control for the cross-language claim: any
drop it shows is a drop in *layout*, not in vocabulary.
"""

from __future__ import annotations

import re

from symbolic_ai_core.data.graph import Graph

from ...base import Parser, register
from ...features import normalise
from ...features import words_of as _words

_BULLET = re.compile(r"^\s*[-*•]\s*(?P<body>.*)$")
_DIGITS = re.compile(r"^\d+$")
MAX_NODES = 512


def slug(text: str) -> str:
    parts = _words(text)
    return "_".join(parts[:6]).lower()


def _atom_type(token: str) -> str:
    return "num" if _DIGITS.match(token) else "ident"


@register("bracket-001", learned=False,
          doc="Blocks, bullets and semicolons as a record of lists. Written down.")
class BracketParser(Parser):
    """Layout to record; first word of an item is guessed to be its head."""

    def parse(self, text: str) -> Graph:
        g = Graph()
        root = g.add("", "record", -1, 0)
        for slot, (header, items) in enumerate(_blocks(normalise(text))):
            if len(g) >= MAX_NODES:
                break
            self._emit_block(g, root, slot, header, items)
        return g

    def _emit_block(self, g: Graph, root: int, slot: int, header: str,
                    items: list[str]) -> None:
        name = slug(header)
        if not name and not items:
            return
        f = g.add(name, "field", root, slot)
        if not items:
            g.add(name, "ident", f, 0)
            return
        lst = g.add("", "list", f, 0)
        for k, item in enumerate(items):
            if len(g) >= MAX_NODES:
                return
            toks = _words(item)
            if not toks:
                continue
            p = g.add(toks[0].lower(), "pred", lst, k)
            for a, tok in enumerate(toks[1:]):
                if len(g) >= MAX_NODES:
                    return
                g.add(tok.lower(), _atom_type(tok), p, a)


def _blocks(text: str) -> list[tuple[str, list[str]]]:
    """``(header, items)`` per block. Items come from bullets, or from splitting
    the header's own tail on ``;`` when the block is written inline."""
    out: list[tuple[str, list[str]]] = []
    for line in text.split("\n"):
        if not line.strip():
            continue
        m = _BULLET.match(line)
        if m and out:
            out[-1][1].append(m.group("body"))
            continue
        if m:
            out.append(("", [m.group("body")]))
            continue
        head, sep, tail = line.partition(":")
        items = [s for s in (p.strip() for p in tail.split(";")) if s] if sep else []
        out.append((head if sep else line, items))
    return out
