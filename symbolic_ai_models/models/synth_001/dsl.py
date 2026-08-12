"""Enumerative program synthesis with observational-equivalence pruning.

Ported verbatim from symbolic-ai-001 (`agents/seq_synth_001/dsl.py`).

The hypothesis is a program, not a parameter vector. We enumerate expressions in
increasing size order (an Occam prior: the shortest program consistent with the
evidence wins) and prune aggressively by *observational equivalence* — two
programs that produce identical values on the evidence are interchangeable, so
only one survives to be extended. This is what makes exhaustive search over a
combinatorial space tractable on a CPU.

The property that matters here: a synthesizer has no training distribution. A
rule family it has never encountered costs it nothing, as long as the family is
expressible in the language. That is the sharpest available contrast with a
network, which can only reproduce families it was fitted on.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Sequence

__all__ = ["Program", "SequenceSynthesizer"]


@dataclass(frozen=True)
class Program:
    """An expression tree over a tiny integer language, with its own printer."""

    op: str
    args: tuple = ()

    def size(self) -> int:
        return 1 + sum(a.size() for a in self.args if isinstance(a, Program))

    def __repr__(self) -> str:
        if self.op == "const":
            return str(self.args[0])
        if self.op in ("i", "prev1", "prev2"):
            return {"i": "i", "prev1": "x[-1]", "prev2": "x[-2]"}[self.op]
        if self.op == "ite_even":
            return f"(i even ? {self.args[0]} : {self.args[1]})"
        sym = {"add": "+", "sub": "-", "mul": "*"}[self.op]
        return f"({self.args[0]} {sym} {self.args[1]})"


def _eval(p: Program, i: int, hist: Sequence[int], mod: int) -> int:
    op = p.op
    if op == "const":
        return p.args[0] % mod
    if op == "i":
        return i % mod
    if op == "prev1":
        return hist[-1] % mod if len(hist) >= 1 else 0
    if op == "prev2":
        return hist[-2] % mod if len(hist) >= 2 else 0
    if op == "ite_even":
        return _eval(p.args[0] if i % 2 == 0 else p.args[1], i, hist, mod)
    a = _eval(p.args[0], i, hist, mod)
    b = _eval(p.args[1], i, hist, mod)
    if op == "add":
        return (a + b) % mod
    if op == "sub":
        return (a - b) % mod
    if op == "mul":
        return (a * b) % mod
    raise KeyError(op)


class SequenceSynthesizer:
    """Find the shortest program reproducing an integer sequence.

    ``modulus`` comes from the environment's *declared* symbol space (the size of
    the value vocabulary), not from knowledge of the task.

    Knobs: max_size, constants, ops, modulus, beam on the value cache. Six.
    """

    def __init__(self, *, max_size: int = 7, extra_constants: Sequence[int] = (),
                 ops: Sequence[str] = ("add", "sub", "mul", "ite_even"), modulus: int = 1_000_000,
                 max_programs: int = 400_000):
        self.max_size = max_size
        self.ops = tuple(ops)
        self.modulus = modulus
        self.extra_constants = tuple(extra_constants)
        self.max_programs = max_programs
        self.stats: dict[str, Any] = {}

    # ------------------------------------------------------------------
    def fit(self, seq: Sequence[int], *, min_index: int = 2) -> Program | None:
        """Return the shortest program p with p(i, x[<i]) == seq[i] for i >= min_index."""
        n = len(seq)
        if n <= min_index:
            return None
        idxs = list(range(min_index, n))
        consts = sorted({0, 1, 2, *(abs(v) % 10 for v in seq), *(v for v in seq[:3]), *self.extra_constants})

        def signature(p: Program) -> tuple:
            return tuple(_eval(p, i, seq[:i], self.modulus) for i in idxs)

        target = tuple(seq[i] % self.modulus for i in idxs)
        # size 1 terminals
        levels: dict[int, list[Program]] = {1: []}
        seen: dict[tuple, Program] = {}
        enumerated = 0
        for p in [Program("i"), Program("prev1"), Program("prev2")] + [Program("const", (c,)) for c in consts]:
            sig = signature(p)
            enumerated += 1
            if sig in seen:
                continue
            seen[sig] = p
            levels[1].append(p)
            if sig == target:
                self.stats = {"enumerated": enumerated, "size": p.size(), "distinct": len(seen)}
                return p

        for size in range(2, self.max_size + 1):
            levels[size] = []
            for a_size in range(1, size):
                b_size = size - 1 - a_size
                if b_size < 1:
                    continue
                for a in levels.get(a_size, ()):
                    for b in levels.get(b_size, ()):
                        for op in self.ops:
                            if op == "ite_even" and a_size + b_size + 1 != size:
                                continue
                            p = Program(op, (a, b))
                            enumerated += 1
                            if enumerated > self.max_programs:
                                self.stats = {"enumerated": enumerated, "aborted": True, "distinct": len(seen)}
                                return None
                            sig = signature(p)
                            if sig in seen:
                                continue
                            seen[sig] = p
                            levels[size].append(p)
                            if sig == target:
                                self.stats = {"enumerated": enumerated, "size": p.size(), "distinct": len(seen)}
                                return p
        self.stats = {"enumerated": enumerated, "found": False, "distinct": len(seen)}
        return None

    def predict_next(self, seq: Sequence[int], program: Program | None) -> int | None:
        if program is None:
            return None
        return _eval(program, len(seq), seq, self.modulus)
