"""The third readout, and the agent that acts through it.

``symbol`` and ``site`` are scored against a target computed from the answer key.
``action`` is scored by an environment, which is a different kind of pressure and
gets its own file: what is pinned here is that the channel is really a knob, that
a pointer is scored by what it picked rather than by index, and — the one that
matters most — that ``graphread`` **abstains rather than switching mechanism**.

A row that quietly fell back to text scoring where the graph was missing would
be a measurement of neither reading, and nothing else in the suite could see it:
the numbers would still be numbers and the tests would still be green. So the
abstention is checked against a mute agent's trajectory, exactly, rather than
against a docstring.
"""

from __future__ import annotations

import pytest

from symbolic_ai_core.graphview import GraphView, Votes
from symbolic_ai_core.readout import CHANNELS, NODE, REGISTRY, SYMBOL
from symbolic_ai_models.data.curriculum import generate

from symbolic_ai_agents.agents import LearnContext, build as build_agent
from symbolic_ai_agents.agents.base import ABSTAIN, PolicyAgent
from symbolic_ai_agents.envs import build as build_env, rollout
from symbolic_ai_agents.envs.base import Observation
from symbolic_ai_agents.readouts.action import (BOTH, ActionReadout, Asked,
                                                Emission)
from symbolic_ai_agents.train import RunConfig, make_tokenizer

import numpy as np

LESSONS = ["unification", "symbol_grounding"]


# ---------------------------------------------------------------------------
# a stub, so the readout can be tested without fitting a model first
# ---------------------------------------------------------------------------
class Toy:
    """A four-word vocabulary, standing in for a ``SymbolTokenizer``."""

    itos = ["<pad>", "frank", "mary", "carol"]
    stoi = {w: i for i, w in enumerate(itos)}

    def __len__(self) -> int:
        return len(self.itos)


def toy_view() -> GraphView:
    """Four nodes: two of them spell ``frank``, one ``mary``, and node 3 is asked.

    The duplicate is the point. A pointer that split its mass between the two
    ``frank`` nodes was never unsure about the *answer*, only about the
    evidence, and the readout has to say so.
    """
    return GraphView(labels=[1, 1, 2, None], types=["token"] * 3 + [None],
                     parent=[-1, 0, 0, 0], slot=[0, 0, 1, 2], depth=[0, 1, 1, 1],
                     rel=np.zeros((4, 4), dtype=np.uint8), hidden=[3], tok=Toy())


def toy_obs(view: GraphView, actions=("frank", "mary", "carol")) -> Observation:
    return Observation(text="name the node marked ?", actions=actions,
                       graph=view, node=3, key="toy")


def emission(symbol: Votes | None = None, node: Votes | None = None) -> Emission:
    channels = {}
    if symbol is not None:
        channels[SYMBOL] = {3: symbol}
    if node is not None:
        channels[NODE] = {3: node}
    return Emission(channels=channels)


# ---------------------------------------------------------------------------
# the protocol
# ---------------------------------------------------------------------------
def test_the_action_readout_lives_in_the_shared_registry():
    """Registered in `symbolic_ai_core`, not in a registry of its own — or "the
    readout is a knob" is two knobs in two packages."""
    cls = REGISTRY.get("action")
    assert cls is ActionReadout
    assert cls.channel in CHANNELS and cls.prefix == "action"


def test_an_unknown_channel_is_refused_rather_than_silently_defaulted():
    """A typo that fell back to `symbol` would print a row labelled `node`."""
    with pytest.raises(ValueError, match="unknown channel"):
        ActionReadout(channel="pointer")


# ---------------------------------------------------------------------------
# the knob
# ---------------------------------------------------------------------------
def test_the_two_channels_read_the_same_emission_differently():
    """The knob has to *do* something, or the two rows measure nothing.

    The vocabulary head here says ``mary`` and the pointer head points at the two
    nodes spelling ``frank``. One emission, two readings, two answers.
    """
    view, out = toy_view(), emission(symbol=({2: 1.0}, 0.8),
                                     node=({0: 0.5, 1: 0.4}, 0.7))
    obs = toy_obs(view)
    by_symbol, _ = ActionReadout(channel=SYMBOL).prefer(out, obs)
    by_node, _ = ActionReadout(channel=NODE).prefer(out, obs)
    assert max(by_symbol, key=by_symbol.get) == "mary"
    assert max(by_node, key=by_node.get) == "frank"


