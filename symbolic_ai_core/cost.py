"""What a unit of *useful capability* costs, and who in the system is paying.

Why this module exists
----------------------

``APPROACH.md`` used to lead with throughput: ~200k tokens/sec on one CPU core,
therefore 15-30 billion tokens per dollar, therefore "we are already 15-30x past
the cost target". Every number in that chain is true and the conclusion does not
follow. What it establishes is

    cost(the symbolic operations we currently run)  <<  $1 / Btok

and what it was read as saying is

    cost(a system with useful language capability)  <<  $1 / Btok

Those are different claims and this repo has only measured the first. The gap is
not rhetorical. The best exact parse recovery here is **0.016** — nothing in this
repo actually turns text into a graph. A system that reached useful capability by
putting a neural semantic parser in front of the symbolic core would have *that*
component's price as its price, and a symbolic core that is free does not make a
$0.30/Btok parser cheaper. Cheap-and-incapable is not a point on the cost curve;
it is a point off the capability axis entirely.

So the north star here is **$ per unit of useful capability**, and this module is
the thing that computes it. It replaces one number (tokens/sec) with a ledger:

======================================  ==================================
denominator                             what it refuses to let you claim
======================================  ==================================
``usd_per_btok_in``                     -- (this is the old number, kept)
``usd_per_solved_episode``              cheap per token, useless per answer
``usd_per_solved_episode_above_floor``  cheap per answer the *floor* bought
``usd_per_recovered_proposition``       cheap text-in, nothing understood
``ms_per_action``                       cheap in aggregate, unusable live
``bytes_per_retained_proposition``      cheap to run, ruinous to hold
======================================  ==================================

Two properties are deliberate and are the reason this is code rather than a
paragraph in a document.

**Cost is charged to the system, not to the component.** A :class:`System` is a
list of :class:`Component`, each priced either from a measured CPU rate or from
a vendor's published per-token price. The system's cost per token is the *sum*.
There is no way to express "our part is free" without also expressing what the
other parts cost, which is the exact misreading this module was written after.

**The floor divides the numerator.** ``usd_per_solved_episode_above_floor``
divides by ``accuracy - floor``, not by ``accuracy``. A system that scores at or
below its fitted floor has bought nothing, and the ledger reports its cost per
unit of capability as **infinite** rather than as a small number. That is the
same discipline the rest of the repo applies to lifts, moved into the place
where cost claims are made -- see
``notes/lessons/`` and the standing rule that a lift is quoted against a floor
or not quoted at all.

What this module does *not* do
------------------------------

It does not time anything. Timing on this box is a measurement of the
neighbours as often as of the model (``scripts/vsa_dim_curve.py`` documents the
3.4x spread that taught us so), so a rate must be supplied by something that
timed it deliberately on a quiet box. When no rate is supplied, :func:`ledger`
falls back to the run's total ``seconds`` -- which is *fit plus eval*, not an
inference rate -- and marks the row ``basis="fit+eval"``. Rows on that basis
carry :attr:`Ledger.quotable` = ``False`` and must not appear in
``RESEARCH_LOG.md``.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Iterable, Literal, Sequence

__all__ = [
    "Price", "Component", "System", "Capability", "Ledger",
    "cpu_component", "api_component", "capability_from_summary", "ledger",
    "ledger_table", "cheapest_above", "perverse_regime",
]

#: A commodity CPU core-hour. Spot/preemptible x86 sits near this at the time of
#: writing; it is an *input*, not a finding, and every consumer may override it.
#: Quoting a cost without quoting the price sheet it came from is the same error
#: as quoting an accuracy without its floor.
DEFAULT_USD_PER_CORE_HOUR = 0.02

#: Bytes per float in a fitted symbolic table when nothing more specific is
#: known. Used only by :attr:`Ledger.bytes_per_retained_proposition`, which is a
#: capacity figure and is meant to be compared across models, not billed.
BYTES_PER_PARAMETER = 4


@dataclass(frozen=True)
class Price:
    """The price sheet. Everything monetary in this module comes from here."""

    usd_per_core_hour: float = DEFAULT_USD_PER_CORE_HOUR
    #: Wall-clock seconds a live agent may spend on one action before the
    #: latency, not the money, is what makes the system unusable.
    latency_budget_ms: float = 100.0

    def usd_per_core_second(self) -> float:
        return self.usd_per_core_hour / 3600.0


@dataclass(frozen=True)
class Component:
    """One priced piece of a system.

    ``kind="cpu"`` prices from a *measured* throughput and the price sheet.
    ``kind="api"`` prices from a vendor's published per-million-token rate and
    ignores throughput entirely -- you are not paying for their cores.

    The point of having both is that a hybrid design must be expressible. The
    honest description of the most likely useful system this repo could build is
    "a small neural parser in front of a large symbolic memory", and that system
    is priced by adding a row of each kind, not by quoting the symbolic row.
    """

    name: str
    kind: Literal["cpu", "api"]
    #: ``cpu``: input tokens processed per second on one core, measured.
    tokens_per_sec: float | None = None
    #: ``cpu``: how many cores this component occupies while it runs.
    cores: float = 1.0
    #: ``api``: USD per million input tokens, from the vendor's price sheet.
    usd_per_mtok_in: float | None = None
    #: ``api``: USD per million output tokens, from the vendor's price sheet.
    usd_per_mtok_out: float | None = None
    #: Free text: where the number came from. A component whose provenance is
    #: empty is an assumption wearing a measurement's clothes.
    source: str = ""

    def __post_init__(self) -> None:
        if self.kind == "cpu" and not self.tokens_per_sec:
            raise ValueError(f"cpu component {self.name!r} needs tokens_per_sec")
        if self.kind == "api" and self.usd_per_mtok_in is None:
            raise ValueError(f"api component {self.name!r} needs usd_per_mtok_in")

    def usd_per_btok_in(self, price: Price) -> float:
        """USD to push one billion input tokens through this component."""
        match self.kind:
            case "cpu":
                assert self.tokens_per_sec
                core_seconds = (1e9 / self.tokens_per_sec) * self.cores
                return core_seconds * price.usd_per_core_second()
            case "api":
                assert self.usd_per_mtok_in is not None
                return self.usd_per_mtok_in * 1000.0
        raise AssertionError(self.kind)                       # pragma: no cover

    def seconds_per_ktok(self) -> float | None:
        """Wall seconds to process a thousand tokens, or ``None`` for an API.

        An API component's latency is a round trip and is not derivable from its
        price, so this returns ``None`` rather than guessing. A system holding
        one has no computed latency and says so.
        """
        if self.kind != "cpu":
            return None
        assert self.tokens_per_sec
        return 1000.0 / self.tokens_per_sec


def cpu_component(name: str, tokens_per_sec: float, *, cores: float = 1.0,
                  source: str = "") -> Component:
    return Component(name=name, kind="cpu", tokens_per_sec=tokens_per_sec,
                     cores=cores, source=source)


def api_component(name: str, usd_per_mtok_in: float, *,
                  usd_per_mtok_out: float | None = None,
                  source: str = "") -> Component:
    return Component(name=name, kind="api", usd_per_mtok_in=usd_per_mtok_in,
                     usd_per_mtok_out=usd_per_mtok_out, source=source)


@dataclass(frozen=True)
class System:
    """Everything that has to run for one answer to come out.

    The whole reason this type exists is that ``sum`` is not optional. A
    :class:`System` with one free symbolic component and one $0.30/Btok neural
    parser costs $0.30/Btok, and there is no accessor on this class that will
    tell you otherwise.
    """

    name: str
    components: tuple[Component, ...] = ()

    def with_component(self, component: Component) -> "System":
        return replace(self, components=self.components + (component,))

    def usd_per_btok_in(self, price: Price) -> float:
        return sum(c.usd_per_btok_in(price) for c in self.components)

    def seconds_per_ktok(self) -> float | None:
        parts = [c.seconds_per_ktok() for c in self.components]
        if any(p is None for p in parts):
            return None
        return sum(p for p in parts if p is not None)

    def dominant(self, price: Price) -> Component | None:
        """The component paying most of the bill.

        Printed beside every cost, because "which part is expensive" is the
        actionable half and a total hides it. If the answer is a neural parser,
        optimising the symbolic core is not the work.
        """
        if not self.components:
            return None
        return max(self.components, key=lambda c: c.usd_per_btok_in(price))


@dataclass(frozen=True)
class Capability:
    """What the system actually got right, and what the floor already had.

    Every rate here is paired with the floor for the same quantity. A rate
    without its floor cannot produce an above-floor cost, and this class refuses
    to carry one -- ``floor`` has no default.
    """

    #: Name of the thing being counted: "answer", "label", "proposition".
    unit: str
    #: Fraction of attempts the system got right, in ``[0, 1]``.
    rate: float
    #: The fitted floor for the same quantity, in ``[0, 1]``.
    floor: float
    #: How many attempts the rate was measured over. Small ``n`` is how this
    #: repo has been wrong most often; it is carried so a reader can see it.
    n: int = 0
    #: Input tokens consumed per attempt. This is the bridge between a
    #: per-token price and a per-answer price, and getting it wrong is the
    #: single easiest way to publish a flattering ledger.
    tokens_per_attempt: float = 0.0
    source: str = ""

    def above_floor(self) -> float:
        return self.rate - self.floor


@dataclass(frozen=True)
class Ledger:
    """The computed row. One system, one capability, one price sheet."""

    system: str
    unit: str
    price: Price
    basis: str
    quotable: bool
    usd_per_btok_in: float
    usd_per_attempt: float
    usd_per_solved: float
    usd_per_solved_above_floor: float
    ms_per_action: float | None
    bytes_per_retained_proposition: float | None
    rate: float
    floor: float
    n: int
    dominant_component: str
    notes: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        d = {k: v for k, v in self.__dict__.items() if k != "price"}
        d["usd_per_core_hour"] = self.price.usd_per_core_hour
        d["notes"] = list(self.notes)
        return d


def _safe_div(numerator: float, denominator: float) -> float:
    """Division that returns ``inf`` rather than raising or flattering.

    A denominator of zero here means "the system solved nothing" or "the system
    beat its floor by nothing". Both are real answers and both cost infinity per
    unit; neither is an error and neither may be silently dropped from a table.
    """
    if denominator <= 0:
        return math.inf
    return numerator / denominator


def ledger(system: System, capability: Capability, *,
           price: Price | None = None,
           retained_propositions: int = 0,
           parameters: int = 0,
           basis: str = "measured") -> Ledger:
    """Compute one row of the capability-cost ledger."""
    price = price or Price()
    notes: list[str] = []

    usd_btok = system.usd_per_btok_in(price)
    if capability.tokens_per_attempt <= 0:
        raise ValueError("capability.tokens_per_attempt must be > 0: a "
                         "per-answer cost with no tokens per answer is not a "
                         "cost, it is a ratio of two unrelated numbers")
    usd_attempt = usd_btok * capability.tokens_per_attempt / 1e9

    if basis != "measured":
        notes.append(
            f"basis={basis!r}: this rate is not an inference throughput; the "
            "row is diagnostic and must not be quoted")
    if capability.n and capability.n < 200:
        notes.append(f"n={capability.n} is small; see the standing rule that a "
                     "slice may form a hypothesis and never report one")
    if capability.above_floor() <= 0:
        notes.append(
            f"{capability.unit} rate {capability.rate:.4f} does not beat its "
            f"floor {capability.floor:.4f}: cost per unit of capability is "
            "infinite, which is the honest entry and not a formatting bug")

    sec_ktok = system.seconds_per_ktok()
    ms_action = None
    if sec_ktok is not None:
        ms_action = sec_ktok * capability.tokens_per_attempt / 1000.0 * 1000.0
        if ms_action > price.latency_budget_ms:
            notes.append(
                f"{ms_action:.1f}ms/action exceeds the "
                f"{price.latency_budget_ms:.0f}ms budget: cheap and too slow to "
                "act with is still unusable")
    else:
        notes.append("a component prices by token and not by core, so latency "
                     "is a round trip and is not derivable here")

    bytes_per_prop = None
    if retained_propositions > 0 and parameters > 0:
        bytes_per_prop = parameters * BYTES_PER_PARAMETER / retained_propositions

    dominant = system.dominant(price)
    return Ledger(
        system=system.name,
        unit=capability.unit,
        price=price,
        basis=basis,
        quotable=basis == "measured",
        usd_per_btok_in=usd_btok,
        usd_per_attempt=usd_attempt,
        usd_per_solved=_safe_div(usd_attempt, capability.rate),
        usd_per_solved_above_floor=_safe_div(usd_attempt,
                                             capability.above_floor()),
        ms_per_action=ms_action,
        bytes_per_retained_proposition=bytes_per_prop,
        rate=capability.rate,
        floor=capability.floor,
        n=capability.n,
        dominant_component=dominant.name if dominant else "",
        notes=tuple(notes),
    )


# ---------------------------------------------------------------------------
# reading a finished run
# ---------------------------------------------------------------------------

#: ``(task, accuracy key, floor key, count key, unit)`` for the capabilities a
#: ``summary.json`` can support. ``answer`` leads because it is the one that
#: says whether anything was understood: only ~1.4% of scored language-modelling
#: positions are the answer, so a ledger keyed on ``token_acc`` would be pricing
#: the boilerplate.
CAPABILITY_KEYS: tuple[tuple[str, str, str, str, str], ...] = (
    ("lm", "answer_acc", "answer_floor", "answer_n", "answer"),
    ("node", "label_acc", "label_floor", "label_n", "proposition"),
    ("node", "type_acc", "type_floor", "type_n", "type"),
)


def capability_from_summary(summary: dict[str, Any], unit: str = "answer",
                            *, tokens_per_attempt: float | None = None,
                            ) -> Capability | None:
    """Pull one :class:`Capability` out of a run's ``summary.json``.

    Returns ``None`` when the run did not score that unit, which is a different
    statement from scoring zero and is kept distinguishable on purpose.
    """
    final = summary.get("final", {})
    for task, acc_key, floor_key, n_key, name in CAPABILITY_KEYS:
        if name != unit:
            continue
        block = final.get(task)
        if not block or acc_key not in block or floor_key not in block:
            continue
        cfg = summary.get("config", {})
        per_attempt = tokens_per_attempt
        if per_attempt is None:
            # One "attempt" is one episode read end to end. `max_len` is the
            # harness's cap on episode length and is the only episode-scale
            # token count a summary carries; it over-states short episodes,
            # which makes the resulting cost conservative rather than
            # flattering, and that is the direction to err in.
            per_attempt = float(cfg.get("max_len") or 0) or 320.0
        return Capability(
            unit=name,
            rate=float(block[acc_key]),
            floor=float(block[floor_key]),
            n=int(block.get(n_key, 0) or 0),
            tokens_per_attempt=per_attempt,
            source=f"{task}.{acc_key}",
        )
    return None


def system_from_summary(summary: dict[str, Any], run_dir: Path | None = None,
                        *, tokens_per_sec: float | None = None,
                        ) -> tuple[System, str]:
    """Build a one-component system for a finished run, and say what timed it.

    Resolution order, most trustworthy first:

    1. an explicit ``tokens_per_sec`` from the caller;
    2. ``timing.json`` beside the run, as written by
       ``scripts/vsa_dim_curve.py`` / ``scripts/metta_cost.py``;
    3. the run's total ``seconds``, which is **fit plus eval** and is not an
       inference rate. Rows on that basis come back ``basis="fit+eval"``.
    """
    name = str(summary.get("model", "unknown"))
    if tokens_per_sec:
        return System(name, (cpu_component(name, tokens_per_sec,
                                           source="caller"),)), "measured"
    if run_dir is not None:
        timing = run_dir / "timing.json"
        if timing.exists():
            rec = json.loads(timing.read_text())
            rate = rec.get("tokens_per_sec")
            if rate:
                return System(name, (cpu_component(name, float(rate),
                                                   source=str(timing)),)
                              ), "measured"
    seconds = float(summary.get("seconds") or 0.0)
    n_eval = int(summary.get("n_eval") or 0)
    max_len = float(summary.get("config", {}).get("max_len") or 320)
    tokens = n_eval * max_len
    rate = tokens / seconds if seconds > 0 and tokens > 0 else 1.0
    return System(name, (cpu_component(name, rate, source="summary.seconds"),)
                  ), "fit+eval"


def ledger_from_run(run_dir: Path, unit: str = "answer", *,
                    price: Price | None = None,
                    tokens_per_sec: float | None = None,
                    extra: Sequence[Component] = ()) -> Ledger | None:
    """Ledger row for one finished run, plus any components it depends on.

    ``extra`` is how the honest hybrid gets priced. A symbolic reasoner that
    only works because something upstream turned text into a graph is not a
    system on its own, and passing the parser in here is what stops its price
    from disappearing.
    """
    summary_path = run_dir / "summary.json"
    if not summary_path.exists():
        return None
    summary = json.loads(summary_path.read_text())
    capability = capability_from_summary(summary, unit)
    if capability is None:
        return None
    system, basis = system_from_summary(summary, run_dir,
                                        tokens_per_sec=tokens_per_sec)
    for component in extra:
        system = system.with_component(component)
    return ledger(system, capability, price=price,
                  parameters=int(summary.get("parameters") or 0),
                  retained_propositions=int(summary.get("n_train") or 0),
                  basis=basis)


# ---------------------------------------------------------------------------
# printing
# ---------------------------------------------------------------------------
def _usd(value: float) -> str:
    if value == math.inf:
        return "inf"
    if value == 0:
        return "0"
    if value >= 0.01:
        return f"${value:,.2f}"
    return f"${value:.2e}"


def cheapest_above(rows: Iterable[Ledger], min_rate: float) -> Ledger | None:
    """The cheapest row that still achieves ``rate >= min_rate``.

    This is the question anyone deploying actually has — *minimise cost subject
    to capability* — and it is the one ``usd_per_solved_above_floor`` alone does
    not answer. See :func:`perverse_regime` for why the unconstrained ratio can
    prefer a worse system.
    """
    ok = [r for r in rows if r.rate >= min_rate]
    return min(ok, key=lambda r: r.usd_per_attempt) if ok else None


def perverse_regime(rows: Iterable[Ledger]) -> tuple[Ledger, Ledger] | None:
    """``(ratio winner, more capable row)`` when the ratio prefers the worse one.

    A lossy arm beats a better one on ``$/solved-above-floor`` exactly when

        relative cost saving  >  relative lift loss
        dcost / cost          >  dacc / (acc - floor)

    and when ``acc >> floor`` that right-hand denominator is large, so accuracy
    is *cheap in lift terms*. The metric is therefore well behaved where a
    system is weak and perverse where it is strong -- the opposite of the regime
    a maturing system lives in. Measured at 2.8% on the flood task, where a
    0.887-accuracy arm outranked a 1.000-accuracy one:
    ``notes/findings/2026-08-18-dollars-per-solved-above-floor-rewards-losing-accuracy.md``.

    Returns ``None`` when the ratio winner is also the most capable row, which
    is the case the metric was designed for and the case it handles correctly.
    """
    rows = [r for r in rows if math.isfinite(r.usd_per_solved_above_floor)]
    if len(rows) < 2:
        return None
    winner = min(rows, key=lambda r: r.usd_per_solved_above_floor)
    better = max(rows, key=lambda r: r.rate)
    return (winner, better) if better.rate > winner.rate else None


def ledger_table(rows: Iterable[Ledger], *, min_rate: float | None = None) -> str:
    """Render ledger rows, sorted by the column that cannot be gamed -- and say
    so when that column is nevertheless preferring a worse system.

    The sort key is ``usd_per_solved_above_floor``. Sorting by
    ``usd_per_btok_in`` would put a system that understands nothing at the top,
    which is precisely the reading this whole module exists to prevent.

    But the ratio has a **perverse regime** far above the floor, so the table
    checks for it and prints a warning naming both rows when it fires. A reader
    who sorts and takes the top row would otherwise ship a 0.887 system over a
    1.000 one with nothing on the page to explain why.

    ``min_rate`` turns the table into the question worth asking -- *the cheapest
    arm achieving accuracy >= a* -- by marking rows that miss the bar and
    reporting the constrained winner.
    """
    rows = sorted(rows, key=lambda r: r.usd_per_solved_above_floor)
    if not rows:
        return "no runs scored the requested unit"
    header = (f"{'system':<22} {'unit':<12} {'$/Btok in':>12} "
              f"{'$/solved':>12} {'$/solved>floor':>15} {'ms/act':>8} "
              f"{'rate':>7} {'floor':>7} {'n':>7}  basis")
    lines = [header, "-" * len(header)]
    for r in rows:
        ms = f"{r.ms_per_action:.1f}" if r.ms_per_action is not None else "-"
        lines.append(
            f"{r.system:<22} {r.unit:<12} {_usd(r.usd_per_btok_in):>12} "
            f"{_usd(r.usd_per_solved):>12} "
            f"{_usd(r.usd_per_solved_above_floor):>15} {ms:>8} "
            f"{r.rate:>7.3f} {r.floor:>7.3f} {r.n:>7d}  "
            f"{r.basis}{'' if r.quotable else ' (NOT QUOTABLE)'}")
    seen: set[str] = set()
    for r in rows:
        for note in r.notes:
            if note not in seen:
                seen.add(note)
                lines.append(f"  ! {r.system}: {note}")
    lines.append("")
    lines.append("Sorted by $/solved-above-floor. A system at or below its "
                 "floor reads 'inf' and that is the correct entry.")

    pair = perverse_regime(rows)
    if pair is not None:
        winner, better = pair
        lines.append("")
        lines.append(
            f"  !! PERVERSE REGIME: the ratio ranks {winner.system} "
            f"(rate {winner.rate:.3f}) above {better.system} "
            f"(rate {better.rate:.3f}). Far above the floor a cost saving buys "
            f"more than the lift it costs, so the ratio prefers the LESS "
            f"capable system. Do not read the top row as the answer -- ask for "
            f"the cheapest arm above an accuracy bar instead.")
    if min_rate is not None:
        pick = cheapest_above(rows, min_rate)
        lines.append("")
        if pick is None:
            lines.append(f"  no system reaches rate >= {min_rate:.3f}; the "
                         f"best is {max(r.rate for r in rows):.3f}")
        else:
            lines.append(f"  cheapest at rate >= {min_rate:.3f}: {pick.system} "
                         f"({_usd(pick.usd_per_attempt)}/attempt, rate "
                         f"{pick.rate:.3f})")
        missed = [r.system for r in rows if r.rate < min_rate]
        if missed:
            lines.append(f"  below the bar: {', '.join(missed)}")
    return "\n".join(lines)
