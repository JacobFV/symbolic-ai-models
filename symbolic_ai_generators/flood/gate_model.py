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


# ---------------------------------------------------------------------------
# the stronger learner, for falsifying the claim the weaker one supports
# ---------------------------------------------------------------------------
@dataclass
class _Node:
    """One node of a regression tree. A leaf carries a value and no children."""

    feature: int = -1
    threshold: float = 0.0
    value: float = 0.0
    left: "_Node | None" = None
    right: "_Node | None" = None

    @property
    def is_leaf(self) -> bool:
        return self.left is None

    def predict(self, x: Sequence[float]) -> float:
        node = self
        while not node.is_leaf:
            node = node.left if x[node.feature] <= node.threshold else node.right
        return node.value

    def to_dict(self) -> dict[str, Any]:
        if self.is_leaf:
            return {"value": self.value}
        return {"feature": self.feature, "threshold": self.threshold,
                "left": self.left.to_dict(), "right": self.right.to_dict()}

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "_Node":
        if "value" in d and "feature" not in d:
            return cls(value=float(d["value"]))
        return cls(feature=int(d["feature"]), threshold=float(d["threshold"]),
                   left=cls.from_dict(d["left"]), right=cls.from_dict(d["right"]))


def _grow(xs, residuals, depth: int, min_leaf: int) -> _Node:
    """A squared-error regression tree over the residuals. Exhaustive splits.

    Exhaustive because there are nine features and a few hundred rows; a
    histogram or a sampled split would be faster and would put a tuning
    parameter between the question and the answer.
    """
    mean = sum(residuals) / len(residuals)
    if depth == 0 or len(residuals) < 2 * min_leaf:
        return _Node(value=mean)
    total_sse = sum((r - mean) ** 2 for r in residuals)
    best = None
    for j in range(len(xs[0])):
        order = sorted(range(len(xs)), key=lambda i: xs[i][j])
        values = [xs[i][j] for i in order]
        res = [residuals[i] for i in order]
        left_sum = left_n = 0.0
        right_sum, right_n = sum(res), float(len(res))
        for k in range(len(res) - 1):
            left_sum += res[k]
            left_n += 1
            right_sum -= res[k]
            right_n -= 1
            if values[k] == values[k + 1] or left_n < min_leaf or right_n < min_leaf:
                continue
            sse = -(left_sum ** 2 / left_n + right_sum ** 2 / right_n)
            if best is None or sse < best[0]:
                best = (sse, j, (values[k] + values[k + 1]) / 2.0)
    if best is None:
        return _Node(value=mean)
    _, j, thr = best
    li = [i for i in range(len(xs)) if xs[i][j] <= thr]
    ri = [i for i in range(len(xs)) if xs[i][j] > thr]
    if not li or not ri:
        return _Node(value=mean)
    return _Node(feature=j, threshold=thr,
                 left=_grow([xs[i] for i in li], [residuals[i] for i in li],
                            depth - 1, min_leaf),
                 right=_grow([xs[i] for i in ri], [residuals[i] for i in ri],
                             depth - 1, min_leaf))


@dataclass
class BoostedGate:
    """Gradient boosting on the logistic loss. **Beside** :class:`GateModel`.

    It exists to falsify a claim the linear model supports: that the routing
    headroom left on the table is unreachable *in principle*, because
    coincidental agreement between the cheap and full answers is not predictable
    from cheap features. If a stronger learner on the same features captures
    materially more, that explanation is wrong and the linear model was simply
    too weak.

    Registered as its own class rather than replacing the logistic one, because
    a model that answers a different question about the same data is a second
    row in the table, not an upgrade.
    """

    trees: list[_Node] = field(default_factory=list)
    base: float = 0.0
    lr: float = 0.1
    threshold: float = 0.5
    features: tuple[str, ...] = FEATURES
    fitted_on: str = ""
    n_train: int = 0

    def raw(self, x: Sequence[float]) -> float:
        return self.base + self.lr * sum(t.predict(x) for t in self.trees)

    def score(self, x: Sequence[float]) -> float:
        z = self.raw(x)
        return 1.0 / (1.0 + math.exp(-max(-60.0, min(60.0, z))))

    def take_cheap(self, x: Sequence[float]) -> bool:
        return self.score(x) >= self.threshold

    def to_dict(self) -> dict[str, Any]:
        return {"trees": [t.to_dict() for t in self.trees], "base": self.base,
                "lr": self.lr, "threshold": self.threshold,
                "features": list(self.features), "fitted_on": self.fitted_on,
                "n_train": self.n_train}

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "BoostedGate":
        feats = tuple(d.get("features") or FEATURES)
        if feats != FEATURES:
            raise ValueError(f"fitted on {list(feats)}, current order is "
                             f"{list(FEATURES)}")
        return cls(trees=[_Node.from_dict(t) for t in d["trees"]],
                   base=float(d["base"]), lr=float(d.get("lr", 0.1)),
                   threshold=float(d.get("threshold", 0.5)), features=feats,
                   fitted_on=str(d.get("fitted_on", "")),
                   n_train=int(d.get("n_train", 0)))

    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dict(), indent=1), encoding="utf-8")


def fit_boosted(rows: Sequence[tuple[Sequence[float], int]], *,
                n_trees: int = 60, depth: int = 3, lr: float = 0.2,
                min_leaf: int = 10, fitted_on: str = "") -> BoostedGate:
    """Logistic gradient boosting. Deliberately small; see :class:`BoostedGate`."""
    if not rows:
        raise ValueError("no training rows")
    xs = [list(x) for x, _ in rows]
    ys = [float(y) for _, y in rows]
    rate = max(min(sum(ys) / len(ys), 1 - 1e-6), 1e-6)
    base = math.log(rate / (1 - rate))
    model = BoostedGate(base=base, lr=lr, fitted_on=fitted_on, n_train=len(rows))
    f = [base] * len(rows)
    for _ in range(n_trees):
        p = [1.0 / (1.0 + math.exp(-max(-60.0, min(60.0, v)))) for v in f]
        residuals = [y - pi for y, pi in zip(ys, p)]
        tree = _grow(xs, residuals, depth, min_leaf)
        model.trees.append(tree)
        for i, x in enumerate(xs):
            f[i] += lr * tree.predict(x)
    return model
