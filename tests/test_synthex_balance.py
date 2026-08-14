"""The 2x2 that separates class *balance* from class *provenance*.

`synthex_class-002` loses to `synthex_random-002` while differing from it in two
things at once: the semantics of the partition and its entropy. These tests pin
the properties that make the four-cell comparison mean what it says — matched
cardinality, matched entropy along each row, provenance along each column, and a
rebalancing that never cuts across a curated class boundary. Break any of them
and the square stops factoring.
"""

from __future__ import annotations

import collections
import math

import pytest

from symbolic_ai_core.data.curriculum import generate
from symbolic_ai_models.models import ModelConfig, build
from symbolic_ai_models.models.synthex_003.model import (
    assignment_stats, label_occurrences, rebalance, rebalance_weighted,
    skew_matched_random, uniform_random)

LESSONS = ["unification", "symbol_grounding", "center_embedding"]

ARMS = ("synthex_class-002", "synthex_random-002", "synthex_balanced-003",
        "synthex_skewrand-003", "synthex_random-003", "synthex_occbal-003")

PURE = ("synthex_class_pure-003", "synthex_balanced_pure-003",
        "synthex_skewrand_pure-003", "synthex_random_pure-003",
        "synthex_occbal_pure-003")


@pytest.fixture(scope="module")
def episodes():
    from symbolic_ai_models.train import TrainConfig, build_tokenizer
    train = list(generate(LESSONS, n=25))
    return train, build_tokenizer(TrainConfig(vocab_size=1600), train)


@pytest.fixture(scope="module")
def fitted(episodes):
    train, tok = episodes
    cfg = ModelConfig(vocab_size=len(tok), max_len=160, max_nodes=128)
    out = {}
    for name in ARMS:
        model = build(name, cfg)
        model.fit_on(train, tok)
        out[name] = model
    return out


@pytest.fixture(scope="module")
def curated(fitted):
    return dict(fitted["synthex_class-002"].symbol_class)


# ---- the square factors ---------------------------------------------------
def test_every_arm_partitions_the_same_symbols_into_the_same_count(fitted):
    """Cardinality is the confound that already inverted this result once.

    A first version of `synthex_random-002` hashed into all 17 node types when
    only 6 ever land on a labelled node, and the row read "random beats curated"
    when it meant "more classes beat fewer". Every cell of the 2x2 inherits the
    curated count for the same reason.
    """
    counts = {n: len(set(m.symbol_class.values())) for n, m in fitted.items()}
    assert len(set(counts.values())) == 1, f"cardinality drifted: {counts}"
    symbols = {n: frozenset(m.symbol_class) for n, m in fitted.items()}
    assert len(set(symbols.values())) == 1, "the arms partition different symbols"


def test_the_balanced_arm_matches_the_control_entropy(curated):
    """"Matched balance" has to be a number, not a claim."""
    k = len(set(curated.values()))
    balanced = assignment_stats(rebalance(curated, k), curated)
    control = assignment_stats(uniform_random(curated, k), curated)
    assert abs(balanced["entropy"] - control["entropy"]) < 0.05, (
        f"balance not matched: {balanced['entropy']:.4f} vs "
        f"{control['entropy']:.4f}")
    assert balanced["entropy"] > math.log2(k) - 0.1


def test_the_skewed_control_matches_the_curated_profile_exactly(curated):
    """Same size multiset, so the entropies are equal by construction."""
    skew = skew_matched_random(curated)
    assert (sorted(collections.Counter(skew.values()).values())
            == sorted(collections.Counter(curated.values()).values()))
    assert abs(assignment_stats(skew, curated)["entropy"]
               - assignment_stats(curated, curated)["entropy"]) < 1e-9


def test_provenance_separates_the_columns(curated):
    """`I(assignment; curated type)` is the provenance axis, in bits.

    High for the curated layer and for the rebalancing of it; near zero for both
    partitions drawn independently of the ontology.

    Asserted as a *ratio to* `H(curated)` and not as an absolute threshold.
    Plug-in mutual information is biased upward by roughly `(a-1)(b-1)/(2N ln2)`
    bits, so an independent partition scores ~0.003 on the full curriculum's
    5,258 symbols and ~0.25 on this three-lesson fixture's few hundred. A
    constant measured on one slice and pinned into a test run on another is the
    mistake this repo keeps paying for.
    """
    k = len(set(curated.values()))
    mi = {"curated": assignment_stats(curated, curated)["mutual"],
          "balanced": assignment_stats(rebalance(curated, k), curated)["mutual"],
          "skewrand": assignment_stats(skew_matched_random(curated),
                                       curated)["mutual"],
          "random": assignment_stats(uniform_random(curated, k),
                                     curated)["mutual"]}
    assert max(mi["skewrand"], mi["random"]) < 0.25 * mi["curated"], mi
    assert mi["balanced"] > 0.4 * mi["curated"], mi
    assert mi["balanced"] < mi["curated"] + 1e-9, (
        "a rebalancing cannot carry more of the ontology than the ontology")


