"""The two controls the readout finding turns on, pinned so they cannot rot.

``notes/findings/2026-08-14-the-action-readout-clears-the-repair-floor-on-179-lessons.md``
reports a 0.423 gap between reading one fitted model's output as a **move** and
reading it as **text**. Two things have to be true for that number to mean what
it says, and both are properties of code rather than of a run:

1. ``graphread-capped`` really is ``graphread`` *under* ``wrap``'s shortlist —
   the same eight strings, ranked by the same shared prior, and no vote outside
   them. A control that quietly saw a ninth candidate would understate the
   confound it was built to measure, and the run would look like a refutation
   that landed.
2. ``abstain`` really is the abstention path and nothing else, so that "what
   silence is worth on ``repair``" is a measured row rather than an inference
   from a model that happened to emit nothing.

Neither is checked by ``tests/test_agents.py``: the cross-product there asks
whether an agent is well-formed, and both of these are well-formed however wrong
they are.
"""

from __future__ import annotations

import pytest

from symbolic_ai_models.data.curriculum import generate

from symbolic_ai_agents.agents import LearnContext, build as build_agent
from symbolic_ai_agents.envs import build as build_env, rollout
from symbolic_ai_agents.train import RunConfig, make_tokenizer

LESSONS = ["unification", "symbol_grounding"]
CAP = 8


@pytest.fixture(scope="module")
def fixtures():
    episodes = list(generate(LESSONS, n=4))
    tok = make_tokenizer(RunConfig(vocab_size=900), episodes)
    return episodes, tok


def _fitted(name, extra, fixtures):
    episodes, tok = fixtures
    envs = {"repair": build_env("repair")}
    agent = build_agent(name, extra)
    agent.fit(LearnContext(episodes=episodes, tok=tok, envs=envs))
    return agent


@pytest.fixture(scope="module")
def uncapped(fixtures):
    return _fitted("graphread", {"model": "ngram", "channel": "symbol"}, fixtures)


@pytest.fixture(scope="module")
def capped(fixtures):
    return _fitted("graphread-capped",
                   {"model": "ngram", "channel": "symbol", "max_actions": CAP},
                   fixtures)


def _repair_views(agent, fixtures):
    """Every ``repair`` observation, with the agent installed as it acts."""
    episodes, tok = fixtures
    env = build_env("repair")
    for ep in episodes:
        obs = env.reset(ep, tok=tok)
        agent.begin(env, obs)
        for _ in range(max(env.horizon, 1)):
            yield env, obs
            step = env.step(obs.actions[0] if obs.actions else "")
            if step.done or step.next_obs is None:
                break
            obs = step.next_obs


# ---------------------------------------------------------------------------
# control 1: the cap is really wrap's cap
# ---------------------------------------------------------------------------
def test_the_capped_agent_never_votes_outside_wraps_shortlist(capped, fixtures):
    """The whole point of the control: same eight strings, no ninth.

    The shortlist is recomputed here from the base-class method rather than read
    off the agent, so a future edit that gave ``graphread-capped`` a private
    ranking would fail this instead of silently measuring something else.
    """
    seen = 0
    for _, obs in _repair_views(capped, fixtures):
        if obs.graph is None or not obs.actions:
            continue
        votes, _ = capped._raw(obs)
        if not votes:
            continue
        seen += 1
        allowed = set(capped.shortlist(obs, obs.actions, CAP))
        assert set(votes) <= allowed, \
            f"capped agent voted for {set(votes) - allowed}, outside the top-{CAP}"
        assert len(allowed) <= CAP
    assert seen, "the capped agent never spoke, so nothing was pinned"


def test_the_shortlist_is_the_one_wrap_uses(fixtures):
    """``wrap._shortlist`` delegates to the base method; if it stops, say so.

    The refactor that moved the ranking into
    :meth:`~symbolic_ai_agents.agents.base.PolicyAgent.shortlist` was made so
    that there would be exactly one ranking rule. Two copies drifting apart is
    the failure ``reference_floor`` records about two copies of a floor.
    """
    wrap = _fitted("wrap", {"model": "ngram", "max_actions": CAP}, fixtures)
    checked = 0
    for _, obs in _repair_views(wrap, fixtures):
        if not obs.actions:
            continue
        checked += 1
        assert wrap._shortlist(obs) == wrap.shortlist(obs, obs.actions, CAP)
    assert checked, "no observation carried actions"


def test_an_uncapped_capped_agent_is_the_plain_one(uncapped, fixtures):
    """``max_actions <= 0`` must reproduce ``graphread`` exactly.

    This is what makes the ladder a ladder: the capped row differs from the
    plain one in the cap and in nothing else, so the difference between them
    prices the cap. If the two disagree with the cap switched off, they differ
    somewhere the finding would attribute to truncation.
    """
    off = _fitted("graphread-capped",
                  {"model": "ngram", "channel": "symbol", "max_actions": 0},
                  fixtures)
    checked = 0
    for _, obs in _repair_views(off, fixtures):
        if obs.graph is None or not obs.actions:
            continue
        checked += 1
        mine, my_raw = off._raw(obs)
        theirs, their_raw = uncapped._raw(obs)
        assert mine == theirs, "capped-with-no-cap disagrees with graphread"
        assert my_raw == pytest.approx(their_raw)
    assert checked, "no graph-carrying observation was seen"


def test_the_cap_can_only_narrow_the_vote(capped, uncapped, fixtures):
    """A control that *added* a candidate would be measuring the wrong thing."""
    for _, obs in _repair_views(capped, fixtures):
        if obs.graph is None or not obs.actions:
            continue
        narrow, _ = capped._raw(obs)
        wide, _ = uncapped._raw(obs)
        assert set(narrow) <= set(wide), \
            "the cap introduced an action the uncapped readout never voted for"


# ---------------------------------------------------------------------------
# control 2: abstain is the abstention path
# ---------------------------------------------------------------------------
def test_abstain_never_speaks(fixtures):
    agent = _fitted("abstain", {}, fixtures)
    for _, obs in _repair_views(agent, fixtures):
        votes, conf = agent.prefer(obs)
        assert votes == {} and conf == 0.0


def test_abstain_matches_a_model_that_emits_nothing(fixtures):
    """The two routes to the abstention path must agree move for move.

    ``notes/findings/2026-08-13-abstention-on-repair-is-below-chance.md`` read
    the abstention number off ``graphread`` pointed at models with no votes to
    give, and its own control was that two such rows agreed to the last digit.
    That control is only as durable as the models staying broken, so the
    explicit agent is pinned against the accidental one here instead.

    ``ngram`` has no ``source_votes``, so ``channel=node`` abstains on every
    decision by construction — the second of the two routes that note used.
    """
    episodes, tok = fixtures
    silent = _fitted("graphread", {"model": "ngram", "channel": "node"}, fixtures)
    explicit = _fitted("abstain", {}, fixtures)
    env_a, env_b = build_env("repair"), build_env("repair")
    compared = 0
    for ep in episodes:
        mine = [m.action for m in rollout(env_a, explicit, ep, tok=tok).moves]
        theirs = [m.action for m in rollout(env_b, silent, ep, tok=tok).moves]
        compared += len(mine)
        assert mine == theirs, \
            "the explicit abstainer and a silent model took different actions"
    assert compared, "nothing was compared"
    assert silent.spoke == 0, \
        "ngram emitted source_votes after all; pick another silent route"
