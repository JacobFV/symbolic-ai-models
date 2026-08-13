"""Every agent, in every environment, against the contract they all answer to.

Parameterised over both registries, so a new agent is covered the moment it is
registered and cannot be added without acting legally everywhere, abstaining
onto the floor rather than below it, and passing the leak test.

The leak test is the "no cheating" rule and it is checked empirically rather
than promised in a docstring: :func:`test_no_agent_consults_the_oracle` replaces
every environment's ``oracle`` with a liar and requires that no trajectory
changes. An agent that fails it is reading its own answer, and its numbers would
be worthless whatever it claims to be doing.
"""

from __future__ import annotations

import pytest

from symbolic_ai_models.data.curriculum import generate

from symbolic_ai_agents.agents import (LearnContext, REGISTRY, agent_names,
                                       build as build_agent)
from symbolic_ai_agents.envs import build as build_env, env_names, rollout
from symbolic_ai_agents.train import RunConfig, make_tokenizer

LESSONS = ["unification", "symbol_grounding"]

#: `wrap` builds and fits a whole model from the other package, which is far
#: slower than the rest. It is still covered — see `test_agent_wrap.py` — but it
#: is skipped in the cross-product so this file stays quick enough to run often.
EXPENSIVE = {"wrap"}
CHEAP = [n for n in agent_names() if n not in EXPENSIVE]


@pytest.fixture(scope="module")
def fixtures():
    episodes = list(generate(LESSONS, n=3))
    tok = make_tokenizer(RunConfig(vocab_size=900), episodes)
    return episodes, tok


@pytest.fixture(scope="module")
def envs():
    return {n: build_env(n) for n in env_names()}


def fitted(name: str, fixtures, envs):
    episodes, tok = fixtures
    agent = build_agent(name, {})
    agent.fit(LearnContext(episodes=episodes, tok=tok, envs=envs))
    return agent


@pytest.fixture(scope="module")
def agents(fixtures, envs):
    return {n: fitted(n, fixtures, envs) for n in CHEAP}


# ---------------------------------------------------------------------------
# the shared contract
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("agent_name", CHEAP)
@pytest.mark.parametrize("env_name", env_names())
def test_acts_legally_everywhere(agent_name, env_name, fixtures, envs, agents):
    """One agent, every environment, and never an action it was not offered."""
    episodes, tok = fixtures
    agent, env = agents[agent_name], envs[env_name]
    for ep in episodes:
        traj = rollout(env, agent, ep, tok=tok)
        assert traj.moves, f"{agent_name} in {env_name}: did nothing"
        for move in traj.moves:
            assert move.action in move.obs.choices, \
                f"{agent_name}: took {move.action!r}, which was not offered"
            assert 0.0 <= move.confidence <= 1.0


@pytest.mark.parametrize("agent_name", CHEAP)
def test_never_repeats_a_refused_action(agent_name, fixtures, envs, agents):
    """Shared machinery, so `retry` measures a ranking rather than which author
    remembered to write a loop guard."""
    episodes, tok = fixtures
    agent, env = agents[agent_name], envs["retry"]
    for ep in episodes:
        traj = rollout(env, agent, ep, tok=tok)
        taken = [m.action for m in traj.moves]
        assert len(taken) == len(set(taken)), \
            f"{agent_name}: answered {taken} — a refused option came back"


@pytest.mark.parametrize("agent_name", CHEAP)
def test_a_fitted_agent_is_deterministic(agent_name, fixtures, envs, agents):
    """Two evaluations of one agent must agree exactly, `random` included."""
    episodes, tok = fixtures
    agent = agents[agent_name]
    for env_name, env in envs.items():
        first = [m.action for m in rollout(env, agent, episodes[0], tok=tok).moves]
        second = [m.action for m in rollout(env, agent, episodes[0], tok=tok).moves]
        assert first == second, f"{agent_name} in {env_name} moved between runs"


# ---------------------------------------------------------------------------
# the leak test
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("agent_name", CHEAP)
def test_no_agent_consults_the_oracle(agent_name, fixtures, envs, agents,
                                      monkeypatch):
    """Replace every ``oracle`` with a liar; nothing an agent does may change.

    ``Environment.oracle`` is the environment's copy of ``target_tokens``: legal
    inside ``fit`` on training episodes, cheating anywhere else. Rather than ask
    agents not to peek, this makes peeking visible — an agent that reads it
    while acting produces a different trajectory here and fails.
    """
    episodes, tok = fixtures
    agent = agents[agent_name]
    for env_name, env in envs.items():
        honest = [(m.action, m.confidence)
                  for m in rollout(env, agent, episodes[0], tok=tok).moves]
        monkeypatch.setattr(type(env), "oracle",
                            lambda self: "<<< a lie >>>", raising=True)
        lied = [(m.action, m.confidence)
                for m in rollout(env, agent, episodes[0], tok=tok).moves]
        monkeypatch.undo()
        assert honest == lied, \
            f"{agent_name} behaved differently in {env_name} when the oracle lied"


# ---------------------------------------------------------------------------
# abstention
# ---------------------------------------------------------------------------
def test_abstaining_lands_on_the_prior_and_not_below_it(fixtures, envs):
    """An agent with nothing to say scores the floor, not chance.

    The model harness found several rule-based models whose mechanism beat the
    floor comfortably while their score did not, purely because abstaining
    dropped them below the baseline they were compared against. The repair there
    was a structure-aware back-off; the repair here is that the prior an
    abstention falls to *is* the shortcut floor.
    """
    from symbolic_ai_agents.agents.base import ABSTAIN, PolicyAgent

    episodes, tok = fixtures

    class Mute(PolicyAgent):
        name = "mute"

        def prefer(self, obs):
            return ABSTAIN

    mute = Mute()
    mute.fit(LearnContext(episodes=episodes, tok=tok, envs=envs))
    env = envs["choice"]
    picks, cheats = [], []
    for ep in episodes:
        traj = rollout(env, mute, ep, tok=tok)
        picks.append(traj.moves[0].action)
        cheats.append(mute.shortcut.pick(ep.prompt, list(ep.choices))
                      if mute.shortcut else None)
    if mute.shortcut is not None and mute.shortcut_purity > 0.5:
        assert picks == cheats, "an abstention did not land on the best cheat"


def test_random_is_actually_uniform_and_not_quietly_informed(fixtures, envs):
    """`random` must not consult the prior, or the floor it defines would be
    the shortcut's score wearing chance's name."""
    agent = build_agent("random", {})
    assert agent.use_prior is False


# ---------------------------------------------------------------------------
# what each agent claims about itself
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("agent_name", CHEAP)
def test_reports_a_size_and_renders(agent_name, agents):
    agent = agents[agent_name]
    assert isinstance(agent.n_parameters(), int)
    assert agent.n_parameters() >= 0
    assert agent.render().strip()


def test_recall_learned_from_reward_rather_than_from_labels(fixtures, envs):
    """`recall` is the one agent fitted on its own rollouts. If its table is
    empty it silently degrades to the prior and the row means nothing."""
    agent = fitted("recall", fixtures, envs)
    assert agent.value, "recall learned nothing from its own experience"
    assert any(cell[1] > 0 for cell in agent.value.values()), \
        "recall never once got paid, so it has nothing to prefer"
