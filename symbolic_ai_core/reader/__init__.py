"""The reading boundary: text in, claims and what was *not* settled out.

`kernel.run@1` made kernel selection configuration rather than control flow. This
is the same seam on the other side of the world. A reader is anything that turns
observations into **candidate claims plus the record of what it could not
settle**, and `reader.run@1` puts it in a flow graph beside the kernels.

Why an ABI rather than another reader
-------------------------------------

``symbolic_ai_generators/flood/read_surface.py`` is an experimental encyclopedia:
lexical patterns, type signatures, an external value registry, role anchors,
positional adjacency, ambiguity enumeration, evidence conflicts. That was the
right research instrument and it **cannot be the deployed architecture** -- it
builds a finished `WorldSnapshot` directly, so everything it could not decide is
either guessed or silently dropped before anything downstream can see it.

The contract here forces the opposite. A reader returns a
:class:`ReadResult`, and the things this repo spent a session learning are
**ports on it rather than private behaviour**:

- ``delta`` -- what it is prepared to assert, as a `WorldDelta`;
- ``candidates`` -- claim alternatives it is *not* prepared to collapse, which is
  directive 19 made structural. Measured: on flood's honest surface, collapsing
  costs 0.679 accuracy with silent errors where carrying gives soundness 1.000;
- ``unresolved`` -- distinctions left open, so a caller that ignores them has
  visibly ignored something rather than never been told;
- ``alignments`` -- span to claim, which the generated surfaces supply exactly and
  which is the supervision a learned reader trains on;
- ``confidence`` and ``provenance`` -- per claim, because "a check that reads part
  of the world inherits that part's errors" appeared six times in one session and
  the fix each time was knowing which part;
- ``cost`` -- because reading is 96.1% of solvency's wall clock and the ledger
  priced 4% of it for months.

A learned reader implements the same protocol. Nothing downstream changes.
"""

from .abi import (READER_RUN, Alignment, Candidate, Reader, ReadResult,
                  get_reader, list_readers, register_reader)

__all__ = ["ReadResult", "Reader", "Candidate", "Alignment", "register_reader",
           "get_reader", "list_readers", "READER_RUN"]