def test_the_two_balanced_arms_bracket_rather_than_match(curated, episodes):
    """Neither balance measure can be matched without unmatching the other.

    `synthex_balanced-003` equalises symbol *types* — the measure the hash
    control is uniform in — and `synthex_occbal-003` equalises label
    *occurrences*, which is what the conditioning context actually sees. On this
    ontology the two cannot be equalised at once, so the pair brackets the
    balance axis. Each arm must beat the other on the measure it optimises, or
    the bracket is not a bracket.
    """
    import collections as c

    train, tok = episodes
    k = len(set(curated.values()))
    occ = label_occurrences(train, tok)
    by_type = rebalance(curated, k)
    by_occ = rebalance_weighted(curated, k, occ)

    def h_occ(a):
        per = c.Counter()
        for s, cls in a.items():
            per[cls] += occ.get(s, 0)
        total = sum(per.values())
        return -sum((v / total) * math.log2(v / total) for v in per.values() if v)

    assert (assignment_stats(by_type, curated)["entropy"]
            > assignment_stats(by_occ, curated)["entropy"])
    assert h_occ(by_occ) > h_occ(by_type)


def test_a_rebalanced_bin_never_cuts_across_a_curated_boundary(curated):
    """The property that makes this "provenance held fixed" rather than "a new
    partition that happens to be balanced".

    Splitting happens inside a curated class and merging between whole ones, so
    every bin is a subset of one class or a union of several — never a partial
    slice of two.
    """
    k = len(set(curated.values()))
    balanced = rebalance(curated, k)
    members = collections.defaultdict(set)
    for symbol, b in balanced.items():
        members[b].add(curated[symbol])
    whole = collections.defaultdict(set)
    for symbol, c in curated.items():
        whole[c].add(balanced[symbol])
    for bin_, classes in members.items():
        if len(classes) == 1:
            continue                       # a split: subset of one class
        for c in classes:                  # a merge: each class arrived whole
            assert whole[c] == {bin_}, (
                f"curated class {c} was split across bins {whole[c]} while also "
                f"sharing bin {bin_}")


# ---- reproducibility ------------------------------------------------------
def test_the_salted_control_reproduces_the_published_row(curated):
    """`synthex_random-003` at the default salt must be `synthex_random-002`.

    Registered beside rather than in place of it, and this is what makes the
    two rows comparable: the salt exists only so the arbitrary draw can be
    re-drawn and a noise band measured.
    """
    import hashlib

    k = len(set(curated.values()))
    published = {s: int(hashlib.sha256(str(s).encode()).hexdigest(), 16) % k
                 for s in curated}
    assert uniform_random(curated, k, "") == published


def test_the_partitions_are_deterministic_across_processes(fitted, curated):
    """sha256 rather than `hash()`, which is salted per interpreter and would
    make every row irreproducible while looking fine in one session."""
    k = len(set(curated.values()))
    assert fitted["synthex_balanced-003"].symbol_class == rebalance(curated, k)
    assert fitted["synthex_skewrand-003"].symbol_class == skew_matched_random(curated)
    assert fitted["synthex_random-003"].symbol_class == uniform_random(curated, k)


def test_a_salt_redraws_the_partition_but_not_its_balance(curated):
    """The noise band has to move the membership and hold the statistic."""
    k = len(set(curated.values()))
    for fn, args in ((rebalance, (curated, k)), (skew_matched_random, (curated,)),
                     (uniform_random, (curated, k))):
        base, redrawn = fn(*args, ""), fn(*args, "s1")
        assert base != redrawn, f"{fn.__name__} ignored its salt"
        assert abs(assignment_stats(base, curated)["entropy"]
                   - assignment_stats(redrawn, curated)["entropy"]) < 0.05


# ---- the arms differ in one method, and the floor is separable ------------
def test_the_arms_differ_only_in_the_class_assignment():
    from symbolic_ai_models.models import REGISTRY
    from symbolic_ai_models.models.synthex_002.model import SynthexClassModel
    shared = ("_contexts", "_label_table", "node_votes", "learn", "_fit_gate",
              "_class_of", "_type_vote")
    for name in ARMS + PURE:
        cls = REGISTRY[name]
        for method in shared:
            assert getattr(cls, method) is getattr(SynthexClassModel, method), (
                f"{name} overrides {method}; the gap would stop being the seed")
    seen = {REGISTRY[n]._assign_classes for n in ARMS}
    assert len(seen) == len(ARMS), "two arms share a method, so a cell is missing"


def test_the_pure_rows_drop_the_shared_memorising_floor():
    """`structural_fallback` is identical across the four cells, so it can only
    compress their differences. The `_pure` rows are the comparison with the
    shared memoriser removed rather than merely equalised."""
    from symbolic_ai_models.models import REGISTRY
    for name in PURE:
        assert REGISTRY[name].structural_fallback is False
    for name in ARMS:
        assert REGISTRY[name].structural_fallback is True
