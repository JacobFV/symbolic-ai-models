"""The kernel contract: manifest, projection, result — and what may be claimed.

Every kernel declares a manifest that is independent of its implementation
language, so that a graph naming ``datalog@1`` can be executed here and edited in
a canvas that has never heard of Python.

Four things in the manifest do real work and are not documentation:

``requires`` / ``provides``
    world **profiles**, not a schema. A kernel asks for the capabilities it
    needs — ``scene.body``, ``logic.rule`` — and is indifferent to the rest, so
    a huge domain engine can sit behind a narrow contract without the boundary
    ontology growing to meet it.
``semantics``
    which logics this kernel reasons under — a *set*, because they are not
    alternatives: stratified datalog is closed-world **and** non-monotonic at
    once. The same textual rule means different things under different ones, and
    ``not p`` is at least four different world states: a proof of not-p, an
    inability to prove p, p's probability below a threshold, and p's absence
    from a database. A projection into a kernel with incompatible semantics is a
    refusal, not a best effort.
``authority``
    per property: ``veto``, ``propose`` or ``observe``. Proof validity from an
    exact kernel is a veto; a pose from an estimator is a proposal. Fusion reads
    this rather than taking the last writer.
``runtime`` / ``dependencies``
    ``native`` or ``external``. An external kernel whose toolchain is absent
    **refuses loudly**. It does not degrade to a weaker kernel, because a silent
    fallback is how a broken component reads as a working one.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field, replace
from typing import Any, Callable, Iterable, Mapping, Protocol, runtime_checkable

from symbolic_ai_core.world import Claim, WorldDelta, WorldSnapshot
from symbolic_ai_core.world.profile import check_profiles

__all__ = ["SEMANTICS", "AUTHORITY", "Discard", "Projection", "KernelCost",
           "KERNEL_MODULES", "kernel_ids", "price_cpu_ns",
           "KernelRequest", "KernelResult", "KernelManifest", "Kernel",
           "KernelUnavailable", "KERNELS", "register_kernel", "get_kernel",
           "check_entitlement", "timed"]

#: Which logic a kernel reasons under. Metadata, because it changes what a rule
#: *means* and two kernels disagreeing about it silently is the whole problem.
SEMANTICS = ("classical", "intuitionistic", "closed_world", "open_world",
             "monotonic", "non_monotonic", "defeasible", "probabilistic",
             "temporal", "modal", "causal", "constraint")

#: What a kernel's claim about a property is worth when several kernels speak.
AUTHORITY = ("veto", "propose", "observe")


class KernelUnavailable(RuntimeError):
    """The toolchain this kernel needs is not on this machine.

    Raised rather than returning an empty result, because an empty result from a
    missing solver is indistinguishable from a solver that found nothing.
    """


@dataclass(frozen=True)
class Discard:
    """One thing the projection could not carry, and why.

    ``why`` is the field that matters. "unsupported" tells a reader nothing; "a
    Quantity role has no datalog representation" tells them whether the answer
    they are holding is about the question they asked.
    """

    kind: str        #: claim | facet | entity | role | rule
    ref: str         #: an id, or an index into the world's claims
    why: str

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "ref": self.ref, "why": self.why}


@dataclass(frozen=True)
class Projection:
    """``P_K(world)``: the kernel-language program, plus what was left behind."""

    kernel: str
    program: Any
    semantics: tuple[str, ...]
    covered_entities: frozenset[str] = frozenset()
    covered_claims: tuple[int, ...] = ()
    discarded: tuple[Discard, ...] = ()
    meta: Mapping[str, Any] = field(default_factory=dict)

    @property
    def lossless(self) -> bool:
        return not self.discarded

    def covers(self, entity_id: str) -> bool:
        return entity_id in self.covered_entities

    def summary(self) -> str:
        return (f"{self.kernel}: {len(self.covered_claims)} claims, "
                f"{len(self.covered_entities)} entities, "
                f"{len(self.discarded)} discarded")

    def to_dict(self) -> dict[str, Any]:
        return {"kernel": self.kernel, "semantics": list(self.semantics),
                "covered_entities": sorted(self.covered_entities),
                "covered_claims": list(self.covered_claims),
                "discarded": [d.to_dict() for d in self.discarded],
                "meta": dict(self.meta)}


@dataclass(frozen=True)
class KernelCost:
    """What one kernel invocation cost. Feeds :mod:`symbolic_ai_core.cost`.

    ``usd`` is ``None`` when nothing priced it, which is **not** zero. That
    distinction is the one this repo spent months without — a throughput number
    read as a capability price — and it is why the flow trace counts unpriced
    nodes separately.

    ``cpu_ns`` and ``wall_ns`` are both recorded and are **not** the same
    number. Money is charged for cores held, so the price comes from ``cpu_ns``;
    usability is decided by ``wall_ns``, and a kernel that blocks on a
    subprocess is cheap and unusable at once. Reporting one and calling it the
    other is how a latency problem becomes invisible in a cost table.
    """

    cpu_ns: int = 0
    wall_ns: int = 0
    bytes_read: int = 0
    bytes_written: int = 0
    usd: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"cpu_ns": self.cpu_ns, "wall_ns": self.wall_ns,
                "bytes_read": self.bytes_read,
                "bytes_written": self.bytes_written, "usd": self.usd}


@dataclass(frozen=True)
class KernelRequest:
    """What is being asked. ``goal`` is kernel-specific; ``budget`` is not."""

    goal: Any = None
    params: Mapping[str, Any] = field(default_factory=dict)
    budget_usd: float | None = None
    budget_ns: int | None = None


@dataclass(frozen=True)
class KernelResult:
    """``R_K``: claims and a delta, never a mutation.

    ``refused`` is a first-class outcome and carries its reason. A kernel that
    cannot answer says so; it does not return an empty delta that reads as "no
    consequences".
    """

    kernel: str
    claims: tuple[Claim, ...] = ()
    delta: WorldDelta = field(default_factory=WorldDelta)
    artifacts: Mapping[str, Any] = field(default_factory=dict)
    trace: Any = None
    diagnostics: Mapping[str, Any] = field(default_factory=dict)
    cost: KernelCost = field(default_factory=KernelCost)
    refused: str = ""

    @property
    def ok(self) -> bool:
        return not self.refused

    def to_dict(self) -> dict[str, Any]:
        return {"kernel": self.kernel,
                "claims": [c.to_dict() for c in self.claims],
                "delta": self.delta.to_dict(),
                "diagnostics": dict(self.diagnostics),
                "cost": self.cost.to_dict(), "refused": self.refused}


@dataclass(frozen=True)
class KernelManifest:
    """A kernel's contract, independent of its implementation language."""

    id: str
    requires: tuple[str, ...] = ()
    provides: tuple[str, ...] = ()
    semantics: tuple[str, ...] = ("classical",)
    pure: bool = True
    deterministic: bool = True
    incremental: bool = False
    differentiable: bool = False
    clocks: str = "none"
    runtime: str = "native"                    #: native | external
    dependencies: tuple[str, ...] = ()
    authority: Mapping[str, str] = field(default_factory=dict)
    tolerances: Mapping[str, float] = field(default_factory=dict)
    cost_estimator: Callable[..., KernelCost] | None = None
    doc: str = ""

    def __post_init__(self) -> None:
        if "@" not in self.id:
            raise ValueError(f"kernel id {self.id!r} carries no version; "
                             f"use `{self.id}@1`. A graph on disk outlives the "
                             f"kernel that ran it.")
        unknown = [s for s in self.semantics if s not in SEMANTICS]
        if unknown or not self.semantics:
            raise ValueError(f"unknown or empty semantics {unknown or '()'}; "
                             f"have {SEMANTICS}. A kernel that does not say "
                             f"which logic it reasons under cannot be checked "
                             f"against one that does.")
        check_profiles(self.requires, where=f"{self.id}.requires")
        check_profiles(self.provides, where=f"{self.id}.provides")
        bad = {k: v for k, v in self.authority.items() if v not in AUTHORITY}
        if bad:
            raise ValueError(f"{self.id}: authority {bad} not in {AUTHORITY}")

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "requires": list(self.requires),
                "provides": list(self.provides),
                "semantics": list(self.semantics),
                "pure": self.pure, "deterministic": self.deterministic,
                "incremental": self.incremental,
                "differentiable": self.differentiable, "clocks": self.clocks,
                "runtime": self.runtime, "dependencies": list(self.dependencies),
                "authority": dict(self.authority),
                "tolerances": dict(self.tolerances), "doc": self.doc}


