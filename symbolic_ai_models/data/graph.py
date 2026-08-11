"""The episode's term tree, flattened into a graph a model can read.

``langcurriculum`` builds every episode as a typed term before it renders it as
prose, and exposes that term as plain JSON through ``Lesson.structured``. This
module turns that JSON into a flat node array plus a parent pointer, which is
all a batch needs: everything else a model might want — who is whose child, how
deep a node sits, which relation holds between two positions — is derived from
the parent pointer in :mod:`symmodels.data.batch`.

Two decisions worth stating, because they shape what the masked-node task
actually measures:

* **Named fields become nodes.** A record ``{query: ..., scene: ...}`` yields a
  ``field`` node labelled ``query`` above the value. Field names are then
  maskable, so "which role does this subtree play" is a question the task can
  ask, rather than a fact wired into the encoding.
* **Strings are exploded.** ``{"t": "str", "v": "(())))"}`` is a leaf carrying
  the whole content of a lesson like ``context_free_language``; left whole, its
  graph has three nodes and nothing to predict. Split into one child per
  symbol, the string's structure is present in the graph exactly as it is
  present in the text.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .tokenizer import split_words

__all__ = ["Graph", "NODE_TYPES", "TYPE_TO_ID", "graph_from_json", "STRUCTURAL"]

#: Every node type a graph position can carry. ``pad`` and ``mask`` come first
#: so that the masked-node task can write ``TYPE_TO_ID["mask"]`` into an input
#: without colliding with a real term type. ``text`` is the type every position
#: of a running-text sequence carries, so that one embedding table serves both
#: tasks.
NODE_TYPES = (
    "pad", "mask", "text",
    "token", "str", "num", "ident", "nil",
    "tuple", "list", "record", "app", "pred", "rel", "node",
    "field", "char",
)
TYPE_TO_ID = {t: i for i, t in enumerate(NODE_TYPES)}

#: Types whose label carries no symbol — a list is a list. These are excluded
#: from the label half of the masked-node loss, since "predict the empty label"
#: is free and would inflate the score.
STRUCTURAL = frozenset({"tuple", "list", "record", "app", "nil"})

#: A string longer than this is truncated when exploded into child nodes.
MAX_STRING_PIECES = 128


@dataclass
class Graph:
    """A term tree as flat arrays. ``parent[0]`` is ``-1``; nodes are pre-order."""

    labels: list[str] = field(default_factory=list)
    types: list[str] = field(default_factory=list)
    parent: list[int] = field(default_factory=list)
    slot: list[int] = field(default_factory=list)
    depth: list[int] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.labels)

    def add(self, label: str, type_: str, parent: int, slot: int) -> int:
        i = len(self.labels)
        self.labels.append(label)
        self.types.append(type_)
        self.parent.append(parent)
        self.slot.append(slot)
        self.depth.append(0 if parent < 0 else self.depth[parent] + 1)
        return i

    def to_dict(self) -> dict[str, Any]:
        return {"labels": self.labels, "types": self.types, "parent": self.parent,
                "slot": self.slot, "depth": self.depth}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Graph":
        return cls(labels=list(d["labels"]), types=list(d["types"]),
                   parent=list(d["parent"]), slot=list(d["slot"]),
                   depth=list(d["depth"]))

    def sexpr(self, root: int = 0) -> str:
        """Re-render as an s-expression. Used by tests and by ``inspect``."""
        kids = [i for i, p in enumerate(self.parent) if p == root]
        head = self.labels[root] or self.types[root]
        if not kids:
            return head
        return "(" + " ".join([head] + [self.sexpr(k) for k in kids]) + ")"


def _label_of(node: dict[str, Any]) -> str:
    t = node.get("t")
    if t in ("pred", "rel", "node"):
        return str(node.get("head", ""))
    if t == "app":
        return str(node.get("fn", ""))
    if t in ("token", "ident", "str", "field", "char"):
        return str(node.get("v", ""))
    if t == "num":
        return _num_label(node.get("v"))
    return ""


def _num_label(v: Any) -> str:
    """Numbers are labels too. Integers keep their identity; floats are rounded
    to three places, so that ``0.5000000001`` and ``0.5`` are the same symbol."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    return str(int(f)) if f.is_integer() else f"{f:.3f}"


def graph_from_json(obs: Any, *, explode_strings: bool = True,
                    max_nodes: int = 512) -> Graph:
    """Build a :class:`Graph` from ``Lesson.structured(...)["observation"]``.

    Traversal is breadth-first-bounded rather than depth-first, so a graph that
    hits ``max_nodes`` loses its deepest detail rather than losing whole
    top-level fields — truncating a scene down to its first object would change
    what the episode is about.
    """
    g = Graph()
    queue: list[tuple[Any, int, int]] = [(obs, -1, 0)]
    while queue and len(g) < max_nodes:
        node, parent, slot = queue.pop(0)
        idx, children = _emit(g, node, parent, slot, explode_strings)
        queue.extend((c, idx, k) for k, c in enumerate(children))
    return g


def _emit(g: Graph, node: Any, parent: int, slot: int,
          explode_strings: bool) -> tuple[int, list[Any]]:
    """Append one node and return ``(its index, its children)``."""
    if not isinstance(node, dict):
        # `to_json` passes plain lists and scalars through untouched.
        if isinstance(node, list):
            idx = g.add("", "list", parent, slot)
            return idx, list(node)
        return g.add(_num_label(node) if isinstance(node, (int, float)) else str(node),
                     "token", parent, slot), []

    t = str(node.get("t", "token"))
    t = t if t in TYPE_TO_ID else "token"
    idx = g.add(_label_of(node), t, parent, slot)

    if t == "str" and explode_strings:
        return idx, [{"t": "char", "v": p}
                     for p in _string_pieces(str(node.get("v", "")))]
    if t in ("pred", "rel", "node"):
        return idx, list(node.get("args") or [])
    if t in ("tuple", "list"):
        return idx, list(node.get("items") or [])
    if t in ("record", "app"):
        # A named field becomes its own node, so the name is predictable.
        src = node.get("fields") if t == "record" else node.get("args")
        kids: list[Any] = []
        for k, v in sorted((src or {}).items()):
            kids.append({"t": "field", "v": k, "_child": v})
        return idx, kids
    if t == "field":
        return idx, [node["_child"]] if node.get("_child") is not None else []
    return idx, []


def _string_pieces(s: str) -> list[str]:
    """Split a string-valued term into the symbols it is made of.

    Prose splits into words; a bracket string splits into brackets. Both go
    through the same splitter, so no lesson gets a special case.
    """
    pieces = split_words(s)
    if not pieces:                                   # whitespace-only or empty
        pieces = list(s)
    return pieces[:MAX_STRING_PIECES]
