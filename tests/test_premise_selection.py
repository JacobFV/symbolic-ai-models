"""Guards for the premise-selection rung, ordered by what they would catch.

``scripts/premise_selection.py`` measures the middle row of the ladder whose two
ends ``derived_split.py`` published. The whole result rests on the selector being
*honest* — no oracle leaking in through the candidate set or the scoring — so the
tests here assert the properties whose failure would silently inflate it:

1. **A hidden node is never a candidate.** If the mask does not restrict the
   candidate set, the selector reads what a model cannot, and the rung stops
   being comparable to the published rows it sits between.
2. **The shrinkage suppresses a spuriously peaked candidate.** A once-seen label
   is perfectly peaked. If it outranks a kind label seen hundreds of times, the
   selector picks noise, the whole-graph row collapses, and the collapse would be
   read as "selection is hard" when it is "the score is broken".
3. **When the kind sibling is chosen, the deduction is the oracle's, exactly.**
   The claim is that only the *premise* varies across the three rungs. If the
   table the selector deduces from is not the one ``derivation_floor`` fits, the
   ladder compares three things at once.
"""

from __future__ import annotations

import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import premise_selection as P
from derived_split import _positions


class _G:
    """Smallest graph that has the shape ``_positions`` looks for."""

    def __init__(self, labels, types, parent):
        self.labels, self.types, self.parent = labels, types, parent

    def __len__(self):
        return len(self.labels)


def _obj_graph():
    #      0 root
    #      1 pred:obj  -> children 2 id, 3 value, 4 kind, 5 num
    return _G(labels=["r", "obj", "o0", "annex", "building", "7"],
              types=["root", "pred", "ident", "ident", "ident", "num"],
              parent=[-1, 0, 1, 1, 1, 1])


def test_a_hidden_node_is_never_a_candidate():
    g = _obj_graph()
    n = len(g)
    assert P._candidates(g, n, 3, "siblings", set()) == [2, 4, 5]
    assert P._candidates(g, n, 3, "siblings", {4}) == [2, 5]
    assert P._candidates(g, n, 3, "graph", {0, 4}) == [1, 2, 5]
    # the target itself is never a candidate, in either scope
    assert 3 not in P._candidates(g, n, 3, "graph", set())


def test_shrinkage_prefers_evidence_over_a_once_seen_peak():
    peaked_once = collections.Counter({"lace": 1})
    well_seen = collections.Counter({"annex": 68})
    assert P._score(peaked_once, 6) < P._score(well_seen, 6)
    # and an empty candidate is worth exactly the blind marginal, so choosing
    # badly costs the conditional and never the marginal
    assert P._score(None, 6) == 1.0 / 6


def test_a_diluted_kind_still_beats_an_uninformative_label():
    # what the whole-graph scope actually sees: the kind label co-occurs with its
    # own value and with the three other objects' values
    diluted = collections.Counter({"annex": 40, "lace": 8, "arm": 8, "bay": 8,
                                   "buffer": 8, "abdomen": 8})
    flat = collections.Counter({v: 13 for v in
                                ("annex", "lace", "arm", "bay", "buffer",
                                 "abdomen")})
    assert P._score(diluted, 6) > P._score(flat, 6)


def test_the_chosen_kind_deduces_what_the_oracle_deduces():
    """The sibling-scoped table, restricted to a kind key, is the oracle table."""
    g = _obj_graph()
    derived = [("o0", "building", "annex")]
    pos = _positions(g, derived)
    assert pos == [(3, 4)], pos
    ep = type("Ep", (), {"graph": g, "lesson_id": "x", "seed": 0})()
    table, values = P.fit_selector([(ep, pos)], "siblings")
    assert values == ["annex"]
    # derivation_floor's own fit, written out: rule[kind label][value label]
    oracle = collections.Counter({g.labels[3]: 1})
    assert table[g.labels[4]] == oracle
    assert table[g.labels[4]].most_common(1)[0][0] == "annex"


def test_the_object_id_is_a_candidate_and_is_not_the_kind():
    """The trap the shrinkage exists for: ``o0`` is always beside the answer."""
    g = _obj_graph()
    cands = P._candidates(g, len(g), 3, "siblings", set())
    assert 2 in cands and g.labels[2] == "o0"
    assert 4 in cands and g.labels[4] == "building"


class _Ep:
    def __init__(self, graph):
        self.graph = graph


def _two_object_episode(kind_a, val_a, kind_b, val_b):
    """One episode holding two `obj` predicates, so scopes can disagree.

    Nodes: 0 root, then (obj, id, value, kind) twice.
    """
    return _G(
        labels=["r", "obj", "o0", val_a, kind_a, "obj", "o1", val_b, kind_b],
        types=["root", "pred", "ident", "ident", "ident",
               "pred", "ident", "ident", "ident"],
        parent=[-1, 0, 1, 1, 1, 0, 5, 5, 5])


def test_the_fitting_scope_decides_whether_the_table_is_the_bijection():
    """Fitting over the whole episode dilutes a deterministic map to the marginal.

    This is the confound that made the published middle rung unreadable, and it
    is invisible in every artefact the run produces: the number comes out at
    0.286, looks like "premise selection is hard", and is really "the selector's
    table cannot express the relation it is choosing among". Measured on the
    real corpus the six kind labels came out at purity 0.29-0.37 where the
    bijection gives 1.000.

    So the two scopes are pinned apart here. `siblings` must recover the map
    exactly; `graph` must not, because it credits every label in the episode
    with every derived value in it. Neither is a bug -- what was a bug was
    varying both the fitting pool and the candidate set in one row and
    attributing the difference to the candidate set. See
    `notes/findings/2026-08-17-the-binding-story-was-right-for-the-wrong-reason.md`.
    """
    # two objects, two different kinds, each with its own derived value
    pairs = [(_Ep(_two_object_episode("ship", "bay", "shoe", "lace")),
              [(3, 4), (7, 8)])]

    sib, _ = P.fit_selector(pairs, "siblings")
    assert dict(sib["ship"]) == {"bay": 1}, sib["ship"]
    assert dict(sib["shoe"]) == {"lace": 1}, sib["shoe"]

    graph, _ = P.fit_selector(pairs, "graph")
    # `ship` now also carries the *other* object's value, which is the dilution
    assert set(graph["ship"]) == {"bay", "lace"}, graph["ship"]
    assert max(graph["ship"].values()) / sum(graph["ship"].values()) == 0.5


def test_a_fit_read_pair_is_named_for_both_scopes():
    """A row keyed by its read scope alone cannot say which table produced it.

    Both `graph` rungs read the whole episode; they differ only in what they
    were fitted over, and the published one was 0.286 while the isolated one is
    0.309. If the emitted keys collided, the second would silently overwrite the
    first and the correction would be invisible.
    """
    assert P.pair_name("graph", "graph") == "graph"
    assert P.pair_name("siblings", "siblings") == "siblings"
    assert P.pair_name("siblings", "graph") == "graph_fit_siblings"
    names = [P.pair_name(f, r) for f, r in P.PAIRS]
    assert len(names) == len(set(names)), names
