"""``P_asp`` : world -> an ASP program, with everything it dropped.

ASP sees the same relational core datalog does, and drops the same things for
the same reasons — a nested proposition, a negated claim, a quantity with a
unit. The projection therefore *reuses the datalog projection* rather than
reimplementing the judgement calls, and then renders what survived as ASP text.

What ASP adds over datalog, and the reason it is ranked above Lean for agent
cognition, is **world completion**: choice rules and integrity constraints turn
"what follows from this world" into "which completions of this world are
admissible". That is already the shape of this repo's central task — a partial
world with something missing, and a space of candidate fillings — so the goal
here is a set of *open* predicates the solver may choose, plus constraints it
must respect.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Iterable, Mapping, Sequence

from symbolic_ai_core.world import WorldSnapshot

from ..abi import Discard, Projection
from ..datalog.project import project_world as project_relational
from .mangle import Mangler, quote

__all__ = ["AspProgram", "project_world", "SEMANTICS"]

SEMANTICS = ("closed_world", "non_monotonic", "defeasible")


class AspProgram:
    """The rendered program, the name bijection, and the open predicates."""

    def __init__(self, text: str, mangler: Mangler,
                 open_predicates: tuple[str, ...]) -> None:
        self.text = text
        self.mangler = mangler
        self.open_predicates = open_predicates

    def __repr__(self) -> str:                                # pragma: no cover
        return f"AspProgram({len(self.text)} chars, " \
               f"{len(self.open_predicates)} open)"


def _domain_atom(spec: Any, var: str, m: Mangler) -> str:
    """A domain as an atom binding ``var``.

    A bare name is a **unary** predicate (``entity``, projected for every
    identity). A relation of higher arity has to say which argument is the
    domain — ``{"pred": "type", "arity": 2, "arg": 0}`` — because guessing the
    first would silently range over the wrong column, and the resulting model is
    perfectly well-formed and about something else.
    """
    if isinstance(spec, str):
        return f"{m.to_solver(spec)}({var})"
    if isinstance(spec, Mapping) and "pred" in spec:
        arity = int(spec.get("arity", 1))
        arg = int(spec.get("arg", 0))
        if not 0 <= arg < arity:
            raise ValueError(f"domain {spec['pred']}: arg {arg} is outside "
                             f"arity {arity}")
        slots = ["_"] * arity
        slots[arg] = var
        return f"{m.to_solver(str(spec['pred']))}({', '.join(slots)})"
    raise ValueError(
        f"a choice domain is a unary predicate name or "
        f"{{'pred': p, 'arity': n, 'arg': i}}, got {spec!r}. A relation of "
        f"arity > 1 must say which column is the domain; guessing the first "
        f"produces a well-formed model of the wrong question.")


def project_world(world: WorldSnapshot, *, program: str = "",
                  choices: Sequence[Mapping[str, Any]] = (),
                  constraints: Sequence[str] = (),
                  ) -> Projection:
    """``P_asp(world)``.

    ``choices`` are the completion space: each is
    ``{"predicate": p, "over": [domain_pred, ...]}``, rendered as a choice rule
    ``{p(X0,...)} :- d0(X0), ....`` ``constraints`` and ``program`` are ASP
    source, passed through verbatim — ASP has syntax (aggregates, optimisation,
    cardinality bounds) that no structured form here would capture, and a
    half-expressive DSL in front of it would be worse than the language.
    """
    rel = project_relational(world)
    m = Mangler()
    lines: list[str] = ["% --- facts projected from the world ---"]
    for fact in sorted(rel.program.facts):
        pred, *terms = fact
        args = ", ".join(quote(t) for t in terms)
        lines.append(f"{m.to_solver(pred)}({args})." if args
                     else f"{m.to_solver(pred)}.")

    discards = list(rel.discarded)
    open_preds: list[str] = []
    if choices:
        lines.append("\n% --- the completion space ---")
    for ch in choices:
        pred = str(ch["predicate"])
        over = list(ch.get("over") or ())
        if not over:
            discards.append(Discard(
                "choice", pred,
                "a choice rule with no domain would range over every constant "
                "that will ever exist, so it has no finite meaning"))
            continue
        try:
            atoms = [_domain_atom(d, f"X{i}", m) for i, d in enumerate(over)]
        except ValueError as err:
            discards.append(Discard("choice", pred, str(err)))
            continue
        vs = [f"X{i}" for i in range(len(over))]
        body = ", ".join(atoms)
        head = f"{m.to_solver(pred)}({', '.join(vs)})"
        bound = ch.get("bounds")
        if bound:
            lo, hi = bound
            lines.append(f"{lo} {{ {head} : {body} }} {hi} :- {body}.")
        else:
            lines.append(f"{{ {head} }} :- {body}.")
        open_preds.append(pred)

    if constraints:
        lines.append("\n% --- integrity constraints ---")
        lines.extend(constraints)
    if program:
        lines.append("\n% --- supplied program ---")
        lines.append(program)

    return Projection(
        kernel="asp@1",
        program=AspProgram("\n".join(lines) + "\n", m, tuple(open_preds)),
        semantics=SEMANTICS,
        covered_entities=rel.covered_entities,
        covered_claims=rel.covered_claims,
        discarded=tuple(discards),
        meta={**rel.meta, "mangled": m.to_dict(),
              "open_predicates": list(open_preds)},
    )
