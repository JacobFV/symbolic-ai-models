"""The OmegaClaw family, against the claims its base class makes.

``tests/test_models.py`` already holds every registered model to the shared
contract, and the three OmegaClaw models are covered there the moment they are
registered. What is left is the set of claims this *family* makes and no other
model does — that its members differ in exactly one method, that its claws point
rather than remember, and that the machinery the base class took over from the
subclasses actually runs for all of them.

They are worth testing because the whole argument for the abstraction is that it
makes a comparison fair. An untested ABC that quietly let two subclasses see
different evidence would produce a table that looks like a result and is an
artefact.
"""

from __future__ import annotations

from typing import Hashable

import numpy as np
import pytest
import torch

from symbolic_ai_core.data.batch import collate_graph
from symbolic_ai_core.data.curriculum import generate
from symbolic_ai_models.models import ModelConfig, build
from symbolic_ai_models.models.omegaclaw import CLAWS, Claim, OmegaClaw, Scan
from symbolic_ai_models.models.omegaclaw_ctx_001 import OmegaClawContext
from symbolic_ai_models.models.omegaclaw_flat_001 import OmegaClawFlat
from symbolic_ai_models.models.omegaclaw_rank_001 import OmegaClawRank
from symbolic_ai_models.train import TrainConfig, build_tokenizer

LESSONS = ["unification", "symbol_grounding", "center_embedding"]
FAMILY = ["omegaclaw_flat", "omegaclaw_ctx", "omegaclaw_rank"]


@pytest.fixture(scope="module")
def fixtures():
    # Twenty per lesson rather than a handful: the held-out fifth has to
    # contain enough scored nodes for the shared confidence map to fit at all,
    # and a fixture too small to fit it would make the calibration tests below
    # pass or fail for reasons that have nothing to do with the family.
    episodes = list(generate(LESSONS, n=20))
    tok = build_tokenizer(TrainConfig(vocab_size=600), episodes)
    return episodes, tok


@pytest.fixture(scope="module")
def cfg(fixtures):
    _, tok = fixtures
    return ModelConfig(vocab_size=len(tok), d_model=32, n_layers=2, n_heads=4,
                       d_ff=64, dropout=0.0, max_nodes=128)


@pytest.fixture(scope="module")
def fitted(fixtures, cfg):
    episodes, tok = fixtures
    out = {}
    for name in FAMILY:
        model = build(name, cfg)
        model.fit_on(episodes, tok)
        out[name] = model.eval()
    return out


def _views(model, fixtures):
    episodes, tok = fixtures
    return list(model.training_views(episodes, tok, repeats=1,
                                     max_nodes=model.cfg.max_nodes))


# ---------------------------------------------------------------------------
# what makes the comparison fair
# ---------------------------------------------------------------------------
def test_the_family_differs_only_in_control():
    """The point of the ABC, asserted rather than assumed.

    If a subclass quietly overrode ``claws`` or ``perceive``, the table would be
    comparing models that were allowed to look at different things while
    appearing to compare control policies. ``omegaclaw_rank`` overrides
    ``commit`` and that is exactly the contrast it exists to draw, so it is
    named here rather than forbidden.
    """
    for cls in (OmegaClawFlat, OmegaClawContext, OmegaClawRank):
        assert cls.claws is OmegaClaw.claws, f"{cls.__name__} changed its reach"
        assert cls.perceive is OmegaClaw.perceive, f"{cls.__name__} changed its context"
        assert cls.weigh is not OmegaClaw.weigh
    assert OmegaClawFlat.commit is OmegaClaw.commit
    assert OmegaClawContext.commit is OmegaClaw.commit
    assert OmegaClawRank.commit is not OmegaClaw.commit


def test_rank_and_ctx_weigh_identically(fitted, fixtures):
    """The ``ctx -> rank`` contrast is about aggregation and nothing else.

    Their ``weigh`` is one duplicated line, kept duplicated so each model reads
    as a whole on its own. Duplication drifts, so it is pinned here: the two
    must return the same weight for the same claim, on real fitted evidence.
    """
    ctx_model, rank_model = fitted["omegaclaw_ctx"], fitted["omegaclaw_rank"]
    rank_model.claw_evidence = ctx_model.claw_evidence
    rank_model.claw_totals = ctx_model.claw_totals
    checked = 0
    for view, targets in _views(ctx_model, fixtures)[:8]:
        scan = Scan(view)
        for node in targets:
            key = ctx_model.perceive(view, node)
            for name, claw in CLAWS.items():
                claim = claw(scan, node)
                if claim is None:
                    continue
                assert ctx_model.weigh(name, key, claim) == \
                    rank_model.weigh(name, key, claim)
                checked += 1
    assert checked > 50, "the test did not actually exercise any claws"


