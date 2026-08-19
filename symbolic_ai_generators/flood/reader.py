"""Flood's reader, behind the generic ABI, with behaviour unchanged.

`read_surface.py` is the research instrument: lexical patterns, type signatures,
a value registry, role anchors, adjacency, ambiguity enumeration, evidence
conflict. It returns a finished `WorldSnapshot`, so everything it could not decide
has already been guessed by the time a caller sees it.

This is the same machinery behind `symbolic_ai_core.reader`, which changes nothing
about what it decides and everything about what it *reports*:

- the role assignment it could not force becomes a **candidate set** rather than
  a silent pick — the enumeration was already implemented and was returning to a
  caller that had to know to ask;
- `evidence_conflict` becomes an **unresolved** entry, so a caller that ignores
  it has visibly ignored it;
- the reader's own `role_assignment_forced` becomes a **confidence**, with its
  measured meaning attached rather than its name: sound on the published surface,
  0.664 among forced readings on `hard_distractors`.

A learned reader implements the same protocol and nothing downstream changes,
which is the point of putting it here rather than in a script.
"""

from __future__ import annotations

import time

from symbolic_ai_core.reader import Candidate, ReadResult, register_reader

from .read_surface import (evidence_conflict, read_content_roles_checked,
                           read_content_roles_worlds)

__all__ = ["FloodContentReader", "FLOOD_CONTENT"]


class FloodContentReader:
    """``read_content_roles`` as a `Reader`. Same claims, more reported."""

    id = "flood.content@1"

    def run(self, text: str, *, query=None, context=()) -> ReadResult:
        started = time.perf_counter()
        world, forced = read_content_roles_checked(text)
        candidates: tuple[Candidate, ...] = ()
        unresolved: tuple[str, ...] = ()
        if not forced:
            worlds = read_content_roles_worlds(text)
            if len(worlds) > 1:
                # Mutually exclusive by construction: exactly one region is the
                # depot. That is what makes agreement across them sound AND
                # complete here, and it is why the flag is on the candidate.
                depots = tuple(c for w in worlds for c in w.claims
                               if c.predicate == "depot")
                candidates = (Candidate(slot="depot", claims=depots,
                                        exclusive=True,
                                        detail="lone-region roles were not "
                                               "forced by anchors or adjacency"),)
            unresolved = ("depot/flooded assignment",)
        conflict = evidence_conflict(text)
        if conflict:
            unresolved = unresolved + tuple(
                f"evidence conflict: {k}" for k in sorted(conflict))
        return ReadResult(
            claims=tuple(world.claims),
            candidates=candidates,
            unresolved=unresolved,
            confidence={i: (1.0 if forced else 0.5)
                        for i in range(len(world.claims))},
            provenance=self.id,
            cost_s=time.perf_counter() - started,
            detail={"role_assignment_forced": forced,
                    "evidence_conflict": {k: list(v)
                                          for k, v in conflict.items()}},
        )


FLOOD_CONTENT = register_reader(FloodContentReader())