def test_a_pointer_is_scored_by_what_it_picked_and_not_by_index():
    """Two nodes spelling one word are one answer, so their weight is summed.

    Keeping them apart would let a pointer that hedged between equivalent
    sources lose to one that guessed a single wrong node, which is the failure
    `_pointer_counts` established the rule against.
    """
    view = toy_view()
    out = emission(node=({0: 0.3, 1: 0.3, 2: 0.35}, 0.6))
    votes, _ = ActionReadout(channel=NODE).prefer(out, toy_obs(view))
    assert votes["frank"] > votes["mary"], \
        "the two nodes spelling 'frank' did not combine into one answer"


def test_both_normalises_before_summing_so_neither_channel_can_shout():
    """`both` is a sum of two unit-mass distributions, not of two raw ones.

    The pointer here carries twenty times the raw weight of the vocabulary head.
    If the sum were taken raw it would decide the answer on its own, and the
    setting would be `node` wearing another name.
    """
    view = toy_view()
    out = emission(symbol=({2: 0.05}, 0.9), node=({0: 1.0}, 0.9))
    votes, _ = ActionReadout(channel=BOTH).prefer(out, toy_obs(view))
    assert votes["frank"] == pytest.approx(votes["mary"]), \
        "one channel outvoted the other by raw magnitude"


def test_an_action_the_environment_did_not_offer_is_dropped():
    view = toy_view()
    out = emission(symbol=({1: 0.9, 2: 0.1}, 0.9))
    votes, _ = ActionReadout().prefer(out, toy_obs(view, actions=("mary",)))
    assert set(votes) == {"mary"}


def test_a_channel_the_model_does_not_emit_is_an_abstention_not_a_zero():
    view = toy_view()
    assert ActionReadout(channel=NODE).prefer(emission(symbol=({1: 1.0}, 0.9)),
                                              toy_obs(view)) == ABSTAIN
    assert ActionReadout().prefer(emission(), toy_obs(view)) == ABSTAIN


def test_no_graph_means_abstain():
    """`choice` carries no graph. The readout must say nothing rather than
    invent something out of the text."""
    bare = Observation(text="who?", actions=("frank", "mary"))
    assert ActionReadout().prefer(emission(symbol=({1: 1.0}, 0.9)), bare) == ABSTAIN


# ---------------------------------------------------------------------------
# counts and the floor
# ---------------------------------------------------------------------------
def test_speaking_wrongly_and_not_speaking_are_different_counts():
    """One column cannot hold "has no pointer" and "has a bad pointer"."""
    view, readout = toy_view(), ActionReadout(channel=NODE)
    spoke = readout.score(emission(node=({2: 1.0}, 0.8)),
                          Asked(toy_obs(view), gold="frank"))
    mute = readout.score(emission(), Asked(toy_obs(view), gold="frank"))
    assert spoke["action_n"] == spoke["action_spoke"] == 1.0
    assert spoke["action_correct"] == 0.0
    assert mute == {"action_n": 1.0, "action_abstain": 1.0}

    from symbolic_ai_core.floors import Totals
    totals = Totals()
    for counts in (spoke, mute):
        for k, v in counts.items():
            totals[k] = totals.get(k, 0.0) + v
    summary = readout.summarize(totals)
    assert summary["action_speak"] == 0.5
    assert summary["action_yield"] == 0.0


@pytest.fixture(scope="module")
def fixtures():
    episodes = list(generate(LESSONS, n=3))
    tok = make_tokenizer(RunConfig(vocab_size=900), episodes)
    return episodes, tok


def test_the_floor_is_the_environments_own_and_says_which_policy_set_it(fixtures):
    """Reused, not re-derived. Two near-identical copies of a floor drift and
    nothing notices — this repo has published a lift over one 0.065 too low."""
    episodes, tok = fixtures
    env = build_env("repair")
    got = ActionReadout().floor(episodes, tok, episodes, env=env)
    assert got["action_floor_by"] in ("random", "shortcut", "context")
    assert 0.0 <= got["action_acc"] <= 1.0


