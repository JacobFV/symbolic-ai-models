"""A node's role, read off the space as the queries it satisfies.

``vsa-002`` asserts that the generator's coordinates are ``(ptype, slot, depth,
arity)`` — four numbers a human wrote down. ``vsa_hks-004`` beat that assertion
using nothing but the graph's spectrum (+0.107 against +0.066 on the ``_pure``
rows), which is evidence that the hand-built tuple is not the right
decomposition. This module is the third answer to the same question: a role is
**the set of conjunctive queries a node satisfies**, and an atomspace is a
richer source of those than a four-tuple.

The one rule the query schedule obeys
--------------------------------------
**No query reads the ``label`` relation.** A role built from symbol identity
would make the model non-equivariant by construction and would put the
``_pure`` rows' renaming column back where ``ensemble-001``'s was — 0.467 down
to 0.038, all of it vocabulary. ``tests/test_metta.py`` asserts the property on
the schedule itself rather than trusting this paragraph.

Why signatures are strings and roles are their superposition
-------------------------------------------------------------
Each solution of each query yields a short signature. A node's role is the
**superposition** of one random bipolar atom per signature, which makes

    ``<role_i, role_j> = d * (signature mass shared by i and j)``

— exactly the graded Gram ``vsa_sum-004`` gets from superposing its four atoms
instead of binding them, which was the construction that beat the hard
partition. The difference here is only *which* signatures there are, so the
comparison against ``vsa_sum-004`` is a controlled one: same algebra, same
temperature, same cleanup, a different query schedule.

Cosine, and why the tuple row does not use it
----------------------------------------------
The rich schedule gives different nodes different *numbers* of signatures — a
node with six children has more child-type solutions than a leaf — and an
unnormalised superposition would then give busy nodes a higher Gram against
everyone, which is a popularity bias rather than a role. So the rich rows
normalise each role to a fixed norm, making the Gram a cosine: *the fraction of
role shared*. :data:`TUPLE_QUERIES` deliberately does **not**, because every
node has exactly four signatures under it and turning normalisation on there
would change the contrast against ``vsa_sum-004`` from "the schedule" to "the
schedule and the normalisation".

Depth, and the one place the hot path does not use the query engine
--------------------------------------------------------------------
Depth is the length of a node's ancestor chain. In the space that is a bounded
transitive rule::

    (= (anc $a $c) (child $a $k $c))
    (= (anc $a $c) (, (anc $a $b) (child $b $k $c)))

and counting solutions gives the depth. Chaining that closure costs ``O(n d)``
atoms and a join per round on every view of every fitting pass, which is real
money inside a sweep. So :func:`role_signatures` walks the parent chain
directly, and ``tests/test_metta.py`` asserts the two agree on real graphs.
Stated here rather than buried: the hot path computes the same relation the
rules define, and the equality is a test rather than a comment.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

from .atoms import Atom, parse_atom
from .space import AtomSpace
from .unify import Bindings

__all__ = ["RoleQuery", "ROLE_QUERIES", "TUPLE_QUERIES", "role_signatures",
           "child_type_key", "node_index", "ANCESTOR_RULES_SOURCE"]


@dataclass(frozen=True)
class RoleQuery:
    """A conjunctive query plus how each of its solutions names a role feature.

    ``patterns`` must bind ``$q`` — the node the role is *for*. Everything is
    read out of one match over the space per query, not one per node: a MeTTa
    ``match`` returns every binding at once and the caller buckets them, which
    is what keeps this linear in solutions rather than in nodes times solutions.
    """

    name: str
    source: tuple[str, ...]
    render: Callable[[Bindings], tuple[str, ...]]

    @property
    def patterns(self) -> tuple[Atom, ...]:
        return tuple(parse_atom(s) for s in self.source)

    def reads_labels(self) -> bool:
        """Whether any pattern mentions the ``label`` relation. Must be False."""
        return any("(label " in s for s in self.source)


def _val(atom: Atom, default: object = None) -> object:
    return getattr(atom, "value", getattr(atom, "name", default))


def _cap(v: object, hi: int) -> int:
    try:
        return min(int(v), hi)                                # type: ignore[arg-type]
    except (TypeError, ValueError):                          # pragma: no cover
        return 0


# ---------------------------------------------------------------------------
# the four hand-built coordinates, expressed as queries
# ---------------------------------------------------------------------------
#: ``vsa-002``'s assertion about the generator, re-expressed. Nothing new is
#: said here; the row built on it exists to check that saying the old thing in
#: the new notation reproduces the old number, which is the harness check this
#: whole line rests on. ``depth`` and ``arity`` are aggregates over solutions
#: rather than solutions, so they are supplied by :func:`role_signatures`
#: directly and are listed here only for the record.
_PARENT_TYPE = RoleQuery(
    "parent_type", ("(child $p $k $q)", "(: $p $t)"),
    lambda b: (f"pt:{_val(b['t'])}", f"sl:{_cap(_val(b['k']), 11)}"))

_ROOT = RoleQuery(
    "root", ("(root $q)",),
    lambda b: ("pt:ROOT", "sl:0"))

TUPLE_QUERIES: tuple[RoleQuery, ...] = (_PARENT_TYPE, _ROOT)

# ---------------------------------------------------------------------------
# what the atomspace can say and the four-tuple cannot
# ---------------------------------------------------------------------------
#: The child's type, keyed by the slot it sits in. ``vsa-002`` sees only
#: ``arity`` — *how many* children — and nothing about what they are. This is
#: the downward direction, which no role in this repo has ever had.
_CHILD_TYPE = RoleQuery(
    "child_type", ("(child $q $k $c)", "(: $c $t)"),
    lambda b: (f"ct:{_cap(_val(b['k']), 11)}/{_val(b['t'])}",
               f"ck:{_val(b['t'])}"))

#: **The typed, slot-selected sibling.** ``CLAWS`` has ``sibling0`` and
#: ``prev_sibling`` and cannot name which sibling; ``ilp``'s strongest
#: discovered clause is exactly this, and ``omegaclaw_reach-001`` had to add a
#: branch to reach it — and still lost, which is the measured reason the
#: pre-registration predicts this line loses on label accuracy. The offset is
#: signed and capped, so "the sibling two slots to my left, and it is a `pred`"
#: is one feature.
_SIBLING_TYPE = RoleQuery(
    "sibling_type", ("(child $p $k $q)", "(child $p $j $s)", "(: $s $t)"),
    lambda b: ()
    if _val(b["k"]) == _val(b["j"]) else
    (f"sb:{max(-4, min(4, int(_val(b['j'], 0)) - int(_val(b['k'], 0))))}"
     f"/{_val(b['t'])}",
     f"sk:{_val(b['t'])}"))

#: Grandparent type with both slots on the path down. ``depth`` says how far
#: from the root a node is; this says what the two steps above it *were*.
_GRANDPARENT = RoleQuery(
    "grandparent", ("(child $g $a $p)", "(child $p $k $q)", "(: $g $t)"),
    lambda b: (f"gp:{_val(b['t'])}/{_cap(_val(b['a']), 11)}"
               f"/{_cap(_val(b['k']), 11)}",
               f"gt:{_val(b['t'])}"))

#: The parent's own parent-slot: "I am argument 0 of something that is itself
#: argument 1 of something". A path, not a position.
_PARENT_SLOT = RoleQuery(
    "parent_slot", ("(child $g $a $p)", "(child $p $k $q)"),
    lambda b: (f"ps:{_cap(_val(b['a']), 11)}/{_cap(_val(b['k']), 11)}",))

#: Every query the ``metta-005`` role reads. Order is fixed and iteration is
#: over a tuple, because a set here would make the signature multiset depend on
#: hash randomisation between processes — a failure this repo has already had.
ROLE_QUERIES: tuple[RoleQuery, ...] = (
    _PARENT_TYPE, _ROOT, _CHILD_TYPE, _SIBLING_TYPE, _GRANDPARENT, _PARENT_SLOT)


def node_index(space: AtomSpace) -> dict[Atom, int]:
    """Occurrence atom -> its position in the node array."""
    return {b["id"]: int(_val(b["i"], -1))                    # type: ignore[arg-type]
            for b in space.query(parse_atom("(node $id $i)"))}


def child_type_key(space: AtomSpace, n: int) -> list[tuple[str, ...]]:
    """The multiset of child types per node, as a sorted tuple.

    Split out from the role schedule because the **type head** wants it as a
    lookup key rather than as a superposed feature, and design rule 1 says the
    label and type heads do not share machinery. They share this one derived
    quantity and nothing else — a query result is data, not a mechanism.

    This is the direction no baseline here can see. ``node_context`` — the tuple
    the masked-node floor, the shared back-off and ``OmegaClaw.perceive`` all
    key on — is ``(parent type, slot, depth, has children)``: entirely upward,
    plus a single bit of arity. What a node *contains* has never been a feature
    of anything in this repo, and a node whose children are ``char`` atoms is a
    ``str`` whatever sits above it.
    """
    index = node_index(space)
    kids: list[list[str]] = [[] for _ in range(n)]
    types: dict[Atom, str] = {}
    for b in space.query(parse_atom("(: $q $t)")):
        types[b["q"]] = str(_val(b["t"], ""))
    for b in space.query(parse_atom("(child $p $k $c)")):
        p = index.get(b["p"])
        if p is not None and 0 <= p < n:
            kids[p].append(types.get(b["c"], "?"))
    return [tuple(sorted(k)) for k in kids]


def role_signatures(space: AtomSpace, n: int,
                    queries: Sequence[RoleQuery] = ROLE_QUERIES,
                    *, with_depth_and_arity: bool = True) -> list[list[str]]:
    """``[signatures of node 0, signatures of node 1, ...]``.

    One match per query over the whole space, bucketed by the node ``$q`` bound
    to. ``depth`` and ``arity`` are aggregates rather than solutions and are
    added here so that :data:`TUPLE_QUERIES` reproduces ``vsa-002``'s four
    coordinates exactly.
    """
    index = node_index(space)
    out: list[list[str]] = [[] for _ in range(n)]
    for query in queries:
        patterns = query.patterns
        for bindings in space.query(*patterns):
            i = index.get(bindings.get("q"))
            if i is None or not (0 <= i < n):
                continue
            out[i].extend(query.render(bindings))

    if with_depth_and_arity:
        parent = [-1] * n
        arity = [0] * n
        for b in space.query(parse_atom("(child $p $k $c)")):
            c = index.get(b["c"])
            p = index.get(b["p"])
            if c is not None and p is not None and 0 <= c < n and 0 <= p < n:
                parent[c] = p
                arity[p] += 1
        for i in range(n):
            depth, walk, guard = 0, parent[i], 0
            while walk >= 0 and guard < n:
                depth += 1
                walk = parent[walk]
                guard += 1
            out[i].append(f"dp:{min(depth, 11)}")
            out[i].append(f"ar:{min(arity[i], 5)}")
    return out


# Kept importable for the test that pins the hot path against the rule form.
ANCESTOR_RULES_SOURCE = (
    "(= (anc $a $c) (child $a $k $c))",
    "(= (anc $a $c) (, (anc $a $b) (child $b $k $c)))",
)
