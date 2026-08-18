"""Combining several kernels' claims about one property — or declining to.

Kernels propose; something has to decide. That decision is **property-specific
and cannot be defaulted**, which is the entire content of this module:

============================  ==========================================
property                      how it combines
============================  ==========================================
forces, fluxes, counts        sum
probabilities (consensus)     log-opinion pool
probabilities (independent)   odds multiplication, prior stated
intervals, constraints        intersection
poses, estimates              inverse-variance weighted mean
proof validity                an exact kernel's veto
policy or legal authority     precedence
alternative hypotheses        **keep the mixture**
============================  ==========================================

The default is the last row. A property with no registered rule produces an
*unresolved group*, not a winner — because the alternative is last-writer-wins,
and last-writer-wins is indistinguishable from a correct answer at the point
where it is read. Nothing here averages two arbitrary state vectors; that
operation is meaningless and its plausibility is what makes it dangerous.

Two further rules the code enforces rather than documents:

* **Authority beats agreement.** A ``veto`` claim from a kernel that declared
  authority over a property removes the proposals it contradicts, whatever the
  count. An exact solver saying a configuration is infeasible is not one vote.
* **Incompatible units do not fuse.** Two masses in kg and lb are not two
  readings to be averaged; they are a question about which one is right, and it
  goes to the unresolved pile.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping, Sequence, Sequence

from ..world import Claim, EntityRef, Quantity

__all__ = ["ClaimGroup", "FusionResult", "FUSION_RULES", "register_fusion",
           "group_claims", "fuse", "sum_quantities", "log_opinion_pool",
           "independent_odds", "intersect_intervals", "inverse_variance",
           "FusionError"]


class FusionError(ValueError):
    """A fusion that cannot be performed, named rather than approximated."""


@dataclass(frozen=True)
class ClaimGroup:
    """Every claim about one ``(predicate, subject)``. The unit of fusion."""

    predicate: str
    subject: tuple[str, ...]
    claims: tuple[Claim, ...]

    @property
    def key(self) -> tuple[str, tuple[str, ...]]:
        return self.predicate, self.subject

    def producers(self) -> tuple[str, ...]:
        return tuple(sorted({c.provenance.producer for c in self.claims}))

    def agree(self) -> bool:
        """Whether every claim in the group says the same thing."""
        first = self.claims[0].to_dict()
        keep = ("predicate", "roles", "polarity")
        base = {k: first[k] for k in keep}
        return all({k: c.to_dict()[k] for k in keep} == base
                   for c in self.claims[1:])


@dataclass(frozen=True)
class FusionResult:
    """What survived, what was vetoed, and what nobody was entitled to settle."""

    resolved: tuple[Claim, ...] = ()
    unresolved: tuple[ClaimGroup, ...] = ()
    vetoed: tuple[Claim, ...] = ()
    notes: tuple[str, ...] = ()

    @property
    def settled(self) -> bool:
        return not self.unresolved

    def to_dict(self) -> dict[str, Any]:
        return {"resolved": [c.to_dict() for c in self.resolved],
                "unresolved": [{"predicate": g.predicate,
                                "subject": list(g.subject),
                                "n": len(g.claims),
                                "producers": list(g.producers())}
                               for g in self.unresolved],
                "vetoed": [c.to_dict() for c in self.vetoed],
                "notes": list(self.notes)}


#: ``predicate -> (group) -> Claim``. Deliberately empty of defaults.
FusionRule = Callable[[ClaimGroup], Claim]
FUSION_RULES: dict[str, FusionRule] = {}


def register_fusion(predicate: str, rule: FusionRule) -> None:
    """Declare how one property combines. Re-registering is refused.

    Silently replacing a fusion rule would redefine every number computed under
    the old one, which is the same defect as editing a registered model in
    place — and this repo has paid for that twice.
    """
    if predicate in FUSION_RULES:
        raise ValueError(
            f"a fusion rule for {predicate!r} is already registered. Replacing "
            f"it would silently redefine every result computed under the old "
            f"one; register a differently-named property instead.")
    FUSION_RULES[predicate] = rule


# ---------------------------------------------------------------------------
# grouping
# ---------------------------------------------------------------------------
def _subject(claim: Claim) -> tuple[str, ...]:
    """The entities a claim is *about*, as its fusion key.

    Entity roles only. Two claims about the same entity with different numeric
    values are competing readings; two claims with different entities are not
    about the same thing at all, and grouping on the whole role map would make
    every claim its own group and fusion a no-op.
    """
    return tuple(sorted(v.id for v in claim.roles.values()
                        if isinstance(v, EntityRef)))


def group_claims(claims: Iterable[Claim]) -> list[ClaimGroup]:
    """Group by ``(predicate, subject)`` and then split on **disjoint times**.

    Two poses of one body, one for t+0.1s and one for t+0.9s, are not two
    readings of one state -- they are two states. Fusing them by inverse variance
    produced a position at no time at all, silently, because from fusion's point
    of view that is its job. The predicate is the type and *the time is part of
    it*.

    An untimed claim has an unbounded interval and still combines with anything,
    which is the correct reading of "this claim does not say when".
    """
    buckets: dict[tuple[str, tuple[str, ...]], list[Claim]] = {}
    for c in claims:
        buckets.setdefault((c.predicate, _subject(c)), []).append(c)
    out: list[ClaimGroup] = []
    for (pred, subj), cs in sorted(buckets.items()):
        for chunk in _split_disjoint_times(cs):
            out.append(ClaimGroup(pred, subj, tuple(chunk)))
    return out


def _split_disjoint_times(claims: Sequence[Claim]) -> list[list[Claim]]:
    """Partition into runs whose validity can refer to the same moment.

    Transitive by construction: a claim joins a run when it overlaps *every*
    member, so a chain of pairwise-overlapping-but-collectively-inconsistent
    intervals does not get merged into one.
    """
    runs: list[list[Claim]] = []
    for c in claims:
        for run in runs:
            if all(c.valid_time.overlaps(o.valid_time) for o in run):
                run.append(c)
                break
        else:
            runs.append([c])
    return runs


# ---------------------------------------------------------------------------
# rules
# ---------------------------------------------------------------------------
def _quantities(group: ClaimGroup, role: str = "value") -> list[Quantity]:
    out = []
    for c in group.claims:
        q = c.roles.get(role)
        if not isinstance(q, Quantity):
            raise FusionError(
                f"{group.predicate}: claim from {c.provenance.producer or '?'} "
                f"has no Quantity in role {role!r}; this rule combines "
                f"measurements and cannot combine whatever else this is")
        out.append(q)
    units = {q.unit for q in out}
    if len(units) > 1:
        raise FusionError(
            f"{group.predicate}: claims arrive in {sorted(units)}. Two readings "
            f"in different units are a question about which is right, not two "
            f"numbers to combine -- convert explicitly upstream.")
    return out


def sum_quantities(group: ClaimGroup, *, role: str = "value") -> Claim:
    """Forces, fluxes and counts. The one case where adding is the meaning."""
    qs = _quantities(group, role)
    total = sum(q.value for q in qs)
    # Independent errors add in quadrature; a stated stderr that is missing on
    # any contributor makes the total's stderr unknown rather than optimistic.
    stderrs = [q.stderr for q in qs]
    err = (math.sqrt(sum(s * s for s in stderrs))
           if all(s is not None for s in stderrs) else None)
    return _combined(group, {role: Quantity(total, qs[0].unit, err)},
                     method="sum")


def _confidences(group: ClaimGroup) -> list[float]:
    confs = [c.confidence for c in group.claims if c.confidence is not None]
    if not confs:
        raise FusionError(
            f"{group.predicate}: no claim states a confidence. Treating "
            f"'not stated' as 1.0 would manufacture certainty.")
    if not group.agree():
        raise FusionError(
            f"{group.predicate}: the claims disagree about content, so pooling "
            f"their confidences would produce a confidence in nothing")
    return confs


def log_opinion_pool(group: ClaimGroup) -> Claim:
    """**Consensus** over probabilities: the normalised geometric mean.

    This is an *averaging* operator and it deliberately does not reinforce. Two
    sources at 0.9 pool to 0.9, not higher — the same way two thermometers
    reading 20 degrees do not imply 25. Reinforcement is a different operation
    (:func:`independent_odds`) and requires an independence assumption that is
    usually false, because correlated sources are the normal case: two models
    trained on one corpus, two analysts reading one report.

    It is preferred to a linear average because it is the pool that behaves
    correctly under *disagreement* — one source at 0.99 and one at 0.01 pools to
    0.5 either way, but a source at 0.0 vetoes the pool here rather than being
    outvoted, which is the right reading of "this is impossible".
    """
    confs = _confidences(group)
    eps = 1e-12
    lo = sum(math.log(max(p, eps)) for p in confs) / len(confs)
    lc = sum(math.log(max(1 - p, eps)) for p in confs) / len(confs)
    g, gc = math.exp(lo), math.exp(lc)
    return _combined(group, dict(group.claims[0].roles),
                     method="log-opinion pool (consensus)",
                     confidence=g / (g + gc))


def independent_odds(group: ClaimGroup, *, prior: float = 0.5) -> Claim:
    """**Reinforcing** fusion: multiply likelihood ratios against a prior.

    Two independent sources at 0.9 give roughly 0.99, which is the behaviour
    people usually mean by "combining evidence". It is only correct when the
    sources really are independent given the truth, and this is not the default
    for exactly that reason — the failure is silent and always in the confident
    direction.

    ``prior`` is explicit and has no default answer either; 0.5 is a *stated
    ignorance*, not a fact about the world. It is also not a knob that only
    scales the output: a source reporting 0.9 against a prior of 0.01 has
    supplied enormous evidence, while the same 0.9 against a prior of 0.9 has
    supplied none, so a *lower* prior yields a *higher* posterior for identical
    reports. Getting that backwards is easy and the test pins it.
    """
    confs = _confidences(group)
    eps = 1e-12
    prior_odds = prior / max(1 - prior, eps)
    odds = prior_odds
    for p in confs:
        p = min(max(p, eps), 1 - eps)
        odds *= (p / (1 - p)) / prior_odds
    post = odds / (1 + odds)
    return _combined(group, dict(group.claims[0].roles),
                     method=f"independent odds (prior {prior})",
                     confidence=post)


def inverse_variance(group: ClaimGroup, *, role: str = "value") -> Claim:
    """Estimates with error bars, combined by precision. The pose rule.

    Weight each reading by ``1/sigma^2`` and take the weighted mean; the fused
    error is ``1/sqrt(sum of weights)``, which is **smaller than either input**.
    That is the whole reason a predictor and a sensor are worth having together,
    and it is the standard result — not a heuristic.

    **A reading with no stated error is refused, not treated as exact.** An
    infinite weight would let one claim dominate completely while looking like a
    very good measurement, and `None` here means *not stated*, which is the one
    thing it definitely does not mean. That refusal is why
    :mod:`symbolic_ai_kernels.rigid` goes to the trouble of growing an honest
    error bar through its integration step.
    """
    qs = _quantities(group, role)
    missing = [c.provenance.producer or "?" for c, q in zip(group.claims, qs)
               if q.stderr is None]
    if missing:
        raise FusionError(
            f"{group.predicate}: {missing} state no error bar. Treating an "
            f"unstated error as zero gives that claim infinite weight, which "
            f"looks exactly like a very good measurement and is not one.")
    if any(q.stderr <= 0 for q in qs):
        raise FusionError(
            f"{group.predicate}: a zero or negative error bar claims infinite "
            f"precision; nothing this kernel stack produces is exact.")
    weights = [1.0 / (q.stderr ** 2) for q in qs]
    total = sum(weights)
    value = sum(w * q.value for w, q in zip(weights, qs)) / total
    return _combined(group, {role: Quantity(value, qs[0].unit,
                                            math.sqrt(1.0 / total))},
                     method="inverse-variance weighted mean")


def intersect_intervals(group: ClaimGroup, *, role: str = "value") -> Claim:
    """Constraints: the answer is what every source allows, or nothing."""
    qs = _quantities(group, role)
    lo = max(q.value - (q.stderr or 0.0) for q in qs)
    hi = min(q.value + (q.stderr or 0.0) for q in qs)
    if lo > hi:
        raise FusionError(
            f"{group.predicate}: the intervals are disjoint ({lo:g} > {hi:g}). "
            f"An empty intersection is a contradiction between sources, not a "
            f"midpoint.")
    mid = (lo + hi) / 2
    return _combined(group, {role: Quantity(mid, qs[0].unit, (hi - lo) / 2)},
                     method="interval intersection")


def _combined(group: ClaimGroup, roles: Mapping[str, Any], *, method: str,
              confidence: float | None = None) -> Claim:
    from ..artifact.value import Provenance
    return Claim(
        predicate=group.predicate, roles=dict(roles), modality="asserted",
        confidence=confidence,
        provenance=Provenance(producer="fuse",
                              inputs=tuple(group.producers()),
                              method=f"{method} over {len(group.claims)} claims"))


# ---------------------------------------------------------------------------
# fusion
# ---------------------------------------------------------------------------
def fuse(claims: Iterable[Claim], *,
         rules: Mapping[str, FusionRule] | None = None,
         authority: Mapping[str, Mapping[str, str]] | None = None,
         ) -> FusionResult:
    """Combine claims, keeping every mixture nobody was entitled to settle.

    ``authority`` maps producer -> ``{property: veto|propose|observe}``, and is
    normally each kernel's ``manifest.authority``. A veto removes the proposals
    it contradicts *whatever the count*: an exact solver saying a configuration
    is infeasible is not one vote among several.
    """
    rules = {**FUSION_RULES, **(rules or {})}
    authority = authority or {}
    resolved: list[Claim] = []
    unresolved: list[ClaimGroup] = []
    vetoed: list[Claim] = []
    notes: list[str] = []

    for group in group_claims(claims):
        kept, killed = _apply_vetoes(group, authority)
        vetoed.extend(killed)
        if not kept:
            notes.append(f"{group.predicate}: every claim was vetoed")
            continue
        group = ClaimGroup(group.predicate, group.subject, tuple(kept))

        if len(group.claims) == 1:
            resolved.append(group.claims[0])
            continue
        if group.agree():
            resolved.append(group.claims[0])
            continue
        rule = rules.get(group.predicate)
        if rule is None:
            # The default, and the reason this module exists.
            unresolved.append(group)
            notes.append(
                f"{group.predicate}: {len(group.claims)} disagreeing claims "
                f"from {list(group.producers())} and no fusion rule -- kept as "
                f"a mixture rather than resolved by arrival order")
            continue
        try:
            resolved.append(rule(group))
        except FusionError as e:
            unresolved.append(group)
            notes.append(str(e))

    return FusionResult(tuple(resolved), tuple(unresolved), tuple(vetoed),
                        tuple(notes))


def _apply_vetoes(group: ClaimGroup,
                  authority: Mapping[str, Mapping[str, str]]
                  ) -> tuple[list[Claim], list[Claim]]:
    """Split a group into what survives its vetoes and what those vetoes kill.

    A veto is expressed as a **negative** claim from a producer with declared
    veto authority over the property: *this does not hold*. It removes the
    positive proposals about the same subject and does not itself become one.
    """
    vetoes = [c for c in group.claims
              if c.polarity == "negative"
              and authority.get(c.provenance.producer, {}).get(
                  group.predicate) == "veto"]
    if not vetoes:
        return list(group.claims), []
    killed = [c for c in group.claims
              if c.polarity == "positive" and c not in vetoes]
    return list(vetoes), killed