def test_the_floor_refuses_to_be_computed_without_an_environment(fixtures):
    episodes, tok = fixtures
    with pytest.raises(ValueError, match="needs env"):
        ActionReadout().floor(episodes, tok, episodes)


# ---------------------------------------------------------------------------
# the agent
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def envs():
    return {n: build_env(n) for n in ("choice", "repair")}


@pytest.fixture(scope="module")
def graphread(fixtures, envs):
    episodes, tok = fixtures
    agent = build_agent("graphread", {"model": "ngram", "channel": "symbol"})
    agent.fit(LearnContext(episodes=episodes, tok=tok, envs=envs))
    return agent


def test_graphread_reads_the_graph_head_where_wrap_reads_text(graphread, fixtures,
                                                              envs):
    """The one difference between the two agents, checked at the seam.

    ``wrap``'s docstring admits "the graph head is not used"; this asserts the
    other half of that sentence — that this agent's preference comes from
    ``node_votes`` and from nothing else. Emptying the emission must silence it.
    """
    episodes, tok = fixtures
    env = envs["repair"]
    for ep in episodes:
        obs = env.reset(ep, tok=tok)
        if obs.graph is None or obs.node < 0:
            continue
        graphread.begin(env, obs)
        mine, _ = graphread._raw(obs)
        theirs, _ = graphread.readout.prefer(
            Emission({SYMBOL: {i: v[0] for i, v in
                               graphread.model.node_votes(obs.graph).items()}}), obs)
        assert mine == dict(theirs)


def test_graphread_abstains_on_choice_and_does_not_fall_back_to_text(fixtures, envs):
    """Its ``choice`` row IS the shared prior, and this is what says so.

    A silent fallback to text scoring would make that row a ``wrap`` row wearing
    this agent's name, and every comparison between the two columns would be
    measuring the fallback. Checked against a mute agent, action for action.
    """
    episodes, tok = fixtures

    class Mute(PolicyAgent):
        name = "mute"

        def prefer(self, obs):
            return ABSTAIN

    mute = Mute()
    mute.fit(LearnContext(episodes=episodes, tok=tok, envs=envs))
    agent = build_agent("graphread", {"model": "ngram"})
    agent.fit(LearnContext(episodes=episodes, tok=tok, envs=envs))

    env = build_env("choice")
    for ep in episodes:
        mine = [m.action for m in rollout(env, agent, ep, tok=tok).moves]
        theirs = [m.action for m in rollout(env, mute, ep, tok=tok).moves]
        assert mine == theirs, "graphread did something on `choice`, where it has "\
                               "no graph to read — the mechanism switched"


def test_graphread_reports_how_often_it_abstained(graphread, fixtures, envs):
    """An abstention rate that is not printed is an abstention rate nobody
    checks, and this agent's headline environments are ones where it is 100%."""
    episodes, tok = fixtures
    before = graphread.asked
    for ep in episodes:
        rollout(envs["repair"], graphread, ep, tok=tok)
    assert graphread.asked > before
    assert 0 <= graphread.spoke <= graphread.asked
    assert "abstained onto the shared prior" in graphread.render()


@pytest.mark.parametrize("channel", [SYMBOL, NODE, BOTH])
def test_every_channel_acts_legally_in_every_environment(channel, fixtures, envs):
    """A model emitting nothing on a channel must still produce a legal agent —
    unscored, never crashed."""
    episodes, tok = fixtures
    agent = build_agent("graphread", {"model": "ptrgen-001", "channel": channel})
    agent.fit(LearnContext(episodes=episodes, tok=tok, envs=envs))
    for env in envs.values():
        for ep in episodes:
            traj = rollout(env, agent, ep, tok=tok)
            assert traj.moves
            for move in traj.moves:
                assert move.action in move.obs.choices


def test_a_neural_model_is_refused_rather_than_trained_badly(fixtures):
    """Same refusal as ``wrap``: an agent run is a fit, not a schedule."""
    import symbolic_ai_models.models as M
    if not M.NEURAL_ENABLED:
        pytest.skip("neural models are not registered (SYMBOLIC_AI_MODELS_NEURAL)")
    episodes, tok = fixtures
    agent = build_agent("graphread", {"model": "gru"})
    with pytest.raises(ValueError, match="needs a training budget"):
        agent.fit(LearnContext(episodes=episodes, tok=tok, envs={}))
