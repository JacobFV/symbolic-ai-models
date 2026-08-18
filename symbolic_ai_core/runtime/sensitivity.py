"""How far an answer moves when an input moves, measured rather than declared.

A kernel manifest carries a **tolerance**: `geo@1` is accurate to about 0.5%.
That number is true and it is not the number a caller needs, because callers
compose. Measured on the openflights route network, substituting the spherical
approximation for the geodesic misclassifies 0.05% of legs and changes 0.43% of
routing answers — an amplification of 8.3x at one range limit, 1.6x at another
and 65x at a third.

The obvious repair is to make the manifest carry an amplification factor, or a
function of some property of the data. **Two attempts at that predictor were
refuted on real data:**

* graph density / reachable fraction: Spearman **0.650** against the observed
  change rate, over ten range limits;
* degree-product centrality of the perturbed edges: **+0.333** for the maximum,
  **+0.283** summed, and **+0.067** for the sheer number of flipped edges.

Nothing cheap predicted it. A true edge-betweenness computation might, and that
is the decisive point rather than a caveat: **Brandes on this graph costs more
than measuring the sensitivity directly.** When the statistic that would predict
the answer is more expensive than the answer, the right design is to measure.

So sensitivity here is an *experiment*, in the same shape as
:mod:`symbolic_ai_core.runtime.margin`: perturb the input the way a real
degradation would, run the real computation, count how many answers moved.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Hashable, Iterable, Sequence

__all__ = ["SensitivityReport", "profile_sensitivity", "input_delta_rate"]


@dataclass(frozen=True)
class SensitivityReport:
    """What a perturbation did to the inputs, and what it did to the answers."""

    label: str
    inputs_total: int
    inputs_changed: int
    answers_total: int
    answers_changed: int

    @property
    def input_rate(self) -> float:
        return self.inputs_changed / self.inputs_total if self.inputs_total else 0.0

    @property
    def output_rate(self) -> float:
        return (self.answers_changed / self.answers_total
                if self.answers_total else 0.0)

    @property
    def amplification(self) -> float | None:
        """Output change rate over input change rate.

        ``None`` when nothing changed upstream — the honest entry, because a
        perturbation that moved no input tells you nothing about amplification
        and reporting 0.0 would read as "this composition is insensitive".
        """
        if not self.inputs_changed:
            return None
        return self.output_rate / self.input_rate

    def summary(self) -> str:
        amp = self.amplification
        return (f"{self.label}: {self.inputs_changed}/{self.inputs_total} inputs "
                f"({self.input_rate:.4%}) -> {self.answers_changed}/"
                f"{self.answers_total} answers ({self.output_rate:.4%}), "
                + (f"{amp:.1f}x" if amp is not None else
                   "amplification undefined: no input moved"))


def input_delta_rate(baseline: dict[Any, Any], perturbed: dict[Any, Any],
                     *, changed: Callable[[Any, Any], bool] | None = None
                     ) -> tuple[int, int]:
    """How many inputs the perturbation actually moved.

    Compares on the **union** of keys, so an input that the perturbation
    deleted or invented counts as changed rather than silently vanishing from
    the denominator.
    """
    keys = set(baseline) | set(perturbed)
    sentinel = object()
    n = 0
    for k in keys:
        a, b = baseline.get(k, sentinel), perturbed.get(k, sentinel)
        if a is sentinel or b is sentinel:
            n += 1
        elif changed(a, b) if changed else a != b:
            n += 1
    return n, len(keys)


def profile_sensitivity(
        answer: Callable[[Any, Hashable], Any],
        baseline: Any, perturbed: Any,
        cases: Sequence[Hashable], *,
        label: str = "",
        inputs: tuple[int, int] = (0, 0)) -> SensitivityReport:
    """Run the real computation twice and count the answers that moved.

    ``answer`` is called as ``answer(state, case)``. Both states must be the
    *same computation* over different inputs — perturbing the algorithm instead
    of the data measures something else, and this signature makes that hard to
    do by accident.

    An answer of ``None`` is compared like any other value: "unreachable" and
    "unreachable" agree, and "unreachable" against "three hops" is a change.
    Treating absence as a missing measurement would drop exactly the cases a
    perturbation is most likely to create.
    """
    changed = sum(1 for c in cases if answer(baseline, c) != answer(perturbed, c))
    return SensitivityReport(label=label, inputs_total=inputs[1],
                             inputs_changed=inputs[0],
                             answers_total=len(cases), answers_changed=changed)
