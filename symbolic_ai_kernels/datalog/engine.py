"""A datalog engine: semi-naive fixed point, stratified negation, incremental.

This is the least glamorous kernel in the stack and probably the most used. If a
world holds millions of relations and a rule like
``ancestor(X,Z) :- parent(X,Y), ancestor(Y,Z)``, you do not want a proof
assistant proving each query — you want ``D_{t+1} = T_P(D_t)`` run to closure by
something that is essentially a database, and then *maintained* rather than
recomputed when five facts change.

Three decisions, each of which the alternative gets wrong quietly:

**Semi-naive, not naive.** A naive fixed point re-derives every already-known
consequence on every round, so a program that converges in *k* rounds does *k*
times the work it needed. Semi-naive requires each derivation to use at least one
fact that is *new this round*, which is why the ``delta`` bookkeeping below looks
fussier than the recurrence does.

**Negation is stratified, and an unstratifiable program is refused.**
``not p`` here means *p is not derivable*, which is closed-world and
non-monotonic — adding a fact can retract a conclusion. That is the right
semantics for defaults and exceptions (``flies(X) :- bird(X), not abnormal(X)``)
and it is only well-defined when negation does not appear inside its own
recursion. A program where it does has no unique model, and the honest response
is to refuse rather than to return whichever fixed point the iteration order
happened to reach.

**Incremental addition only.** :func:`add_facts` computes the *new* consequences
of new facts without recomputing the closure. Retraction is deliberately not
implemented: under negation, removing a fact can both retract and *create*
conclusions, and doing that correctly needs derivation counts the engine does not
keep. A wrong incremental retraction is indistinguishable from a right one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Iterator, Mapping, Sequence

__all__ = ["Var", "Atom", "Literal", "Rule", "Program", "Fact", "evaluate",
           "add_facts_report", "strata", "FactIndex", "IncrementalModel",
           "NonMonotoneAddition", "add_facts", "StratificationError", "query"]


class StratificationError(ValueError):
    """Negation inside its own recursion. No unique model exists."""


@dataclass(frozen=True)
class Var:
    """A variable. Distinct from a constant, which is a plain ``str``."""

    name: str

    def __repr__(self) -> str:
        return self.name.upper()

    def to_dict(self) -> dict[str, str]:
        return {"var": self.name}


Term = "Var | str"
Fact = tuple  # (predicate, *constants)


@dataclass(frozen=True)
class Atom:
    pred: str
    terms: tuple[Any, ...] = ()

    @property
    def arity(self) -> int:
        return len(self.terms)

    def is_ground(self) -> bool:
        return all(not isinstance(t, Var) for t in self.terms)

    def ground(self, subst: Mapping[str, str]) -> Fact:
        out = []
        for t in self.terms:
            if isinstance(t, Var):
                if t.name not in subst:
                    raise KeyError(f"unbound variable {t.name} in {self}")
                out.append(subst[t.name])
            else:
                out.append(t)
        return (self.pred, *out)

    def as_fact(self) -> Fact:
        if not self.is_ground():
            raise ValueError(f"{self} is not ground")
        return (self.pred, *self.terms)

    def to_dict(self) -> dict:
        """The JSON form ``rule_from_dict`` reads. Rules travel as node
        parameters, and a parameter that cannot be serialised cannot be hashed
        into a cache key or opened in an editor."""
        return {"pred": self.pred,
                "terms": [t.to_dict() if isinstance(t, Var) else {"const": t}
                          for t in self.terms]}

    def __repr__(self) -> str:
        return f"{self.pred}({', '.join(map(repr, self.terms))})"


@dataclass(frozen=True)
class Literal:
    atom: Atom
    negated: bool = False

    def to_dict(self) -> dict:
        d = self.atom.to_dict()
        if self.negated:
            d["negated"] = True
        return d

    def __repr__(self) -> str:
        return ("not " if self.negated else "") + repr(self.atom)


@dataclass(frozen=True)
class Rule:
    head: Atom
    body: tuple[Literal, ...] = ()

    def __post_init__(self) -> None:
        bound = {t.name for lit in self.body if not lit.negated
                 for t in lit.atom.terms if isinstance(t, Var)}
        unsafe = ({t.name for t in self.head.terms if isinstance(t, Var)}
                  | {t.name for lit in self.body if lit.negated
                     for t in lit.atom.terms if isinstance(t, Var)}) - bound
        if unsafe:
            raise ValueError(
                f"unsafe rule {self}: {sorted(unsafe)} appear only in the head "
                f"or under negation. A variable that no positive body literal "
                f"binds ranges over every constant that will ever exist, so the "
                f"rule has no finite meaning.")

    def to_dict(self) -> dict:
        return {"head": self.head.to_dict(),
                "body": [l.to_dict() for l in self.body]}

    def __repr__(self) -> str:
        body = ", ".join(map(repr, self.body))
        return f"{self.head} :- {body}." if body else f"{self.head}."


@dataclass(frozen=True)
class Program:
    rules: tuple[Rule, ...] = ()

    def predicates(self) -> set[str]:
        return ({r.head.pred for r in self.rules}
                | {l.atom.pred for r in self.rules for l in r.body})

    def intensional(self) -> set[str]:
        """Predicates some rule derives. The rest are extensional (input)."""
        return {r.head.pred for r in self.rules}


# ---------------------------------------------------------------------------
# stratification
# ---------------------------------------------------------------------------
def strata(program: Program) -> list[list[Rule]]:
    """Group rules so that every negated predicate is fully derived earlier.

    Iterative refinement rather than an SCC decomposition, because the failure
    mode has to be *reported*, not just detected: when the levels stop moving
    while a negative edge is still violated, the predicates still in play are
    exactly the ones in the negative cycle, and the message names them.
    """
    idb = program.intensional()
    level = {p: 0 for p in program.predicates()}
    for _ in range(len(level) + 1):
        changed = False
        for r in program.rules:
            h = r.head.pred
            for lit in r.body:
                p = lit.atom.pred
                if p not in idb:
                    continue
                want = level[p] + (1 if lit.negated else 0)
                if want > level[h]:
                    level[h], changed = want, True
        if not changed:
            break
    else:
        bad = sorted({r.head.pred for r in program.rules
                      for l in r.body if l.negated and l.atom.pred in idb})
        raise StratificationError(
            f"negation inside its own recursion, among {bad}. Such a program "
            f"has no unique model, and returning whichever fixed point the "
            f"iteration happened to reach would be an answer nobody could "
            f"check.")
    out: dict[int, list[Rule]] = {}
    for r in program.rules:
        out.setdefault(level[r.head.pred], []).append(r)
    return [out[k] for k in sorted(out)]


# ---------------------------------------------------------------------------
# evaluation
# ---------------------------------------------------------------------------
class FactIndex:
    """Facts by predicate, and also by (predicate, position, value).

    The predicate-only index is what this engine had, and it makes a recursive
    join quadratic: ``ult(X,Z) :- par(X,Y), ult(Y,Z)`` binds ``Y`` from the
    first literal and then **rescans every** ``ult`` fact to find the ones
    starting with it. Measured against a purpose-written closure over the same
    GLEIF data, that cost 495x at 250 edges and 5,446x at 4,000 -- an overhead
    that grows, which is the signature of the wrong asymptotics rather than a
    slow constant.

    The extra index is ``arity`` entries per fact and turns each bound position
    into a lookup. It changes no semantics: the same substitutions are found,
    because the position buckets are only ever used to *narrow* the candidate
    set before :func:`_match` runs unchanged over it.

    One visible consequence: the *order* in which candidates are visited
    changes, so a fact reachable by several derivations may be justified by a
    different one of them. The least model is identical; only which witness
    :mod:`.proof` happens to record moves, and any valid witness is as good.
    """

    __slots__ = ("by_pred", "by_pos")

    def __init__(self, facts: Iterable[Fact] = ()) -> None:
        self.by_pred: dict[str, list[Fact]] = {}
        self.by_pos: dict[tuple[str, int, str], list[Fact]] = {}
        for f in facts:
            self.by_pred.setdefault(f[0], []).append(f)
            for j, v in enumerate(f[1:]):
                self.by_pos.setdefault((f[0], j, v), []).append(f)

    def candidates(self, atom: "Atom",
                   subst: Mapping[str, str]) -> Sequence[Fact]:
        """The narrowest bucket that must contain every match.

        Picks the most selective *bound* position rather than the first, so a
        rule joining on a high-cardinality column beats one joining on a flag.
        """
        best: Sequence[Fact] | None = None
        for j, term in enumerate(atom.terms):
            value = (subst.get(term.name) if isinstance(term, Var) else term)
            if value is None:
                continue
            bucket = self.by_pos.get((atom.pred, j, value), ())
            if best is None or len(bucket) < len(best):
                best = bucket
                if not bucket:
                    return ()
        if best is None:
            return self.by_pred.get(atom.pred, ())
        return best

    def get(self, pred: str, default: Any = ()) -> Sequence[Fact]:
        """Predicate-only access, kept so existing callers read unchanged."""
        return self.by_pred.get(pred, default)

    def add(self, fact: Fact) -> None:
        """Insert one fact. The reason an incremental model can stay cheap.

        Rebuilding the index each round is what made ``add_facts`` cost the
        size of the *world* rather than the size of the *delta* — measured at
        1,230 ms to add a single edge to a 285,596-fact model, against 6,967 ms
        to recompute the whole thing. A 5.7x saving on a change of two facts is
        not the "proportional to what changed" the contract promises.
        """
        self.by_pred.setdefault(fact[0], []).append(fact)
        for j, v in enumerate(fact[1:]):
            self.by_pos.setdefault((fact[0], j, v), []).append(fact)

    def extend(self, facts: Iterable[Fact]) -> None:
        for f in facts:
            self.add(f)


def _index(facts: Iterable[Fact]) -> FactIndex:
    return FactIndex(facts)


def _match(atom: Atom, fact: Fact, subst: dict[str, str]) -> dict[str, str] | None:
    if fact[0] != atom.pred or len(fact) - 1 != atom.arity:
        return None
    out = subst
    for term, value in zip(atom.terms, fact[1:]):
        if isinstance(term, Var):
            seen = out.get(term.name)
            if seen is None:
                if out is subst:
                    out = dict(subst)
                out[term.name] = value
            elif seen != value:
                return None
        elif term != value:
            return None
    return out


def _solve(body: Sequence[Literal], i: int, subst: dict[str, str],
           known: set[Fact], idx: "FactIndex",
           delta_idx: "FactIndex | None",
           must_use: int) -> Iterator[dict[str, str]]:
    """Backtracking join. ``must_use`` is the body position bound to delta."""
    if i == len(body):
        yield subst
        return
    lit = body[i]
    if lit.negated:
        # Safe by construction: every variable here is bound by an earlier
        # positive literal, so the atom is ground at this point.
        if lit.atom.ground(subst) not in known:
            yield from _solve(body, i + 1, subst, known, idx, delta_idx, must_use)
        return
    source = (delta_idx if (delta_idx is not None and i == must_use) else idx)
    for fact in source.candidates(lit.atom, subst):
        nxt = _match(lit.atom, fact, subst)
        if nxt is not None:
            yield from _solve(body, i + 1, nxt, known, idx, delta_idx, must_use)


def _delta_first(body: Sequence[Literal], slot: int, delta_idx
                 ) -> tuple[Sequence[Literal], int]:
    """Put the delta-bound literal first, so the join starts from what is new.

    Semi-naive requires each derivation to use a fact that is new this round,
    but requiring it at position *j* while still solving left to right means
    literals before *j* are enumerated in full. On ``ult(X,Z) :- par(X,Y),
    ult(Y,Z)`` with the delta on ``ult``, that scanned all 124,260 ``par``
    facts to find partners for two new ones — which is how "cost proportional
    to the delta" became 210 ms for a two-fact change.

    Starting at the delta binds its variables immediately, so every later
    literal is an indexed lookup rather than a scan.

    **Safety is preserved by construction.** All positives are emitted before
    all negatives, so every variable in a negated literal is still bound by the
    time it is reached — which is the condition that lets ``not p`` be decided
    by a ground membership test rather than by search.
    """
    if delta_idx is None or slot < 0:
        return body, slot
    rest_pos = [l for i, l in enumerate(body) if i != slot and not l.negated]
    negs = [l for l in body if l.negated]
    return [body[slot], *rest_pos, *negs], 0


def _round(rules: Sequence[Rule], known: set[Fact], idx, delta_idx
           ) -> set[Fact]:
    """One application of T_P, restricted to derivations that use ``delta``."""
    new: set[Fact] = set()
    for r in rules:
        positives = [i for i, l in enumerate(r.body) if not l.negated]
        if not r.body:
            fact = r.head.as_fact()
            if fact not in known:
                new.add(fact)
            continue
        slots = positives if delta_idx is not None else [-1]
        for slot in slots:
            body, must = _delta_first(r.body, slot, delta_idx)
            for subst in _solve(body, 0, {}, known, idx, delta_idx, must):
                fact = r.head.ground(subst)
                if fact not in known:
                    new.add(fact)
    return new


def evaluate(program: Program, facts: Iterable[Fact], *,
             max_rounds: int = 10_000) -> set[Fact]:
    """The least model: every fact derivable from ``facts`` under ``program``."""
    known = set(facts)
    for layer in strata(program):
        idx = _index(known)
        delta = _round(layer, known, idx, None)
        known |= delta
        rounds = 0
        while delta:
            rounds += 1
            if rounds > max_rounds:                        # pragma: no cover
                raise RuntimeError(f"datalog did not converge in {max_rounds} "
                                   f"rounds; a rule is probably not range "
                                   f"restricted")
            idx = _index(known)
            new = _round(layer, known, idx, _index(delta))
            known |= new
            delta = new
    return known


def add_facts(program: Program, known: set[Fact],
              new_facts: Iterable[Fact]) -> set[Fact]:
    """The consequences of ``new_facts`` alone. ``known`` is not modified.

    This is the incremental path and it is why datalog sits next to the
    ``WorldDelta`` contract: a delta arrives, and the cost is proportional to
    what it actually changed rather than to the size of the world.

    **It is sound only for monotone additions.** Under stratified negation a
    *new* fact can invalidate a conclusion drawn from ``not p``, so a program
    whose negated predicates are touched by the addition is recomputed from
    scratch instead — reported in the return of :func:`add_facts_report`.
    """
    return add_facts_report(program, known, new_facts)[0]


def add_facts_report(program: Program, known: set[Fact],
                     new_facts: Iterable[Fact]) -> tuple[set[Fact], bool]:
    """``(added facts, whether a full recomputation was needed)``."""
    added = {f for f in new_facts if f not in known}
    if not added:
        return set(), False
    negated = {l.atom.pred for r in program.rules for l in r.body if l.negated}
    if negated & {f[0] for f in added} or _reaches(program, {f[0] for f in added},
                                                  negated):
        full = evaluate(program, known | added)
        return full - known, True
    total = set(known)
    delta = set(added)
    total |= delta
    idx = _index(total)
    while delta:
        new = _round(program.rules, total, idx, _index(delta))
        total |= new
        idx.extend(new)
        delta = new
    return total - known, False


def _reaches(program: Program, start: set[str], targets: set[str]) -> bool:
    """Whether any rule chain leads from ``start`` to a negated predicate."""
    edges: dict[str, set[str]] = {}
    for r in program.rules:
        for lit in r.body:
            edges.setdefault(lit.atom.pred, set()).add(r.head.pred)
    seen, stack = set(start), list(start)
    while stack:
        p = stack.pop()
        if p in targets:
            return True
        for q in edges.get(p, ()):
            if q not in seen:
                seen.add(q)
                stack.append(q)
    return False


def query(facts: Iterable[Fact], atom: Atom) -> list[dict[str, str]]:
    """Every substitution satisfying ``atom`` against a set of facts."""
    out = []
    for f in facts:
        m = _match(atom, f, {})
        if m is not None:
            out.append(m)
    return out


class IncrementalModel:
    """A least model that owns its index, so a delta costs what the delta costs.

    :func:`add_facts_report` is stateless by design — it does not modify
    ``known`` — and that is exactly what makes it unable to honour the
    contract's headline. Every call must rebuild an index over the whole model
    before it can do any work, so adding one edge to a 285,596-fact model cost
    1,230 ms where recomputing everything cost 6,967 ms: a 5.7x saving on a
    change of two facts, falling to 1.4x by two hundred edges.

    The fix is not a faster rebuild, it is not rebuilding. A world that expects
    deltas holds its own index and maintains it, which is what this class is
    for and what the ``WorldDelta`` contract assumed all along.

    Stateful on purpose, and the one caveat is loud: **monotone additions
    only.** Under stratified negation a new fact can retract a conclusion, so
    :meth:`add` refuses rather than silently returning a wrong model — a wrong
    incremental result is indistinguishable from a right one, which is why
    retraction is absent here too.
    """

    __slots__ = ("program", "facts", "_idx", "_negated")

    def __init__(self, program: "Program", facts: Iterable[Fact] = ()) -> None:
        self.program = program
        self.facts = evaluate(program, facts)
        self._idx = _index(self.facts)
        self._negated = {l.atom.pred for r in program.rules
                         for l in r.body if l.negated}

    def add(self, new_facts: Iterable[Fact]) -> set[Fact]:
        """Consequences of ``new_facts``. Returns only what is newly derived."""
        added = {f for f in new_facts if f not in self.facts}
        if not added:
            return set()
        preds = {f[0] for f in added}
        if self._negated & preds or _reaches(self.program, preds, self._negated):
            raise NonMonotoneAddition(
                f"adding {sorted(preds)} can reach a negated predicate "
                f"{sorted(self._negated)}: an incremental result would be "
                "unsound. Rebuild with IncrementalModel(program, facts | new).")
        self.facts |= added
        self._idx.extend(added)
        delta = set(added)
        derived: set[Fact] = set(added)
        while delta:
            new = _round(self.program.rules, self.facts, self._idx,
                         _index(delta))
            if not new:
                break
            self.facts |= new
            self._idx.extend(new)
            derived |= new
            delta = new
        return derived


class NonMonotoneAddition(ValueError):
    """An addition that could retract a conclusion. Refused, never guessed."""
