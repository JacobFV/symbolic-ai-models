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

- ``claims`` + ``belief`` + ``factors`` -- a candidate pool, a belief over it and
  the constraints among them, so the reader can say *A: 0.62, B: 0.38, A XOR B*
  without materialising two worlds. Enumeration is one reading of a factor set
  and is exponential in the open choices; the factor is what is actually known.
  Collapsing to a delta is a decision `ReadResult.delta` takes explicitly;
- ``mentions`` -- spans with candidate entities, identity left open, because
  relation semantics disambiguate identity and a reader that resolves at the
  mention stage discards the evidence that would have settled it;
- ``unresolved`` -- distinctions left open, so a caller that ignores them has
  visibly ignored something rather than never been told;
- ``alignments`` -- span to claim, which the generated surfaces supply exactly and
  which is the supervision a learned reader trains on;
- ``confidence`` and ``provenance`` -- per claim, because "a check that reads part
  of the world inherits that part's errors" appeared six times in one session and
  the fix each time was knowing which part;
- ``cost`` -- because reading is 96.1% of solvency's wall clock and the ledger
  priced 4% of it for months.

A learned reader implements the same protocol. Nothing downstream changes --
:class:`~symbolic_ai_core.reader.learned.LearnedSpanReader` is the demonstration,
and it reads all three generated domains with no domain lexicon in its source.
"""

from .abi import (READER_RUN, Alignment, Factor, Mention, Reader, ReadResult,
                  get_reader, list_readers, register_reader)
from .learned import LearnedSpanReader, Unit, supervise

__all__ = ["ReadResult", "Reader", "Factor", "Mention", "Alignment",
           "register_reader", "get_reader", "list_readers", "READER_RUN",
           "LearnedSpanReader", "Unit", "supervise"]
