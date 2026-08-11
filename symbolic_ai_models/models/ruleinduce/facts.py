"""Facts, frames and literals: the substrate every symbolic learner here shares.

Ported from symbolic-ai-001 (`induction/facts.py`); the symbol import is
repointed at `base_symbolic_002`, which owns that algebra here.


Three ideas, in order of importance.

**Facts.** Any *parsed* symbol flattens to a set of ground facts
``(predicate, arg, arg, …)`` plus named scalars. Nothing about any task is
assumed; we only walk the symbol structure.

**Frames.** A fact set is expressed in *some* frame of reference. Re-expressing
numeric arguments relative to an anchor entity (``at(agent,3,4)`` →
``rel_wall(+1,0)``) is the symbolic analogue of translational equivariance: it
makes a hypothesis learned in a 5×5 world literally the same hypothesis in a
20×20 world. This is where symbolic generalization comes from, and it is an
explicit, named, swappable choice rather than something a network has to
rediscover from data.

**Literals.** A literal is an existence test over facts with per-argument
constraints (equals-a-constant, sign of a number, wildcard). Conjunctions of a
few literals form the hypothesis language for rule induction. The language is
generated *from the data*, so nothing is hardcoded per environment.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Iterator, Mapping, Sequence

from ...parsers.primitives.symbols import Symbol, walk

__all__ = ["Fact", "FactSet", "facts_of", "anchor_frame", "Literal", "Constraint",
           "candidate_literals", "ANY", "Eq", "Sign"]

Fact = tuple  # (pred:str, *args) with args being str | int | float


# --------------------------------------------------------------------------
# extraction
# --------------------------------------------------------------------------
def _atom(s: Symbol) -> Any:
    if s.type in ("num",):
        v = s.value
        return int(v) if isinstance(v, float) and float(v).is_integer() else v
    if s.type in ("ident", "token", "str"):
        return s.value
    return None


def facts_of(obs: Symbol) -> "FactSet":
    """Flatten an observation into ground facts + named scalars.

    * every ``pred``/``rel``/``node`` symbol becomes ``(name, *atomic args)``
    * every record field with an atomic value becomes a scalar
    * bare identifiers inside a named list become ``(field, value)`` facts
    """
    facts: set[Fact] = set()
    scalars: dict[str, Any] = {}
    order = {"n": 0}          # preorder counter: structure is position, and a
                              # tree that flattens to an unordered bag of leaves
                              # has had its structure destroyed before any
                              # learner sees it

    def visit(s: Symbol, field: str | None, nested: bool = False) -> None:
        if s.type in ("pred", "rel", "node"):
            head = s.value[0]
            args = tuple(_atom(c) for c in s.children)
            if all(a is not None for a in args):
                facts.add((str(head), *args))
                if nested:
                    # only where structure would otherwise be lost: a nested node
                    # in a tree has a position, a fact in a flat scene does not,
                    # and adding a spurious index to the latter would destroy the
                    # translation invariance the anchor frame depends on
                    facts.add((f"{head}_at", order["n"], *args))
                    order["n"] += 1
            else:                       # nested structure: keep the head as a marker
                facts.add((str(head),))
                for c in s.children:
                    visit(c, field, nested=True)
            return
        if s.type == "record":
            for k, v in s.value:
                a = _atom(v)
                if a is not None:
                    scalars[str(k)] = a
                else:
                    # descending from a field straight into a predicate is a
                    # structure (a tree), so its root is positioned too
                    visit(v, str(k), nested=(v.type in ("pred", "rel", "node")))
            return
        if s.type in ("list", "tuple"):
            for i, c in enumerate(s.children):
                a = _atom(c)
                if a is not None and field:
                    facts.add((field, a))
                    # position is meaning in a sequence; without it, "the third
                    # symbol" is not expressible at all
                    facts.add((f"{field}_at", i, a))
                else:
                    visit(c, field)
            return
        if s.type == "app":
            fn, *kvs = s.value
            facts.add((f"call:{fn}",))
            for k, v in kvs:
                a = _atom(v)
                if a is not None:
                    facts.add((f"arg:{fn}:{k}", a))
        # atoms outside a list contribute nothing on their own

    visit(obs, None)
    return FactSet(frozenset(facts), scalars, obs)


@dataclass(frozen=True)
class FactSet:
    facts: frozenset
    scalars: Mapping[str, Any]
    source: Any = None          # the observation symbol, for programs that must
                                # walk the tree rather than its flattening

    def by_pred(self, pred: str) -> list[Fact]:
        return sorted((f for f in self.facts if f[0] == pred), key=str)

    def preds(self) -> set[str]:
        return {f[0] for f in self.facts}

    def __contains__(self, f: Fact) -> bool:
        return f in self.facts

    def __len__(self) -> int:
        return len(self.facts)

    def render(self, limit: int = 12) -> str:
        fs = sorted(str(f) for f in self.facts)[:limit]
        return " ".join(fs) + (f" …(+{len(self.facts)-limit})" if len(self.facts) > limit else "")


# --------------------------------------------------------------------------
# frames
# --------------------------------------------------------------------------
def anchor_frame(fs: FactSet, anchor_pred: str = "at", anchor_key: Any = "agent") -> FactSet:
    """Re-express numeric facts relative to an anchor entity.

    ``at(agent,3,4)`` + ``wall(4,4)`` → ``rel:wall(1,0)`` and ``self:at()``.
    Facts with a different numeric arity than the anchor are left alone.

    A hypothesis expressed in this frame is automatically translation-invariant,
    which is exactly what lets a rule induced on a small world transfer to a
    large one.
    """
    anchors = [f for f in fs.by_pred(anchor_pred) if len(f) > 2 and f[1] == anchor_key]
    if not anchors:
        return fs
    a = anchors[0]
    nums = [i for i, v in enumerate(a) if isinstance(v, (int, float))]
    if not nums:
        return fs
    origin = [a[i] for i in nums]
    out: set[Fact] = set()
    for f in fs.facts:
        if f is a:
            out.add(("self", *[str(x) for x in f[1:len(f) - len(nums)]]))
            continue
        fnums = [i for i, v in enumerate(f) if isinstance(v, (int, float))]
        if len(fnums) == len(nums) and fnums:
            rel = list(f)
            for k, i in enumerate(fnums):
                rel[i] = f[i] - origin[k]
            out.add(("rel:" + str(rel[0]), *rel[1:]))
        else:
            out.add(f)
    return FactSet(frozenset(out), dict(fs.scalars))


# --------------------------------------------------------------------------
# literals
# --------------------------------------------------------------------------
class Constraint:
    def holds(self, v: Any) -> bool:  # pragma: no cover - overridden
        raise NotImplementedError

    def cost(self) -> int:
        return 1


class _Any(Constraint):
    def holds(self, v: Any) -> bool:
        return True

    def cost(self) -> int:
        return 0

    def __repr__(self) -> str:
        return "_"


ANY = _Any()


@dataclass(frozen=True)
class Eq(Constraint):
    value: Any

    def holds(self, v: Any) -> bool:
        return v == self.value

    def __repr__(self) -> str:
        return f"={self.value}"


@dataclass(frozen=True)
class Sign(Constraint):
    op: str          # "+", "-", "0", "<=", ">="

    def holds(self, v: Any) -> bool:
        if not isinstance(v, (int, float)):
            return False
        return {"+": v > 0, "-": v < 0, "0": v == 0, ">=": v >= 0, "<=": v <= 0}[self.op]

    def __repr__(self) -> str:
        return {"+": ">0", "-": "<0", "0": "==0", ">=": ">=0", "<=": "<=0"}[self.op]


@dataclass(frozen=True)
class Literal:
    """``∃ fact: pred matches and every argument satisfies its constraint``."""

    pred: str
    args: tuple[Constraint, ...]
    negated: bool = False

    def holds(self, fs: FactSet) -> bool:
        found = False
        for f in fs.facts:
            if f[0] != self.pred or len(f) - 1 != len(self.args):
                continue
            if all(c.holds(v) for c, v in zip(self.args, f[1:])):
                found = True
                break
        return (not found) if self.negated else found

    def cost(self) -> int:
        return 1 + sum(c.cost() for c in self.args)

    def __repr__(self) -> str:
        inner = ",".join(repr(c) for c in self.args)
        return ("¬" if self.negated else "") + f"{self.pred}({inner})"


def candidate_literals(
    examples: Sequence[FactSet],
    *,
    max_constants: int = 8,
    numeric_signs: Sequence[str] = ("+", "-", "0"),
    include_negations: bool = True,
    max_literals: int = 400,
) -> list[Literal]:
    """Generate the hypothesis language *from the observed facts*.

    For every (predicate, arity) seen, emit literals that constrain at most two
    argument positions: symbolic positions by an observed constant, numeric
    positions by sign. Nothing task-specific is written down anywhere.
    """
    shapes: dict[tuple[str, int], list[set]] = {}
    for fs in examples:
        for f in fs.facts:
            key = (f[0], len(f) - 1)
            cols = shapes.setdefault(key, [set() for _ in range(len(f) - 1)])
            for i, v in enumerate(f[1:]):
                if len(cols[i]) <= max_constants * 4:
                    cols[i].add(v)

    lits: list[Literal] = []
    for (pred, arity), cols in sorted(shapes.items()):
        base = tuple(ANY for _ in range(arity))
        lits.append(Literal(pred, base))
        per_pos: list[list[tuple[int, Constraint]]] = []
        for i, vals in enumerate(cols):
            opts: list[tuple[int, Constraint]] = []
            numeric = all(isinstance(v, (int, float)) for v in vals) and vals
            if numeric:
                opts += [(i, Sign(s)) for s in numeric_signs]
                for v in sorted(vals, key=lambda x: abs(x))[:max_constants]:
                    opts.append((i, Eq(v)))
            else:
                for v in sorted(vals, key=lambda x: str(x))[:max_constants]:
                    opts.append((i, Eq(v)))
            per_pos.append(opts)
        flat = [o for opts in per_pos for o in opts]
        for i, c in flat:                                   # one constraint
            args = list(base)
            args[i] = c
            lits.append(Literal(pred, tuple(args)))
        for a in range(len(per_pos)):                       # two constraints
            for b in range(a + 1, len(per_pos)):
                for i, ci in per_pos[a][:6]:
                    for j, cj in per_pos[b][:6]:
                        args = list(base)
                        args[i], args[j] = ci, cj
                        lits.append(Literal(pred, tuple(args)))
    if include_negations:
        lits = lits + [Literal(l.pred, l.args, True) for l in lits]
    # prefer cheap (more general) literals when truncating
    lits.sort(key=lambda l: (l.cost(), repr(l)))
    return lits[:max_literals]
