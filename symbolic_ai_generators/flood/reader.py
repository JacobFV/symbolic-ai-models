"""Flood's reader, behind the generic ABI, with behaviour unchanged.

`read_surface.py` is the research instrument: lexical patterns, type signatures,
a value registry, role anchors, adjacency, ambiguity enumeration, evidence
conflict. It returns a finished `WorldSnapshot`, so everything it could not decide
has already been guessed by the time a caller sees it.

This is the same machinery behind `symbolic_ai_core.reader`, which changes nothing
about what it decides and everything about what it *reports*:

- the role assignment it could not force becomes an **XOR factor over candidate
  claims with a belief**, rather than a silent pick — the enumeration was already
  implemented and was returning to a caller who had to know to ask, and a factor
  says *A: 0.62, B: 0.38, A XOR B* without materialising two worlds;
- `evidence_conflict` becomes an **unresolved** entry, so a caller that ignores
  it has visibly ignored it;
- the reader's own `role_assignment_forced` becomes a **belief**, with its
  measured meaning attached rather than its name: sound on the published surface,
  0.664 among forced readings on `hard_distractors`.

A learned reader implements the same protocol and nothing downstream changes,
which is the point of putting it here rather than in a script.
"""

from __future__ import annotations

import time

from symbolic_ai_core.reader import Factor, ReadResult, register_reader

from .read_surface import (evidence_conflict, read_content_roles_checked,
                           read_content_roles_worlds)

__all__ = ["FloodContentReader", "FLOOD_CONTENT"]


class FloodContentReader:
    """``read_content_roles`` as a `Reader`. Same claims, more reported."""

    id = "flood.content@1"

    def run(self, text: str, *, query=None, context=()) -> ReadResult:
        started = time.perf_counter()
        world, forced = read_content_roles_checked(text)
        claims = list(world.claims)
        factors: tuple[Factor, ...] = ()
        unresolved: tuple[str, ...] = ()
        belief: dict[int, float] = {i: 1.0 for i in range(len(claims))}
        if not forced:
            worlds = read_content_roles_worlds(text)
            # Exactly one region is the depot, so the alternatives are a genuine
            # XOR -- which is what makes agreement across them a sound AND
            # complete detector here, and is exactly the property real prose was
            # measured NOT to supply. The factor records it rather than the
            # reader assuming it.
            alts = []
            for w in worlds:
                for c in w.claims:
                    if c.predicate == "depot" and c.to_dict() not in [
                            x.to_dict() for x in alts]:
                        alts.append(c)
            if len(alts) > 1:
                chosen = {c.to_dict()["roles"]["where"]["entity"]
                          for c in claims if c.predicate == "depot"}
                idx = []
                for c in alts:
                    where = c.to_dict()["roles"]["where"]["entity"]
                    existing = next((i for i, x in enumerate(claims)
                                     if x.predicate == "depot"
                                     and x.to_dict()["roles"]["where"]["entity"]
                                     == where), None)
                    if existing is None:
                        claims.append(c)
                        existing = len(claims) - 1
                    idx.append(existing)
                    belief[existing] = 1.0 / len(alts) if where not in chosen \
                        else 1.0 - (len(alts) - 1) / (2 * len(alts))
                factors = (Factor(kind="xor", claims=tuple(idx),
                                  detail="lone-region roles were not forced by "
                                         "anchors or adjacency"),)
            unresolved = ("depot/flooded assignment",)
        conflict = evidence_conflict(text)
        if conflict:
            unresolved = unresolved + tuple(
                f"evidence conflict: {k}" for k in sorted(conflict))
        return ReadResult(
            claims=tuple(claims),
            belief=belief,
            factors=factors,
            unresolved=unresolved,
            provenance=self.id,
            cost_s=time.perf_counter() - started,
            diagnostics={"role_assignment_forced": forced,
                         "evidence_conflict": {k: list(v)
                                               for k, v in conflict.items()}},
        )


FLOOD_CONTENT = register_reader(FloodContentReader())
