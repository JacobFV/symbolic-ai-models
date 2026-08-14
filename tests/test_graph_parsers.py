"""What ``symbolic_ai_parsers`` claims, tested as claims rather than as coverage.

Every assertion here is a *relation* — perfect on identity, invariant under
renumbering, at-or-above the floor — and never a measured constant. A number
measured on the three-lesson fixture below would be a number measured on three
lessons, and this repo has six recorded instances of a small slice producing a
confident wrong reading. The fixture exists to exercise the code; the sweep
measures.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest

from symbolic_ai_core.data.curriculum import generate
from symbolic_ai_core.data.graph import Graph
from symbolic_ai_parsers import (METRICS, REGISTRY, build, fit_floor, get,
                                 parser_names, score_graph)
from symbolic_ai_parsers.align import align, canonical, children_of, content_align
from symbolic_ai_parsers.evaluate import EVAL_SEED0, LANGUAGES, evaluate_parser
from symbolic_ai_parsers.lexicon import Lexicon
from symbolic_ai_parsers.scoring import brackets, label_bag

LESSONS = ["analogy", "adversarial_argumentation", "algorithm_analysis"]


@pytest.fixture(scope="module")
def train():
    return list(generate(LESSONS, n=4, seed0=0, max_nodes=128))


@pytest.fixture(scope="module")
def evals():
    return {lang: list(generate(LESSONS, n=2, seed0=EVAL_SEED0, language=lang,
                                max_nodes=128))
            for lang in LANGUAGES}


@pytest.fixture(scope="module")
def fitted(train):
    out = {}
    for name in parser_names():
        p = build(name)
        p.fit(train)
        out[name] = p
    return out


# ---- the registry, and the bug it was copied over to avoid ---------------

def test_a_bare_name_resolves_over_numbers_not_over_words():
    """``template-seeded`` is a knob. It must never be what ``template`` means.

    This is the ``ptrgen-argmax`` failure from ``models/registry.py``, where a
    control became what the bare name resolved to because a string sort puts
    every word above every number. It is repeated here because the same naming
    convention is in use and the same mistake is therefore available.
    """
    numbered = sorted(n for n in REGISTRY
                      if n.startswith("template-") and n.split("-")[-1].isdigit())
    assert get("template").name == numbered[-1]
    assert get("template").name not in ("template-seeded", "template-lex")
    assert get("template-seeded").name == "template-seeded"
    assert get("template-001").name == "template-001"


def test_an_unnumbered_family_refuses_to_resolve():
    from symbolic_ai_parsers.base import REGISTRY as R, Parser

    R["ghost-alpha"] = type("Ghost", (Parser,), {"name": "ghost-alpha"})
    try:
        with pytest.raises(KeyError, match="no numbered version"):
            get("ghost")
    finally:
        del R["ghost-alpha"]


def test_the_shape_features_do_not_count_tokens(evals):
    """The correction ``template-002`` exists for, asserted as a property.

    ``layout_features`` moves wholesale between an English prompt and its
    Chinese rendering because it counts and measures tokens, and Chinese
    retokenises the same document into far more, far shorter pieces.
    ``shape_features`` reads punctuation and lines, so it should move far less.
    Relative distance, not an absolute one, so this is a claim about the two
    feature sets and not a number measured on this fixture.
    """
    import numpy as np

    from symbolic_ai_parsers.features import layout_features, shape_features

    def drift(f) -> float:
        num = den = 0.0
        for a, b in zip(evals["english"], evals["chinese"]):
            va, vb = f(a.prompt), f(b.prompt)
            num += float(np.abs(va - vb).sum())
            den += float(np.abs(va).sum()) + 1e-9
        return num / den

    assert drift(shape_features) < drift(layout_features)


def test_cjk_punctuation_is_folded_onto_its_ascii_role():
    """NFKC folds ``：`` because it is a compatibility form and leaves ``、``
    alone because it is not — and ``、`` is the Chinese list separator."""
    from symbolic_ai_parsers.features import fold, normalise

    assert "、" in normalise("alice、bob")
    assert fold("alice、bob和dave") .count(",") == 1
    assert fold("图如下：").endswith(":")


def test_both_seeding_arms_stay_registered():
    """The knob is only honest if its control is in the same sweep."""
    assert {"template-001", "template-lex", "template-seeded"} <= set(REGISTRY)
    assert REGISTRY["template-001"].seeded is False
    assert REGISTRY["template-seeded"].seeded is True


# ---- scoring ------------------------------------------------------------

def test_a_graph_scores_perfectly_against_itself(train):
    for ep in train[:6]:
        s = score_graph(ep.graph, ep.graph)
        for m in METRICS:
            assert getattr(s, m) == pytest.approx(1.0), (m, ep.lesson_id)


def test_an_unrelated_graph_does_not_score_perfectly(train):
    a, b = train[0].graph, train[len(train) // 2].graph
    assert score_graph(a, b).exact == 0.0


def _renumber(g: Graph) -> Graph:
    """The same tree, emitted depth-first instead of breadth-first."""
    kids = children_of(g)
    out = Graph()

    def walk(old: int, parent: int, slot: int) -> None:
        new = out.add(g.labels[old], g.types[old], parent, slot)
        for k, c in enumerate(kids[old]):
            walk(c, new, k)

    walk(0, -1, 0)
    return out


def test_every_score_ignores_node_numbering(train):
    """Otherwise ``exact`` is a statement about traversal order, not structure."""
    for ep in train[:4]:
        shuffled = _renumber(ep.graph)
        s = score_graph(shuffled, ep.graph)
        for m in METRICS:
            assert getattr(s, m) == pytest.approx(1.0), (m, ep.lesson_id)


def test_the_alignment_free_scores_survive_renumbering(train):
    """``bracket_f1`` and ``label_f1`` are supposed to need no alignment at all."""
    for ep in train[:4]:
        assert brackets(_renumber(ep.graph)) == brackets(ep.graph)
        assert label_bag(_renumber(ep.graph)) == label_bag(ep.graph)


def test_the_tree_alignment_cannot_be_used_to_score_attachment(train):
    """Pinned, because scoring was written this way first and it read well.

    Under the top-down mapping a pair is only ever added once its parents are
    paired, so attachment is right on every aligned node and a UAS computed over
    it measures how many nodes were alignable. If this ever stops holding, the
    docstring in ``align.content_align`` is wrong and should be rewritten rather
    than the test deleted.
    """
    a, b = train[0].graph, train[1].graph
    m = align(a, b)
    assert m, "the fixture must actually align something for this to mean anything"
    for i, j in m.items():
        pi, pj = a.parent[i], b.parent[j]
        assert (pi < 0 and pj < 0) or m.get(pi) == pj


def test_the_content_alignment_can_be_used_to_score_attachment(train):
    """A graph with the right nodes in the wrong places must lose UAS."""
    g = train[0].graph
    flat = Graph()
    root = flat.add(g.labels[0], g.types[0], -1, 0)
    for i in range(1, len(g)):                  # every node hung off the root
        flat.add(g.labels[i], g.types[i], root, 0)
    s = score_graph(flat, g)
    assert s.label_f1 == pytest.approx(1.0)     # same labels
    assert s.uas < 0.99                         # different attachments
    assert content_align(flat, g)


def test_canonical_is_idempotent(train):
    for ep in train[:4]:
        c = canonical(ep.graph)
        assert canonical(c).to_dict() == c.to_dict()


# ---- floors -------------------------------------------------------------

def test_the_floor_is_fitted_on_train_and_is_a_real_bar(train, evals):
    floor = fit_floor(train, n_candidates=8, n_targets=8)
    scores = floor.evaluate(evals["english"])
    assert set(scores) == set(METRICS)
    for m in METRICS:
        assert 0.0 <= scores[m] <= 1.0
    # A text-blind constant beating nothing at all would make the floor
    # decorative. On any templated corpus it does not.
    assert scores["bracket_f1"] > 0.0 or scores["label_f1"] > 0.0


def test_the_floor_does_not_move_with_the_language(train, evals):
    """It cannot: the graphs are byte-identical across languages, and the floor
    never reads the text. If this fails, one of those two facts changed."""
    floor = fit_floor(train, n_candidates=8, n_targets=8)
    base = floor.evaluate(evals["english"])
    for lang in LANGUAGES[1:]:
        assert floor.evaluate(evals[lang]) == pytest.approx(base, nan_ok=True)


def test_the_gold_graph_is_the_same_object_in_every_language(evals):
    """The premise of the whole cross-language evaluation, asserted here too so
    that this package fails loudly rather than reporting a drop that is really a
    change of target."""
    for lang in LANGUAGES[1:]:
        for a, b in zip(evals["english"], evals[lang]):
            assert a.instance_id == b.instance_id
            assert a.graph.to_dict() == b.graph.to_dict()
            assert a.prompt != b.prompt


# ---- the parsers --------------------------------------------------------

def test_every_parser_returns_a_graph_in_every_language(fitted, evals):
    for name, parser in fitted.items():
        for lang in LANGUAGES:
            for ep in evals[lang][:3]:
                g = parser.parse(ep.prompt)
                assert isinstance(g, Graph)
                assert len(g.labels) == len(g.types) == len(g.parent) == len(g.slot)
                if len(g):
                    assert g.parent[0] < 0


def test_every_parser_survives_degenerate_input(fitted):
    for name, parser in fitted.items():
        for text in ["", "\n\n", "?", "   ", "a" * 4000, "沒有\n  - 一"]:
            assert isinstance(parser.parse(text), Graph), name


def test_no_parser_scores_below_zero_or_above_one(fitted, evals):
    for name, parser in fitted.items():
        r = evaluate_parser(parser, evals["english"], {m: 0.0 for m in METRICS},
                            language="english")
        for m in METRICS:
            assert 0.0 <= r.scores[m] <= 1.0, (name, m)


def test_parsing_is_stable_across_processes(tmp_path):
    """Sets and frozensets iterate in a hash-randomised order, which is fixed
    within a process and differs between them. This repo has already had a
    number flap for that reason, so the parses are digested under two seeds."""
    script = (
        "import json,hashlib;"
        "from symbolic_ai_core.data.curriculum import generate;"
        "from symbolic_ai_parsers import build,parser_names;"
        f"tr=list(generate({LESSONS!r},n=3,seed0=0,max_nodes=128));"
        f"ev=list(generate({LESSONS!r},n=2,seed0={EVAL_SEED0},max_nodes=128));"
        "out={};"
        "\nfor n in parser_names():\n"
        "    p=build(n); p.fit(tr)\n"
        "    out[n]=hashlib.sha256(json.dumps([p.parse(e.prompt).to_dict() "
        "for e in ev],sort_keys=True).encode()).hexdigest()\n"
        "print(json.dumps(out))"
    )
    digests = []
    for seed in ("1", "999"):
        env = {"PYTHONHASHSEED": seed, "PATH": "/usr/bin:/bin"}
        import os
        env = {**os.environ, "PYTHONHASHSEED": seed}
        out = subprocess.run([sys.executable, "-c", script], capture_output=True,
                             text=True, env=env, check=True)
        digests.append(json.loads(out.stdout.strip().splitlines()[-1]))
    assert digests[0] == digests[1]


# ---- the package layout -------------------------------------------------

def test_every_registered_parser_has_a_package_named_after_it():
    """The ``models/`` convention, enforced rather than described.

    A directory named for the row it produces cannot drift away from the
    registry — which is the failure the version suffix was added to prevent in
    the first place. Skeleton packages (``template``, ``classical``,
    ``polyglot``) register nothing and are allowed to exist without a row.
    """
    import symbolic_ai_parsers.parsers as pkg

    have = {p.name for p in pathlib.Path(pkg.__file__).parent.iterdir()
            if p.is_dir() and not p.name.startswith("_")}
    want = {n.replace("-", "_") for n in parser_names()}
    assert want <= have, f"registered but no package: {sorted(want - have)}"
    extra = have - want
    assert extra <= {"template", "classical", "polyglot"}, (
        f"package with no row: {sorted(extra)}")


# ---- the treebank and the induced grammar -------------------------------

def test_the_treebank_finds_spans_the_generator_never_recorded(train):
    from symbolic_ai_parsers.treebank import Treebank

    tb = Treebank.build(train)
    assert tb.n_clause_nodes > 0
    assert tb.coverage > 0.0
    for s in tb.samples:
        assert s.tokens and s.head
        for i, slot in s.arg_slots:
            assert 0 <= i < len(s.tokens)
            assert slot >= 0
        assert len(s.categories()) == len(s.tokens)


def test_every_induced_rule_can_be_found_again_by_the_chart(train):
    """The trie is the grammar. If a rule cannot be matched back out of it, the
    automaton and the rule list have drifted and every classical row is wrong."""
    from symbolic_ai_parsers.grammar import Grammar
    from symbolic_ai_parsers.treebank import Treebank

    g = Grammar.induce(Treebank.build(train))
    assert g.rules
    for rule in g.rules[:60]:
        surface = ["zzq_nonce" if c == "ARG" else c for c in rule.rhs]
        found = {r for end, r, _ in g.matches(surface, 0) if end == len(surface)}
        assert rule in found, rule


def test_surface_order_and_graph_slot_are_kept_apart():
    """Turkish moves the predicate to the end and leaves the arguments' roles
    alone. A grammar that folded position into slot would learn that as a
    different predicate; this asserts it learns it as a different word order."""
    from symbolic_ai_parsers.grammar import Grammar
    from symbolic_ai_parsers.treebank import Treebank

    def slots_and_shapes(language):
        eps = list(generate(["analogy"], n=6, seed0=0, language=language,
                            max_nodes=128))
        g = Grammar.induce(Treebank.build(eps))
        return {r.head: (r.arg_slots, r.rhs) for r in g.rules}

    en, tr = slots_and_shapes("english"), slots_and_shapes("turkish")
    shared = set(en) & set(tr)
    assert shared, "the two renderings share no predicate head at all"
    assert any(en[h][0] == tr[h][0] and en[h][1] != tr[h][1] for h in shared), (
        "no head kept its slots while changing its surface order")


def test_the_classical_parsers_compose_rather_than_retrieve(train, evals):
    """The claim that separates them from every other parser here.

    A symbol that occurs in no training graph is put into the eval text; a
    parser that builds its answer will emit it as a node label, and one that
    copies a remembered graph cannot.
    """
    import re

    from symbolic_ai_parsers.features import words_of

    ep = evals["english"][0]
    # An argument, not a field name: something the generator copied verbatim
    # into the prose, which is what a parser has to lift back out of it.
    surface = set(words_of(ep.prompt))
    victim = next(l for l, t in zip(ep.graph.labels, ep.graph.types)
                  if t == "ident" and l in surface and len(l) > 2)
    nonce = "qxzvv"
    text = re.sub(rf"\b{re.escape(victim)}\b", nonce, ep.prompt)

    built = retrieved = 0
    for name in ("cky-001", "lr-001", "shiftreduce-001"):
        p = build(name)
        p.fit(train)
        built += nonce in p.parse(text).labels
    for name in ("retrieve-001", "template-002"):
        p = build(name)
        p.fit(train)
        retrieved += nonce in p.parse(text).labels
    assert built > 0, "no classical parser emitted a symbol it had never seen"


# ---- the seeding knob ---------------------------------------------------

def test_the_seeded_lexicon_sees_more_episodes_than_the_training_one(train):
    """The knob has to actually be a knob. What it *buys* is measured by the
    sweep, not asserted here — but "the seeded arm rests on more data" is a
    fact about the construction and is worth pinning."""
    own = Lexicon.from_episodes(train)
    seeded = Lexicon.from_curriculum(n=32, lessons=LESSONS, max_nodes=128)
    assert seeded.source.startswith("curriculum:")
    for lid in LESSONS:
        assert seeded.n_per_lesson[lid] > own.n_per_lesson[lid]


def test_a_seeded_lexicon_never_reaches_the_evaluation_seeds():
    """Seeds >= 1,000,000 are eval only, and a dictionary built from them would
    be undetectable in the score. Asserted on the generator call itself."""
    import symbolic_ai_parsers.lexicon as lexmod

    seen: list[int] = []
    real = lexmod.generate

    def spy(*a, **kw):
        seen.append(kw.get("seed0", 0))
        return real(*a, **kw)

    lexmod.generate = spy
    try:
        lexmod._CURRICULUM_CACHE.clear()
        Lexicon.from_curriculum(n=2, lessons=LESSONS[:1], max_nodes=64)
    finally:
        lexmod.generate = real
        lexmod._CURRICULUM_CACHE.clear()
    assert seen and all(s + 2 < EVAL_SEED0 for s in seen)