@runtime_checkable
class Kernel(Protocol):
    """Project, then run. Neither step may touch the world it was handed."""

    manifest: KernelManifest

    def available(self) -> tuple[bool, str]: ...

    def project(self, world: WorldSnapshot,
                request: KernelRequest) -> Projection: ...

    def run(self, projection: Projection,
            request: KernelRequest) -> KernelResult: ...


KERNELS: dict[str, Kernel] = {}

#: Kernel id -> the module that registers it. Looked up lazily, so that asking
#: for ``datalog@1`` does not import a Lean or SMT binding that may not be
#: installed. A kernel whose module imports cleanly but whose *toolchain* is
#: missing still registers, and answers ``available() -> (False, why)`` — the
#: two failures are different and a caller needs to tell them apart.
KERNEL_MODULES: dict[str, str] = {
    "datalog@1": "symbolic_ai_kernels.datalog",
    "asp@1": "symbolic_ai_kernels.asp",
    "smt@1": "symbolic_ai_kernels.smt",
    "lean@1": "symbolic_ai_kernels.lean",
    "egraph@1": "symbolic_ai_kernels.egraph",
    "rigid@1": "symbolic_ai_kernels.rigid",
}


def kernel_ids() -> list[str]:
    """Every kernel this repo knows about, loaded or not."""
    return sorted(set(KERNELS) | set(KERNEL_MODULES))