def test_every_subclass_saw_the_same_evidence(fitted):
    """Three models, one fitting procedure: the tables must be identical.

    The base class gathers evidence before any control policy is consulted, so
    two members can only differ downstream of it. Were that not true, a
    difference in score could be a difference in what was learned rather than in
    how it was used, and the family's headline contrast would mean nothing.
    """
    tables = [(m.claw_evidence, m.claw_totals) for m in fitted.values()]
    for evidence, totals in tables[1:]:
        assert evidence == tables[0][0]
        assert totals == tables[0][1]


# ---------------------------------------------------------------------------
# what the claws are allowed to do
# ---------------------------------------------------------------------------
def test_every_claw_points_at_a_visible_node(fitted, fixtures):
    """Pointer-valued by construction, checked rather than promised.

    A claw returning a symbol that is not in the episode in front of it would be
    remembering, and the family's equivariance claim would be false. The claim
    it returns must name a node, that node must not be the hidden one, and the
    symbol must be that node's label.
    """
    model = fitted["omegaclaw_ctx"]
    fired = 0
    for view, targets in _views(model, fixtures)[:8]:
        scan = Scan(view)
        for node in targets:
            for name, claw in CLAWS.items():
                claim = claw(scan, node)
                if claim is None:
                    continue
                fired += 1
                assert 0 <= claim.source < len(view), f"{name} pointed nowhere"
                assert claim.source != node, f"{name} pointed at the hidden node"
                assert view.labels[claim.source] == claim.symbol, \
                    f"{name} invented a symbol"
    assert fired > 50


def test_nothing_fires_when_the_whole_graph_is_hidden(fitted, fixtures):
    """With every label gone there is nowhere to point, and the model says so.

    The strongest available check that no claw reads through the mask: masking
    everything removes every source of every claim, so a claw that still fires
    is reading something it was not given.
    """
    episodes, tok = fixtures
    model = fitted["omegaclaw_ctx"]
    batch = collate_graph(episodes[:2], tok, mask_all=True)
    view = model._view(batch, 0)
    scan = Scan(view)
    for node in view.hidden:
        for name, claw in CLAWS.items():
            assert claw(scan, node) is None, f"{name} fired on a fully masked graph"


def test_an_empty_reach_abstains_onto_the_backoff(fixtures, cfg):
    """A model whose claws never fire must cost itself nothing beyond the prior."""
    episodes, tok = fixtures

    class _Grasping(OmegaClaw):
        name = "grasping"

        def claws(self):
            return {}

        def weigh(self, name: str, ctx: Hashable, claim: Claim) -> float:
            return 1.0

    model = _Grasping(cfg)
    model.structural_fallback = False       # isolate the abstention path
    model.fit_on(episodes, tok)
    batch = collate_graph(episodes[:2], tok, rng=np.random.default_rng(0))
    with torch.no_grad():
        logits = model.eval()(batch).symbol_logits
    view = model._view(batch, 0)
    assert view.hidden, "the fixture produced no hidden nodes to check"
    assert torch.allclose(logits[0, view.hidden[0]], model.symbol_backoff,
                          atol=1e-5)


# ---------------------------------------------------------------------------
# the machinery the base class took over
# ---------------------------------------------------------------------------
def test_reliability_is_shrunk_towards_the_global_rate(fitted):
    """A cell seen once must not be allowed to claim certainty.

    The whole reason ``reliability`` shrinks is that the default context key
    produces far more cells than there are examples to fill them. This checks
    the shrinkage is real: a perfect one-shot cell must land strictly between
    its raw rate and the claw's global rate.
    """
    model = fitted["omegaclaw_ctx"]
    thin = [(key, name) for (key, name), (fired, right) in model.claw_evidence.items()
            if fired == 1 and right == 1]
    if not thin:
        pytest.skip("no single-observation cell in this fixture")
    key, name = thin[0]
    overall = model.reliability(name)
    here = model.reliability(name, key)
    assert overall < here < 1.0


