"""Guards on the `005` role source. Each one is a property nothing else checks.

``notes/lessons/2026-08-13-a-guard-is-the-only-thing-that-catches-a-silent-
property.md``: when a failure would be invisible, assert the property rather
than resolving to be careful. Four of these five would have caught a specific
way this family could look like it reasons while doing something else.
"""

from __future__ import annotations

import numpy as np
import pytest

from symbolic_ai_atomspace import (ANCESTOR_RULES_SOURCE, ROLE_QUERIES,
                                   TUPLE_QUERIES, AtomSpace, Rule, chain,
                                   occurrence, parse_atom, role_signatures,
                                   view_to_atomspace)
from symbolic_ai_core.data import curriculum as C
from symbolic_ai_core.graphview import GraphView


def _views(n_lessons: int = 24, seeds: int = 1) -> list[GraphView]:
    """Masked views over real curriculum graphs, built without the collator.

    The collator is exercised everywhere else; what is wanted here is control
    over exactly which nodes are hidden, so the leak and equivariance
    assertions can be per node rather than on average.
    """
    out: list[GraphView] = []
    lessons = C.lesson_ids()[:n_lessons]
    for ep in C.generate(lessons, n=seeds, seed0=0, on_error="skip"):
        g = ep.graph
        hidden = list(range(1, len(g), 5))
        out.append(GraphView(
            labels=[None if i in hidden else i for i in range(len(g))],
            types=[None if i in hidden else t for i, t in enumerate(g.types)],
            parent=list(g.parent), slot=list(g.slot), depth=list(g.depth),
            rel=np.zeros((0, 0)), hidden=hidden, tok=None))
    return out


@pytest.fixture(scope="module")
def views():
    got = _views()
    assert len(got) >= 20, "the view fixture stopped generating"
    return got


def test_no_role_query_reads_the_label_relation():
    """The property the whole `_pure` renaming column rests on.

    A role built from symbol identity is not equivariant, and a bits gain built
    on one is ``ensemble-001``'s 4.77 in a new notation — 0.467 down to 0.038
    under renaming. Asserted on the schedule itself, so a query added later
    cannot quietly break it.
    """
    for query in ROLE_QUERIES + TUPLE_QUERIES:
        assert not query.reads_labels(), f"{query.name} reads (label ...)"


def test_the_roles_are_bit_identical_when_every_label_is_permuted(views):
    """The empirical half of the test above, on real graphs.

    Reading the schedule proves nobody *wrote* ``(label ...)``. This proves no
    signature depends on a label by some other route — the source of truth is
    the number, not the source text.
    """
    for view in views[:20]:
        n = len(view)
        before = role_signatures(view_to_atomspace(view), n, ROLE_QUERIES)
        renamed = GraphView(
            labels=[None if l is None else (l + 977) % 4096 for l in view.labels],
            types=list(view.types), parent=list(view.parent),
            slot=list(view.slot), depth=list(view.depth), rel=view.rel,
            hidden=list(view.hidden), tok=None)
        after = role_signatures(view_to_atomspace(renamed), n, ROLE_QUERIES)
        assert before == after


def test_no_signature_of_a_hidden_node_could_have_come_from_its_own_answer(views):
    """A hidden node has no ``label`` atom, so nothing can read it.

    ``GraphView`` closes this structurally and the encoding of one must too. An
    IR that helpfully materialised the hidden label into a derived atom would
    make every number downstream meaningless, and would do it silently.
    """
    for view in views[:20]:
        space = view_to_atomspace(view)
        for i in view.hidden:
            assert not list(space.query(parse_atom(f"(label {occurrence(i)} $s)")))


def test_the_depth_the_hot_path_computes_is_the_one_the_rules_define(views):
    """The hot path walks parent pointers; the space says depth is a bounded
    transitive closure. ``roles.py`` claims the two agree; this is the claim.

    Without it the fast path is a comment, and a comment that drifted from the
    code would put a wrong coordinate into every role in the family.
    """
    rules = tuple(Rule.from_atom(parse_atom(s)) for s in ANCESTOR_RULES_SOURCE)
    for view in views[:12]:
        n = len(view)
        space = view_to_atomspace(view)
        chain(space, rules, max_rounds=n + 1)
        by_rule = {}
        for i in range(n):
            name = occurrence(i)
            by_rule[i] = sum(1 for _ in space.query(
                parse_atom(f"(anc $a {name})")))
        signatures = role_signatures(view_to_atomspace(view), n, ())
        for i in range(n):
            fast = [s for s in signatures[i] if s.startswith("dp:")]
            assert fast == [f"dp:{min(by_rule[i], 11)}"], (
                f"node {i}: hot path {fast} vs ancestor closure {by_rule[i]}")


def test_the_atomspace_schedule_says_strictly_more_than_the_four_tuple(views):
    """The claim that the IR is not a rename, as a number.

    If ``ROLE_QUERIES`` and ``TUPLE_QUERIES`` induced the same partition of
    nodes, the whole line would be a notation change and every downstream row a
    null by construction. Assert the partition is genuinely finer on real
    graphs, and that the extra signatures are the named ones.
    """
    finer = 0
    prefixes: set[str] = set()
    for view in views:
        n = len(view)
        space = view_to_atomspace(view)
        rich = role_signatures(space, n, ROLE_QUERIES)
        thin = role_signatures(space, n, TUPLE_QUERIES)
        prefixes |= {s[:2] for sigs in rich for s in sigs}
        if len({tuple(sorted(s)) for s in rich}) > \
                len({tuple(sorted(s)) for s in thin}):
            finer += 1
    assert finer > len(views) // 2, (
        f"the atomspace schedule refines the four-tuple on only {finer} of "
        f"{len(views)} graphs -- the IR is a rename")
    assert {"ct", "sb", "gp", "ps"} <= prefixes, (
        f"the downward, sibling and path groups never fired: {sorted(prefixes)}")


