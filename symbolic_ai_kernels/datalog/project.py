"""``P_datalog`` : world -> ground atoms and rules, with everything it dropped.

Datalog is flat, untyped, positive and closed-world. A world IR claim is none of
those things: it is n-ary with *named* roles, it may nest, it carries a modality,
a polarity, a confidence and two time intervals, and its roles may be quantities
with units. Projecting it therefore loses a lot, and this module's real job is
to be **specific about what**.

The distinction that matters is between a claim that cannot be carried at all
and a claim that is carried with its qualifications stripped:

* a nested proposition, a hypothesis, or a negated claim is **not projected**.
  Asserting *casey believes p* as the fact ``p`` would be a lie, and asserting a
  negative claim as a positive fact inverts it.
* a claim with a confidence of 0.6, or one that holds only during 2026, **is**
  projected — as a hard, untimed fact — and the confidence and the interval are
  recorded as discards. The kernel is entitled to reason about the structure it
  covered; the discard record is what lets a consumer decide whether an answer
  that ignored a 0.6 is an answer to their question.

Role names survive in the projection's ``meta["roles"]`` so that a derived fact
can be translated back into a claim with the role names it started with, rather
than into ``arg0`` and ``arg1``.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from symbolic_ai_core.world import Claim, EntityRef, Quantity, WorldSnapshot

from ..abi import Discard, Projection
from .engine import Atom, Fact, Literal, Program, Rule, Var

__all__ = ["project_world", "rules_from_world", "rule_from_dict", "DatalogProgram"]

#: Semantics the projection is valid under. Recorded on the Projection so that a
#: consumer combining this with a classical kernel can notice the mismatch.
SEMANTICS = ("closed_world", "non_monotonic")


class DatalogProgram:
    """The projected program: rules plus the extensional facts they run over."""

    def __init__(self, program: Program, facts: set[Fact]) -> None:
        self.program = program
        self.facts = facts

    def __repr__(self) -> str:                                # pragma: no cover
        return f"DatalogProgram({len(self.program.rules)} rules, " \
               f"{len(self.facts)} facts)"


def _scalar(v: Any) -> str | None:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, str):
        return v
    if isinstance(v, (int, float)):
        return str(v)
    return None


def rule_from_dict(d: Mapping[str, Any]) -> Rule:
    """A rule as plain JSON, so ``logic.rule`` facets can carry one.

    Terms are tagged — ``{"var": "x"}`` or ``{"const": "a"}`` — for the same
    reason a claim role is tagged: a bare string cannot say whether it is a
    variable or a constant, and guessing from capitalisation is a convention
    that breaks the first time an entity id is capitalised.
    """
    def term(t: Any) -> Any:
        if isinstance(t, Mapping):
            if "var" in t:
                return Var(str(t["var"]))
            if "const" in t:
                return str(t["const"])
        raise ValueError(f"a datalog term is {{'var': ...}} or {{'const': ...}}, "
                         f"got {t!r}")

    def atom(a: Mapping[str, Any]) -> Atom:
        return Atom(str(a["pred"]), tuple(term(t) for t in a.get("terms") or ()))

    return Rule(head=atom(d["head"]),
                body=tuple(Literal(atom(b), bool(b.get("negated", False)))
                           for b in d.get("body") or ()))


def rules_from_world(world: WorldSnapshot) -> tuple[list[Rule], list[Discard]]:
    """Rules carried by entities with a ``logic.rule`` facet."""
    rules: list[Rule] = []
    discards: list[Discard] = []
    for eid, e in sorted(world.entities.items()):
        facet = e.facet("logic.rule")
        if facet is None:
            continue
        for spec in (facet.values.get("rules") or []):
            try:
                rules.append(rule_from_dict(spec))
            except (ValueError, KeyError) as err:
                discards.append(Discard("rule", eid, f"malformed rule: {err}"))
    return rules, discards


def project_world(world: WorldSnapshot, *, extra_rules: Iterable[Rule] = (),
                  ) -> Projection:
    """``P_datalog(world)``."""
    facts: set[Fact] = set()
    discards: list[Discard] = []
    covered_entities: set[str] = set()
    covered_claims: list[int] = []
    roles: dict[str, list[str]] = {}

    # --- entity types and profiles ------------------------------------
    for eid, e in sorted(world.entities.items()):
        for t in e.types:
            facts.add(("type", eid, t))
        for profile, facet in sorted(e.facets.items()):
            facts.add(("has_profile", eid, profile))
            for k, v in sorted(facet.values.items()):
                s = _scalar(v)
                if s is None:
                    discards.append(Discard(
                        "facet", f"{eid}.{profile}.{k}",
                        f"a {type(v).__name__} value has no datalog term; only "
                        f"scalars project"))
                else:
                    facts.add(("attr", eid, f"{profile}.{k}", s))
        covered_entities.add(eid)

    # --- claims -------------------------------------------------------
    for i, c in enumerate(world.claims):
        keep, why = _projectable(c)
        if not keep:
            discards.append(Discard("claim", str(i), why))
            continue
        names = sorted(c.roles)
        terms: list[str] = []
        bad = ""
        for name in names:
            v = c.roles[name]
            if isinstance(v, EntityRef):
                terms.append(v.id)
                covered_entities.add(v.id)
            elif isinstance(v, Quantity):
                bad = (f"role {name!r} is a Quantity ({v.value} {v.unit}); "
                       f"datalog is untyped and projecting it would drop the "
                       f"unit")
                break
            else:
                s = _scalar(v)
                if s is None:
                    bad = (f"role {name!r} is a {type(v).__name__}, which has "
                           f"no datalog term")
                    break
                terms.append(s)
        if bad:
            discards.append(Discard("claim", str(i), bad))
            continue
        facts.add((c.predicate, *terms))
        roles.setdefault(c.predicate, names)
        covered_claims.append(i)
        discards.extend(_qualification_losses(c, i))

    rules, rule_discards = rules_from_world(world)
    rules.extend(extra_rules)
    discards.extend(rule_discards)

    return Projection(
        kernel="datalog@1",
        program=DatalogProgram(Program(tuple(rules)), facts),
        semantics=SEMANTICS,
        covered_entities=frozenset(covered_entities),
        covered_claims=tuple(covered_claims),
        discarded=tuple(discards),
        meta={"roles": roles, "n_facts": len(facts), "n_rules": len(rules)},
    )


def _projectable(c: Claim) -> tuple[bool, str]:
    if any(isinstance(v, Claim) for v in c.roles.values()):
        return False, ("a nested proposition has no flat datalog atom; "
                       "asserting the inner claim as a fact would drop the "
                       "outer one's meaning entirely")
    if c.polarity == "negative":
        return False, ("an explicitly negative claim is not negation-as-"
                       "failure; projecting it as a fact would assert its "
                       "opposite")
    if c.modality != "asserted":
        return False, (f"modality {c.modality!r}: datalog has one modality and "
                       f"projecting this as a fact would turn a "
                       f"{c.modality} into a measurement")
    return True, ""


def _qualification_losses(c: Claim, i: int) -> list[Discard]:
    """What a projected claim carried that the fact does not."""
    out = []
    if c.confidence is not None and c.confidence < 1.0:
        out.append(Discard("uncertainty", str(i),
                           f"confidence {c.confidence} projected as a hard fact"))
    if c.valid_time.start or c.valid_time.end:
        out.append(Discard("valid_time", str(i),
                           f"holds {c.valid_time.start}..{c.valid_time.end}, "
                           f"projected as untimed"))
    if c.scope:
        out.append(Discard("scope", str(i),
                           f"asserted in scope {c.scope!r}, projected globally"))
    return out