@pytest.mark.parametrize("name", FAMILY)
def test_the_learned_state_survives_a_round_trip(name, fitted, fixtures, cfg):
    """``LEARNED`` must name everything, or a reloaded run predicts differently.

    A rule-based model's tables are ordinary Python objects that ``state_dict``
    cannot see, so this is the check that the family named all of its own.
    """
    episodes, tok = fixtures
    batch = collate_graph(episodes[:2], tok, rng=np.random.default_rng(2))
    with torch.no_grad():
        before = fitted[name](batch).symbol_logits

    reloaded = build(name, cfg)
    reloaded.load_symbolic_state(fitted[name].symbolic_state(), tok)
    reloaded.symbol_backoff.copy_(fitted[name].symbol_backoff)
    reloaded.type_backoff.copy_(fitted[name].type_backoff)
    with torch.no_grad():
        after = reloaded.eval()(batch).symbol_logits
    assert torch.allclose(before, after, atol=1e-6)


@pytest.mark.parametrize("name", FAMILY)
def test_the_confidence_is_measured_not_asserted(name, fitted):
    """Every member inherits the held-out calibration, so every map is fitted.

    ``workspace`` stated 0.534 and delivered 0.216 before it grew one of these.
    Moving the calibration into the base class is most of what the abstraction
    is for, and a member whose map silently failed to fit would be back to a
    hand-written formula without anyone noticing.

    Both heads, because sharing one map between them is precisely the mistake
    this family made and measured: a type lift of −1.96 for ``omegaclaw_flat``
    on the first sweep, from stating the label head's confidence about a
    question the label head had not been asked.
    """
    assert fitted[name].confidence_map.fitted
    assert fitted[name].type_confidence_map.fitted


@pytest.mark.parametrize("name", FAMILY)
def test_the_render_is_readable(name, fitted):
    """The artifact of a symbolic run is text you can argue with."""
    rendered = fitted[name].render()
    assert "claws" in rendered and "confidence map" in rendered
    assert any(claw in rendered for claw in CLAWS)


# ---------------------------------------------------------------------------
# the substrate claim itself
# ---------------------------------------------------------------------------
def test_a_new_member_of_the_family_is_one_method(fixtures, cfg):
    """The claim the ABC is being judged on, written as a test.

    Everything a new symbolic model needs — masked training views, evidence over
    a structural operator set, held-out calibration, a proper distribution, a
    type head, abstention onto the shared back-off — arrives from the base
    class. What is left for a new model is ``weigh``. If this test ever needs a
    second method to pass, the abstraction has stopped earning its keep and the
    family should be told so here first.
    """
    episodes, tok = fixtures

    class _PeerOnly(OmegaClaw):
        """Believe the peer claw and nothing else."""

        name = "peeronly"

        def weigh(self, name: str, ctx: Hashable, claim: Claim) -> float:
            return 1.0 if name == "peer" else 0.0

    model = _PeerOnly(cfg)
    model.fit_on(episodes, tok)
    batch = collate_graph(episodes, tok, rng=np.random.default_rng(0))
    with torch.no_grad():
        logits = model.eval()(batch).symbol_logits
    mass = logits.exp().sum(-1)
    assert torch.isfinite(logits).all()
    assert torch.allclose(mass, torch.ones_like(mass), atol=1e-3)
    # A one-claw model is the case where the shared calibration runs out of
    # evidence: `peer` fires on a minority of nodes, so the held-out fifth of
    # this fixture yields fewer than the ten observations `ScoreCalibrator`
    # insists on, and the map declines to fit. That is the base class degrading
    # to its cautious formula rather than failing, and the confidence it states
    # must still be a usable number.
    assert 0.0 < model.confidence(0.5) <= 0.9


# ---------------------------------------------------------------------------
# omegaclaw_em: the estimator, isolated
# ---------------------------------------------------------------------------
def test_the_default_estimator_is_plain_hard_counting():
    """`_observe`/`_estimate` split the fitting in two; the default must not
    have changed what the family already measured."""
    from symbolic_ai_models.models.omegaclaw import OmegaClaw

    class Probe(OmegaClaw):
        def weigh(self, name, ctx, claim):
            return 1.0

    probe = Probe(ModelConfig(vocab_size=64))
    records = [
        ("ctx-a", (("peer", 5), ("echo", 9)), 5),      # peer right, echo wrong
        ("ctx-a", (("peer", 7), ("echo", 7)), 7),      # both right
        ("ctx-b", (("peer", 1),), 2),                  # peer wrong, alone
    ]
    evidence, totals = probe._estimate(records)
    assert totals["peer"] == [3.0, 2.0]
    assert totals["echo"] == [2.0, 1.0]
    assert evidence[("ctx-a", "peer")] == [2.0, 2.0]
    assert evidence[("ctx-b", "peer")] == [1.0, 0.0]


