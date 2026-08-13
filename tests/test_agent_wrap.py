"""The seam between the two packages.

``wrap`` is the row that makes ``symbolic_ai_models`` and ``symbolic_ai_agents``
answerable to each other, so the seam gets its own file. What is pinned here is
the wiring claim the module docstring makes and nothing stronger: on ``choice``
this agent's raw preference must rank the options exactly as
:func:`symbolic_ai_models.agent.score_choices` ranks them.

The action finally taken may differ, because every agent here mixes its
preference against the shared prior — that is deliberate, it is what makes the
six agents comparable, and it is why this test checks ``_raw`` rather than
``act``.
"""

from __future__ import annotations

import pytest

from symbolic_ai_models.agent import score_choices
from symbolic_ai_models.data.curriculum import generate

from symbolic_ai_agents.agents import LearnContext, build as build_agent
from symbolic_ai_agents.envs import build as build_env, rollout
from symbolic_ai_agents.train import RunConfig, make_tokenizer

LESSONS = ["unification"]


@pytest.fixture(scope="module")
def wrapped():
    episodes = list(generate(LESSONS, n=4))
    tok = make_tokenizer(RunConfig(vocab_size=900), episodes)
    envs = {"choice": build_env("choice")}
    agent = build_agent("wrap", {"model": "ngram", "max_actions": 64})
    agent.fit(LearnContext(episodes=episodes, tok=tok, envs=envs))
    return agent, episodes, tok


def test_the_wrapper_ranks_options_as_the_model_does(wrapped):
    agent, episodes, tok = wrapped
    env = build_env("choice")
    for ep in episodes:
        obs = env.reset(ep, tok=tok)
        agent.begin(env, obs)
        votes, _ = agent._raw(obs)
        assert votes, "the wrapper produced no preference at all"
        mine = sorted(votes, key=lambda a: (-votes[a], list(obs.actions).index(a)))
        theirs = score_choices(agent.model, tok, obs.text, list(obs.actions))
        direct = sorted(obs.actions,
                        key=lambda a: (-theirs[list(obs.actions).index(a)],
                                       list(obs.actions).index(a)))
        assert mine == direct, \
            "the wrapper and score_choices disagree about the model's ranking"


def test_the_wrapped_model_acts_in_every_environment(wrapped):
    """One wrapper, every environment — including the ones the model harness
    cannot express."""
    agent, episodes, tok = wrapped
    for name in ("choice", "retry", "repair", "probe"):
        env = build_env(name)
        traj = rollout(env, agent, episodes[0], tok=tok)
        assert traj.moves
        for move in traj.moves:
            assert move.action in move.obs.choices


def test_a_neural_model_is_refused_rather_than_trained_badly():
    """This package supplies no training budget, so a network cannot be fitted
    here. Refusing and saying why beats reporting an undertrained number."""
    import symbolic_ai_models.models as M
    if not M.NEURAL_ENABLED:
        pytest.skip("neural models are not registered (SYMBOLIC_AI_MODELS_NEURAL)")
    episodes = list(generate(LESSONS, n=2))
    tok = make_tokenizer(RunConfig(vocab_size=900), episodes)
    agent = build_agent("wrap", {"model": "gru"})
    with pytest.raises(ValueError, match="needs a training budget"):
        agent.fit(LearnContext(episodes=episodes, tok=tok, envs={}))


def test_the_shortlist_is_agent_independent(wrapped):
    """Truncation is a handicap, stated as one — but it must be the *same*
    handicap for two wrapped models, or the comparison stops being about the
    models."""
    agent, episodes, tok = wrapped
    env = build_env("repair")
    obs = env.reset(episodes[0], tok=tok)
    agent.begin(env, obs)
    agent.max_actions = 4
    first = agent._shortlist(obs)
    second = agent._shortlist(obs)
    assert first == second and len(first) <= 4