def register_kernel(kernel: Kernel) -> Kernel:
    kid = kernel.manifest.id
    if kid in KERNELS:
        raise ValueError(f"kernel {kid} is already registered; kernels are "
                         f"versioned rather than redefined")
    KERNELS[kid] = kernel
    return kernel


def get_kernel(kernel_id: str) -> Kernel:
    if kernel_id not in KERNELS and kernel_id in KERNEL_MODULES:
        import importlib
        importlib.import_module(KERNEL_MODULES[kernel_id])
    try:
        return KERNELS[kernel_id]
    except KeyError:
        raise KeyError(f"unknown kernel {kernel_id!r}; known: "
                       f"{kernel_ids()}") from None


def check_entitlement(projection: Projection, claims: Iterable[Claim]) -> None:
    """A kernel may not claim about what its projection discarded.

    This is the rule that makes a lossy projection safe to use. If the ASP
    projection dropped an entity's continuous geometry, an ASP claim *about that
    entity* is a claim made without its support — and the reader has no way to
    know, because the answer looks like every other answer.

    Entities the projection never saw at all are the clear case and are refused.
    Entities it saw but partially discarded are allowed through with the discard
    record attached, because a kernel is entitled to reason about the part it
    covered — the record is what lets a consumer decide.
    """
    unseen = []
    for c in claims:
        for eid in c.entities():
            if not projection.covers(eid):
                unseen.append((c.predicate, eid))
    if unseen:
        raise ValueError(
            f"{projection.kernel} claimed about entities its projection never "
            f"covered: {sorted(set(unseen))[:8]}. A claim whose support was "
            f"discarded is not a claim this kernel is entitled to make.")


def price_cpu_ns(cpu_ns: int, *, usd_per_core_hour: float | None = None
                 ) -> float:
    """CPU nanoseconds -> USD, at the repo's stated price sheet.

    The rate comes from :mod:`symbolic_ai_core.cost`, which is the only place a
    monetary input lives, because quoting a cost without quoting the price sheet
    it came from is the same error as quoting an accuracy without its floor.
    """
    from symbolic_ai_core.cost import DEFAULT_USD_PER_CORE_HOUR
    rate = (DEFAULT_USD_PER_CORE_HOUR if usd_per_core_hour is None
            else usd_per_core_hour)
    return cpu_ns * rate / 3600.0 / 1e9


def timed(fn: Callable[[], Any]) -> tuple[Any, tuple[int, int]]:
    """Run ``fn``, returning ``(result, (cpu_ns, wall_ns))``.

    Two clocks, because they answer different questions and this repo has
    already been burned by a throughput number standing in for a price.
    ``process_time_ns`` counts CPU actually burned by this process;
    ``perf_counter_ns`` counts elapsed time, including anything spent waiting on
    a solver in another process.
    """
    c0, w0 = time.process_time_ns(), time.perf_counter_ns()
    out = fn()
    return out, (time.process_time_ns() - c0, time.perf_counter_ns() - w0)