def test_the_signature_atom_seed_does_not_depend_on_hash_randomisation():
    """A role atom drawn from ``hash(str)`` would differ between the fitting
    process and the prediction process. ``blake2b`` is what stops that, and
    ``tests/test_models.py``'s cross-process determinism test is what would
    otherwise have caught it — expensively, and under another model's name."""
    import os
    import subprocess
    import sys

    code = ("from symbolic_ai_models.models.metta_005.model import _atom_seed;"
            "print(_atom_seed('ct:0/pred'), _atom_seed('sb:-2/num'))")
    out = []
    for seed in ("1", "999"):
        env = dict(os.environ, PYTHONHASHSEED=seed)
        out.append(subprocess.run([sys.executable, "-c", code], env=env,
                                  capture_output=True, text=True,
                                  check=True).stdout.strip())
    assert out[0] == out[1] and out[0]


def test_the_type_ladder_ends_on_the_floors_own_key():
    """``metta_type-005`` must degrade *to the floor's key*, not near it.

    ``node_context`` is written once in ``symbolic_ai_core.graphview`` precisely
    because four hand-copied near-misses of it is how a back-off stops being the
    baseline it is measured against. This head adds three rungs above that tuple
    and must still contain it.
    """
    from symbolic_ai_core.graphview import node_context
    from symbolic_ai_models.models.metta_005.model import DownwardTypes

    for view in _views(n_lessons=6):
        for node in range(min(len(view), 12)):
            ladder = DownwardTypes._type_ladder(view, node, ("char", "char"))
            assert ladder[3][1:] == node_context(view, node), (
                f"rung 3 is {ladder[3][1:]}, the floor keys on "
                f"{node_context(view, node)}")


def test_every_metta_row_is_registered_beside_its_predecessor():
    """New models go beside the old ones. A `005` row that displaced a `004`
    one would silently redefine every published number carrying its name."""
    from symbolic_ai_models.models import REGISTRY

    for name in ("vsa-002", "vsa_sum-004", "vsa_hks-004", "vsa_perm-002",
                 "vsa_perm_pure-002", "corefer-001"):
        assert name in REGISTRY, f"{name} vanished"
    metta = sorted(n for n in REGISTRY if n.startswith("metta"))
    assert len(metta) >= 12, metta
    for name in metta:
        assert name.endswith("-005"), name


def test_the_recorded_curve_picks_what_the_parent_fit_picks():
    """`metta_gated-005` re-derives the knob objective so it can record the whole
    curve. That duplication is only safe if the two agree.

    A curve reported for a knob that was actually chosen by different arithmetic
    would be worse than no curve: it would look like evidence and be a second
    opinion. So run the parent's fit and the recording fit on the same episodes
    and require the same chosen value, and require the curve to have a point per
    grid entry.
    """
    from symbolic_ai_core.data.tokenizer import SymbolTokenizer
    from symbolic_ai_models.models import build
    from symbolic_ai_models.models.base import ModelConfig
    from symbolic_ai_models.models.vsa_spec_004.model import RoleEmbedding

    episodes = list(C.generate(C.lesson_ids()[:6], n=4, seed0=0,
                               on_error="skip"))
    tok = SymbolTokenizer.build([e.text for e in episodes], max_vocab=2048)
    cfg = ModelConfig(vocab_size=len(tok), max_nodes=64,
                      extra={"vsa_dim": 512})

    recording = build("metta_gated-005", cfg)
    recording.fit_on(episodes, tok)
    assert len(recording.knob_curve) == len(type(recording).knob_grid)
    assert recording._knob == max(recording.knob_curve, key=lambda kv: kv[1])[0]

    parent = build("metta_gated-005", cfg)
    parent._fit_scalars = RoleEmbedding._fit_scalars.__get__(parent)
    parent.fit_on(episodes, tok)
    assert parent._knob == recording._knob, (
        f"the recorded curve chose {recording._knob} and the parent fit chose "
        f"{parent._knob} -- the re-derived objective has drifted")


def test_an_atomspace_query_expresses_ilps_clause_that_claws_cannot(views):
    """The concrete expressiveness claim, as a firing count on real graphs.

    ``CLAWS`` is twelve routes somebody wrote down; it has ``sibling0`` and
    ``prev_sibling`` and no way to say *which* sibling, so
    ``omegaclaw_reach-001`` had to add a branch to reach ``ilp``'s best
    discovered clause — a typed, slot-selected sibling. Here it is one query,
    and this test says it actually selects rather than merely parsing: the
    typed, offset-selected form must fire on strictly fewer nodes than the
    untyped one, or "typed" is not doing anything.
    """
    typed = untyped = 0
    for view in views:
        space = view_to_atomspace(view)
        untyped += sum(1 for _ in space.query(
            parse_atom("(child $p $k $q)"), parse_atom("(child $p $j $s)")))
        typed += sum(1 for _ in space.query(
            parse_atom("(child $p $k $q)"), parse_atom("(child $p $j $s)"),
            parse_atom("(: $s pred)")))
    assert 0 < typed < untyped, (typed, untyped)