def test_em_reduces_to_counting_when_no_two_claws_agree():
    """Hard counting is the limiting case, so the difference between the two
    models is only ever about redundancy — never about anything else."""
    from symbolic_ai_models.models.omegaclaw_em_001 import OmegaClawEM

    model = OmegaClawEM(ModelConfig(vocab_size=64))
    # Every example has exactly one correct claw, so there is nothing to share.
    records = [("c", (("peer", 1), ("echo", 2)), 1)] * 40 + \
              [("c", (("peer", 3), ("echo", 4)), 4)] * 40
    _, totals = model._estimate(records)
    assert totals["peer"][1] == pytest.approx(40.0, abs=0.5)
    assert totals["echo"][1] == pytest.approx(40.0, abs=0.5)


def test_em_splits_credit_between_claws_that_always_agree():
    """The failure it exists for: two claws, one solved problem, two hits."""
    from symbolic_ai_models.models.omegaclaw_em_001 import OmegaClawEM

    model = OmegaClawEM(ModelConfig(vocab_size=64))
    records = [("c", (("peer", 1), ("mirror", 1)), 1)] * 60
    _, totals = model._estimate(records)
    hard = sum(totals[n][1] for n in ("peer", "mirror"))
    assert hard == pytest.approx(60.0, abs=1.0), "credit must be conserved"
    # Neither may keep a full hit rate: that is exactly the double count.
    for name in ("peer", "mirror"):
        assert totals[name][1] / totals[name][0] < 0.95


def test_em_charges_a_claw_that_is_never_uniquely_right():
    """A claw riding along behind a better one should lose its reputation."""
    from symbolic_ai_models.models.omegaclaw_em_001 import OmegaClawEM

    model = OmegaClawEM(ModelConfig(vocab_size=64))
    records = (
        # `mirror` is right alone half the time...
        [("c", (("mirror", 1),), 1)] * 40 +
        # ...and `tagalong` is only ever right in its company.
        [("c", (("mirror", 2), ("tagalong", 2)), 2)] * 40
    )
    _, totals = model._estimate(records)
    mirror = totals["mirror"][1] / totals["mirror"][0]
    tagalong = totals["tagalong"][1] / totals["tagalong"][0]
    assert mirror > tagalong, "EM did not discount the redundant claw"


def test_perfectly_redundant_claws_split_evenly_and_stay_there():
    """The degeneracy that would make the ranking meaningless, ruled out.

    Two claws that always fire together and are always both right carry no
    information distinguishing them, so a mixture's likelihood is flat between
    "a did it" and "b did it". If the iteration broke that tie it would be
    inventing a ranking from the initialisation. It does not: the symmetric
    fixed point is stable at any number of rounds.
    """
    from symbolic_ai_models.models.omegaclaw_em_001 import OmegaClawEM

    records = [("c", (("a", 1), ("b", 1)), 1)] * 200
    for rounds in (1, 12, 200, 1000):
        model = OmegaClawEM(ModelConfig(
            vocab_size=64, extra={"em_rounds": rounds, "em_tolerance": 0.0}))
        _, totals = model._estimate(records)
        assert totals["a"][1] == pytest.approx(totals["b"][1], rel=1e-6), (
            f"the tie broke after {rounds} rounds")


def test_the_default_round_budget_actually_reaches_the_fixed_point():
    """Stopping early understates redundancy, which is the whole measurement.

    A claw right only in a better claw's company reads 0.500 after one round
    and 0.0885 at the fixed point; twelve rounds gives 0.147 and would have
    been reported as the answer. The default has to converge on its own.
    """
    from symbolic_ai_models.models.omegaclaw_em_001 import OmegaClawEM

    records = ([("c", (("a", 1), ("b", 1)), 1)] * 100
               + [("c", (("a", 2),), 2)] * 100)
    default = OmegaClawEM(ModelConfig(vocab_size=64))
    _, at_default = default._estimate(records)

    converged = OmegaClawEM(ModelConfig(
        vocab_size=64, extra={"em_rounds": 5000, "em_tolerance": 0.0}))
    _, at_convergence = converged._estimate(records)

    for name in ("a", "b"):
        rate = at_default[name][1] / at_default[name][0]
        limit = at_convergence[name][1] / at_convergence[name][0]
        assert rate == pytest.approx(limit, abs=0.01), (
            f"{name} had not converged under the default budget")
