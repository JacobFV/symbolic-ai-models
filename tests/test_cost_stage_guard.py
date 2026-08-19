"""The guard for the omission that priced 4% of solvency.

`cost.py` cannot detect a missing *component* -- ``sum`` is not optional only
over what it is given. It can detect that nothing in the system claims to do the
**reading**, which is the specific omission every milestone in this repo made:
text has to become a world before a kernel can run on it, and pricing only the
kernel is an incomplete ledger rather than a cheaper system.
"""

from __future__ import annotations

from symbolic_ai_core.cost import Capability, System, cpu_component, ledger

CAP = Capability(unit="answer", rate=0.9, floor=0.5, n=100,
                 tokens_per_attempt=300)


def _fires(*components) -> bool:
    row = ledger(System(name="t", components=components), CAP)
    return any("READING" in n for n in row.notes)


def test_it_fires_on_a_declared_kernel_only_system() -> None:
    assert _fires(cpu_component("k", 1e4, source="m", stage="solve"))


def test_it_is_silent_when_the_reader_is_priced() -> None:
    assert not _fires(cpu_component("r", 1e6, source="m", stage="read"),
                      cpu_component("k", 1e4, source="m", stage="solve"))


def test_it_is_silent_when_nothing_is_declared() -> None:
    """Deliberate, and a real limitation rather than an oversight.

    Declaring stages is what opts a caller into the check; without that, every
    existing caller would get a note it cannot act on. The cost is that an
    author who declares nothing gets no guard at all.
    """
    assert not _fires(cpu_component("k", 1e4, source="m"))


def test_the_note_says_what_it_costs_to_omit() -> None:
    """A guard that only says "missing" invites being ignored. This one carries
    the measurement that shows when the omission matters."""
    row = ledger(System(name="t", components=(
        cpu_component("k", 1e4, source="m", stage="solve"),)), CAP)
    note = next(n for n in row.notes if "READING" in n)
    assert "96.1%" in note and "1.9%" in note


def test_pricing_is_unchanged_by_declaring_a_stage() -> None:
    """The field is metadata. It must not move a number."""
    plain = ledger(System(name="t", components=(
        cpu_component("k", 1e4, source="m"),)), CAP)
    tagged = ledger(System(name="t", components=(
        cpu_component("k", 1e4, source="m", stage="solve"),)), CAP)
    assert plain.usd_per_solved_above_floor == \
        tagged.usd_per_solved_above_floor
