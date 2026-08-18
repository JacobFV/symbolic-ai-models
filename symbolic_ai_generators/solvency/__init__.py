"""A covenant test over revised financial data, and the look-ahead it invites.

The second generated task, and structurally the opposite of the flood one: no
routing, no discrete search, no subset answer. One boolean per firm per decision
date — *did this group clear its revenue covenant?* — and the whole difficulty is
that the figures the question is about were **revised after the decision**.

That is the two-times machinery the world IR has carried since it was written and
nothing had exercised: ``valid_time`` is the quarter a figure is about, and
``transaction_time`` is when it could have been known. A backtest that reads the
current vintage of a historical figure is answering a question nobody could have
asked at the time, and the failure is silent — the number is plausible, the code
is short, and the answer is the flattering one.
"""

from __future__ import annotations

from .world import CORRUPTIONS, SolvencyCase, corrupt, decide, generate

__all__ = ["SolvencyCase", "generate", "decide", "corrupt", "CORRUPTIONS"]
