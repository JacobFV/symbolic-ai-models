"""A learned routing gate: logistic regression, fitted and saved as an artifact.

Small and inspectable on purpose. The gate has to be *cheaper than what it
gates*, so the model is nine weights and a dot product — and it has to be
auditable, so the weights are printable and the artifact is JSON.

The discipline around it is the repo's standing one, and it is what makes the
number mean anything:

* **fitted on training seeds**, tuned on a **development** split, and reported on
  **evaluation** seeds it never saw;
* scored on the **constrained** objective — cheapest arm achieving accuracy at
  least *a* — because the unconstrained ratio has a perverse regime far above
  the floor and would reward a gate that gives accuracy away;
* placed **beside** the hand-written gate rather than replacing it, so one run
  prints both.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from .features import FEATURES

__all__ = ["GateModel", "fit"]


@dataclass
class GateModel:
    """``P(the cheap answer matches the full answer | features)``."""

    weights: list[float] = field(default_factory=lambda: [0.0] * len(FEATURES))
    features: tuple[str, ...] = FEATURES
    #: Route to the cheap arm only when the predicted probability clears this.
    #: Tuned on the development split against an accuracy bar, never on eval.
    threshold: float = 0.5
    fitted_on: str = ""
    n_train: int = 0

    def score(self, x: Sequence[float]) -> float:
        z = sum(w * v for w, v in zip(self.weights, x))
        return 1.0 / (1.0 + math.exp(-max(-60.0, min(60.0, z))))

    def take_cheap(self, x: Sequence[float]) -> bool:
        return self.score(x) >= self.threshold

    def to_dict(self) -> dict[str, Any]:
        return {"weights": list(self.weights), "features": list(self.features),
                "threshold": self.threshold, "fitted_on": self.fitted_on,
                "n_train": self.n_train}

    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dict(), indent=1), encoding="utf-8")

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "GateModel":
        feats = tuple(d.get("features") or FEATURES)
        if feats != FEATURES:
            raise ValueError(
                f"this model was fitted on {list(feats)} and the current "
                f"feature order is {list(FEATURES)}. A weight vector against a "
                f"different ordering is not broken, it is merely worse, which "
                f"is the harder failure to notice.")
        return cls(weights=list(d["weights"]), features=feats,
                   threshold=float(d.get("threshold", 0.5)),
                   fitted_on=str(d.get("fitted_on", "")),
                   n_train=int(d.get("n_train", 0)))

    @classmethod
    def load(cls, path: str | Path) -> "GateModel":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def explain(self) -> str:
        pairs = sorted(zip(self.features, self.weights),
                       key=lambda p: -abs(p[1]))
        return "  ".join(f"{n}={w:+.2f}" for n, w in pairs)


def fit(rows: Sequence[tuple[Sequence[float], int]], *, epochs: int = 400,
        lr: float = 0.5, l2: float = 1e-3, fitted_on: str = "") -> GateModel:
    """Plain batch gradient descent on the logistic loss. No framework.

    Nine weights over a few thousand rows does not need one, and a fitted
    parameter this repo cannot print is a fitted parameter it cannot audit —
    which is a standing lesson here, not a style preference.
    """
    if not rows:
        raise ValueError("no training rows: a gate fitted on nothing would "
                         "route on its bias term")
    n_features = len(rows[0][0])
    w = [0.0] * n_features
    n = len(rows)
    for _ in range(epochs):
        grad = [0.0] * n_features
        for x, y in rows:
            z = sum(wi * xi for wi, xi in zip(w, x))
            p = 1.0 / (1.0 + math.exp(-max(-60.0, min(60.0, z))))
            err = p - y
            for j, xi in enumerate(x):
                grad[j] += err * xi
        for j in range(n_features):
            w[j] -= lr * (grad[j] / n + l2 * w[j])
    return GateModel(weights=w, fitted_on=fitted_on, n_train=n)
