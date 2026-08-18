"""Dimensional checking for the constraint language, done before the solver.

SMT is untyped about units. ``mass < 20`` is satisfiable whether the 20 is
kilograms or pounds, and z3 will happily tell you so — which is precisely the
failure this repo keeps naming: a shared substrate that converts silently moves
results further than any model does.

So units are checked **at projection**, and a mismatch is a **refusal, not a
discard**. That distinction is deliberate. A discard says "I could not carry
this part of your world"; comparing a mass to a length is not an unrepresentable
part of the world, it is a malformed question, and answering it would be worse
than declining.

The algebra is deliberately tiny: units are compared as strings, products and
quotients compose into a canonical form, and there is no conversion table. A
conversion belongs in an explicit node in the flow graph where the trace can
show it — the same rule the port checker enforces one layer up.
"""

from __future__ import annotations

from collections import Counter

__all__ = ["Unit", "DIMENSIONLESS", "UnitError", "parse_unit", "mul", "div",
           "same"]


class UnitError(ValueError):
    """A dimensional mismatch. The question is malformed, not the world."""


Unit = str
DIMENSIONLESS: Unit = "1"


def parse_unit(text: str) -> Counter:
    """``"kg*m/s/s"`` -> ``{kg: 1, m: 1, s: -2}``. No conversion, only algebra."""
    if not text or text == DIMENSIONLESS:
        return Counter()
    out: Counter = Counter()
    sign = 1
    token = ""
    for ch in text.replace(" ", ""):
        if ch in "*/":
            if token:
                out[token] += sign
            token, sign = "", (1 if ch == "*" else -1)
        else:
            token += ch
    if token:
        out[token] += sign
    # "1" is the dimensionless marker, not a base unit -- "1/s" is a frequency,
    # and letting the literal through makes it a "1 per second" of something.
    return Counter({k: v for k, v in out.items() if v and k != DIMENSIONLESS})


def render(dims: Counter) -> Unit:
    """Canonical text for an exponent map, and it must survive :func:`parse_unit`.

    Denominator factors are joined with ``/``, not ``*``: the parser treats
    ``*`` as "back to the numerator", so ``kg*m/s*s`` reads as ``kg*m`` — the
    two ``s`` cancelling — while ``kg*m/s/s`` reads as the ``kg*m/s^2`` it was
    meant to be. Round-tripping is not a nicety here; every comparison in this
    module goes through the parser.
    """
    if not dims:
        return DIMENSIONLESS
    num = "*".join(sorted(k for k, v in dims.items() for _ in range(max(v, 0))))
    den = "/".join(sorted(k for k, v in dims.items() for _ in range(max(-v, 0))))
    if not num:
        return "1/" + den
    return num + ("/" + den if den else "")


def same(a: Unit, b: Unit, *, where: str = "") -> Unit:
    if parse_unit(a) != parse_unit(b):
        raise UnitError(
            f"{where or 'this comparison'} puts {a or '<none>'} beside "
            f"{b or '<none>'}. There is no conversion table here on purpose: a "
            f"conversion belongs in an explicit node where the trace can show "
            f"it.")
    return a


def _combine(a: Unit, b: Unit, sign: int) -> Unit:
    """Exponent arithmetic by hand.

    ``Counter`` addition and subtraction silently drop non-positive counts, so
    ``Counter({"kg": 1}) - Counter({"s": 1})`` is ``{"kg": 1}`` and ``kg/s``
    comes out as ``kg``. That is a unit error produced by the unit checker,
    which is the worst possible place for one.
    """
    out: dict[str, int] = dict(parse_unit(a))
    for k, v in parse_unit(b).items():
        out[k] = out.get(k, 0) + sign * v
    return render(Counter({k: v for k, v in out.items() if v}))


def mul(a: Unit, b: Unit) -> Unit:
    return _combine(a, b, 1)


def div(a: Unit, b: Unit) -> Unit:
    return _combine(a, b, -1)
