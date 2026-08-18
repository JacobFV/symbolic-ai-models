"""What a kernel will cost, before you run it — fitted, and reported with its error.

`KernelManifest` has carried a ``cost_estimator`` field since the ABI was
written. Grepping the repo finds it in exactly one place: its own declaration.
No kernel supplies one, nothing reads one, no test touches one. It is the same
defect as ``add_facts``' delta contract one stage earlier — that claim was
documented and wrong, this one is documented and absent — and both survived
because **a claim nothing exercises is a claim nothing checks.**

It matters because a router has to choose *before* it runs. The routing finding
used a hand-written provable gate, which works exactly once per task and has to
be re-derived by hand for the next one. A fitted estimator is the general form,
and the only honest way to ship one is with its calibration attached.

**The metric a router needs is not relative error.** A router picks between
options, so what matters is whether the estimate *orders* them correctly. An
estimator that is uniformly 3x low is useless by relative error and perfect for
routing; one that is unbiased but noisy is the reverse. Both are reported, and
:attr:`Calibration.ordering` is the one to read when deciding whether to route.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from typing import Callable, Iterable, Mapping, Sequence

__all__ = ["Observation", "Calibration", "PowerLawCost", "fit_power_law"]


@dataclass(frozen=True)
class Observation:
    """One measured run: what it was given, and what it cost."""

    size: float
    cost: float

    def __post_init__(self) -> None:
        if self.size <= 0 or self.cost <= 0:
            raise ValueError(
                f"size and cost must both be positive, got {self.size} and "
                f"{self.cost}: a power law is fitted in log space and a "
                "zero would be a silent -inf")


@dataclass(frozen=True)
class Calibration:
    """How wrong the estimate is, in the two ways that matter separately."""

    n: int
    median_rel_error: float
    p90_rel_error: float
    ordering: float
    bias: float

    #: Below this, a size estimate cannot be used to choose between plans.
    #: 0.90 is a judgement, not a measurement: datalog scores 1.000 and SMT
    #: across the 3-SAT phase transition scores 0.667, and nothing measured so
    #: far lands between 0.70 and 1.00, so the threshold is not yet load
    #: bearing and should be revisited when something does.
    ORDERABLE = 0.90

    @property
    def orderable(self) -> bool:
        """Whether a router may use this estimate to pick between plans.

        The property that decides it, and it is not accuracy. A cost model
        fitted on small datalog runs is 7x low at full scale and orders every
        pair correctly; an SMT estimate can be unbiased and still order two
        thirds of pairs, because a 2,250-clause instance away from the phase
        transition solves 7,892x faster than a 1,491-clause instance on it.
        """
        return self.ordering >= self.ORDERABLE

    def summary(self) -> str:
        return (f"n={self.n}: median {self.median_rel_error:.1%}, "
                f"p90 {self.p90_rel_error:.1%}, ordering {self.ordering:.3f}"
                f"{'' if self.orderable else ' (NOT orderable)'}, "
                f"bias {self.bias:+.2f}x")


@dataclass(frozen=True)
class PowerLawCost:
    """``cost = a * size**b``, fitted in log space.

    A power law rather than a line because every kernel cost this repo has
    measured is superlinear in its input — the datalog engine ran at n^2.0
    before its index was fixed and n^1.5 after — and a linear model fitted to
    that under-predicts the large cases, which are exactly the ones a router
    must not send down the expensive branch.
    """

    a: float
    b: float
    n: int = 0

    def __call__(self, size: float) -> float:
        if size <= 0:
            raise ValueError("size must be positive")
        return self.a * size ** self.b

    def calibrate(self, held_out: Sequence[Observation]) -> Calibration:
        """Error on runs the fit never saw.

        Fitting and scoring on the same points measures the fit's flexibility,
        not its usefulness, and this repo has a standing rule against forming a
        number on the data it will be quoted against.
        """
        if not held_out:
            raise ValueError("calibration needs held-out observations")
        ratios = [self(o.size) / o.cost for o in held_out]
        rel = sorted(abs(r - 1.0) for r in ratios)
        pairs = ok = 0
        for i, a in enumerate(held_out):
            for b in held_out[i + 1:]:
                if a.cost == b.cost:
                    continue
                pairs += 1
                if (self(a.size) < self(b.size)) == (a.cost < b.cost):
                    ok += 1
        return Calibration(
            n=len(held_out),
            median_rel_error=rel[len(rel) // 2],
            p90_rel_error=rel[min(len(rel) - 1, int(0.9 * len(rel)))],
            ordering=ok / pairs if pairs else 1.0,
            bias=math.exp(statistics.mean(math.log(r) for r in ratios)))


def fit_power_law(observations: Iterable[Observation]) -> PowerLawCost:
    """Least squares on ``log cost`` against ``log size``.

    Two points are the minimum and are fitted exactly; the caller finds out how
    little that is worth from :meth:`PowerLawCost.calibrate`, which is why this
    does not refuse small samples but the calibration always reports ``n``.
    """
    obs = list(observations)
    if len(obs) < 2:
        raise ValueError(
            f"a power law needs at least 2 observations, got {len(obs)}")
    xs = [math.log(o.size) for o in obs]
    ys = [math.log(o.cost) for o in obs]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    denom = sum((x - mx) ** 2 for x in xs)
    if denom == 0:
        raise ValueError(
            "every observation has the same size: an exponent cannot be "
            "fitted from one point on the x axis")
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / denom
    return PowerLawCost(a=math.exp(my - b * mx), b=b, n=len(obs))
