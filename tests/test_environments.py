"""Every environment, against the contract the harness assumes of all of them.

Parameterised over the registry, so a new environment is covered the moment it
is registered and cannot be added without presenting an observation, taking an
action, ending, and — the two that matter — being reproducible and not handing
the answer to the thing being asked.
"""

from __future__ import annotations

import pytest

from symbolic_ai_models.data.curriculum import generate

from symbolic_ai_agents.envs import REGISTRY, build, env_names
from symbolic_ai_agents.train import RunConfig, make_tokenizer

LESSONS = ["unification", "symbol_grounding"]


@pytest.fixture(scope="module")
def fixtures():
    episodes = list(generate(LESSONS, n=3))
    tok = make_tokenizer(RunConfig(vocab_size=900), episodes)
    return episodes, tok


# ---------------------------------------------------------------------------
# the shared contract
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("name", env_names())
def test_presents_something_to_do(name, fixtures):
    episodes, tok = fixtures
    env = build(name)
    for ep in episodes:
        obs = env.reset(ep, tok=tok)
        assert obs.text, f"{name}: an observation with no text"
        assert obs.choices, f"{name}: an observation with nothing legal to do"
        assert obs.key, f"{name}: an observation that does not say which question"


@pytest.mark.parametrize("name", env_names())
def test_terminates_within_its_horizon(name, fixtures):
    """Taking the first legal action every time must end inside the horizon."""
    episodes, tok = fixtures
    env = build(name)
    for ep in episodes:
        obs = env.reset(ep, tok=tok)
        for _ in range(env.horizon):
            step = env.step(obs.choices[0])
            if step.done:
                break
            assert step.next_obs is not None, f"{name}: not done and no next"
            obs = step.next_obs
        else:                                             # pragma: no cover
            pytest.fail(f"{name}: ran past its horizon of {env.horizon}")


@pytest.mark.parametrize("name", env_names())
def test_two_resets_give_the_identical_world(name, fixtures):
    """A floor that moved between runs would make every lift unreproducible.

    Environments seed themselves from the episode, so this is the property that
    lets two agents be compared: they face the same masked nodes and the same
    redacted lines, and a difference between them is a difference between them.
    """
    episodes, tok = fixtures
    for ep in episodes:
        first = build(name).reset(ep, tok=tok)
        second = build(name).reset(ep, tok=tok)
        assert first.text == second.text
        assert first.actions == second.actions
        assert first.probes == second.probes


@pytest.mark.parametrize("name", env_names())
def test_the_oracle_is_always_right(name, fixtures):
    """Following the oracle must solve the episode, in every environment.

    This is what makes ``training_views`` a training set rather than a source of
    plausible-looking noise: an agent fitted on the oracle's answers is fitted
    on answers that were actually correct.
    """
    episodes, tok = fixtures
    env = build(name)
    for ep in episodes:
        env.reset(ep, tok=tok)
        for _ in range(env.horizon):
            gold = env.oracle()
            if gold is None:
                break                        # nothing to be right about here
            step = env.step(gold)
            assert step.correct is not False, \
                f"{name}: the oracle's own action was scored wrong"
            if step.done:
                assert step.info.get("solved", 1.0), \
                    f"{name}: following the oracle did not solve the episode"
                break


@pytest.mark.parametrize("name", env_names())
def test_the_oracle_is_a_legal_action(name, fixtures):
    """An answer the agent could not have given is not a target it can be
    fitted against."""
    episodes, tok = fixtures
    env = build(name)
    for ep in episodes:
        obs = env.reset(ep, tok=tok)
        gold = env.oracle()
        if gold is not None:
            assert gold in obs.choices or gold.strip() in [c.strip() for c
                                                           in obs.choices]


# ---------------------------------------------------------------------------
# the leak tests
# ---------------------------------------------------------------------------
def test_repair_never_shows_a_hidden_label(fixtures):
    """The node being asked about is ``None`` in the view, not merely marked.

    Structural rather than promised: there is no field holding the value being
    predicted, so an agent that wanted to cheat has nothing to read. The same
    guarantee :class:`symbolic_ai_models.models.symbolic.GraphView` gives the
    rule-based models.
    """
    episodes, tok = fixtures
    env = build("repair")
    for ep in episodes:
        obs = env.reset(ep, tok=tok)
        while True:
            if obs.graph is not None and obs.node >= 0:
                assert obs.graph.labels[obs.node] is None
                assert obs.graph.types[obs.node] is None
                assert obs.graph.word(obs.node) is None
                assert env.oracle() not in (None, "")
                # ...and the answer is not sitting in the rendered text either.
                assert "?" in obs.text
            step = env.step(obs.choices[0])
            if step.done or step.next_obs is None:
                break
            obs = step.next_obs


def test_probe_hides_something_and_reveals_it_when_paid(fixtures):
    episodes, tok = fixtures
    env = build("probe")
    revealed_any = False
    for ep in episodes:
        obs = env.reset(ep, tok=tok)
        if not obs.probes:
            continue
        assert "(hidden)" in obs.text
        step = env.step(obs.probes[0])
        assert step.reward < 0, "a probe that costs nothing is not a probe"
        assert not step.done and step.next_obs is not None
        assert step.next_obs.text.count("(hidden)") < obs.text.count("(hidden)")
        assert len(step.next_obs.probes) < len(obs.probes)
        revealed_any = True
    assert revealed_any, "no episode in the fixture offered a probe"


def test_probe_never_hides_the_question(fixtures):
    """Anchoring the redaction on the last matching segment hid the question
    itself, which made the environment a guessing game. Pinned here."""
    episodes, tok = fixtures
    env = build("probe")
    for ep in episodes:
        obs = env.reset(ep, tok=tok)
        visible = obs.text.split("(hidden)")[-1]
        assert "?" in visible or " | " in visible


def test_retry_pays_the_reciprocal_rank(fixtures):
    """Right on try k is worth 1/k, and running out is worth nothing."""
    episodes, tok = fixtures
    env = build("retry", tries=3)
    ep = episodes[0]
    obs = env.reset(ep, tok=tok)
    wrong = [c for c in obs.actions if c.strip() != ep.answer.strip()]
    env.step(wrong[0])
    step = env.step(ep.answer)
    assert step.done and step.correct
    assert step.reward == pytest.approx(0.5)


def test_repair_errors_stay_on_the_page(fixtures):
    """A wrong fill is what the agent reads at the next node. Teacher forcing
    would put the truth there instead, and that difference is the whole point
    of this environment."""
    episodes, tok = fixtures
    env = build("repair", mask_rate=0.9, max_steps=8)
    for ep in episodes:
        obs = env.reset(ep, tok=tok)
        gold = env.oracle()
        if gold is None:
            continue
        wrong = next((a for a in obs.actions if a != gold), None)
        node = obs.node
        if wrong is None:
            continue
        step = env.step(wrong)
        if step.next_obs is None or step.next_obs.graph is None:
            continue
        after = step.next_obs.graph
        assert after.word(node) == wrong, "the wrong fill did not stay"
        return
    pytest.skip("no episode in the fixture had two candidates and a second node")


@pytest.mark.parametrize("name", env_names())
def test_summarize_reports_a_return_and_a_success(name, fixtures):
    from symbolic_ai_agents.envs.base import Totals, Trajectory

    episodes, tok = fixtures
    env = build(name)
    totals = Totals()
    for ep in episodes:
        env.reset(ep, tok=tok)
        traj = Trajectory(env=name, lesson_id=ep.lesson_id,
                          instance_id=ep.instance_id)
        totals.add(traj.counts())
    metrics = env.summarize(totals)
    assert "return" in metrics and "success" in metrics
    assert metrics["n"] == len(episodes)


def test_a_policy_that_sets_the_floor_has_exactly_zero_lift():
    """The invariant that would have caught a whole broken sweep.

    The floor is the best of the reference policies, and those policies are
    *also* registered agents. So whichever one wins the floor must score exactly
    zero lift against it -- it is being compared to itself.

    It was not. `reference_floor` fitted its copies with one environment and no
    seed while the run fitted the scored agent with all four and `cfg.seed`, and
    `ContextAgent.fit` stores `ctx.envs`, so the two copies learned different
    tables. On the first full-curriculum sweep `context` scored 0.2589 on
    `repair` against a floor of 0.2336 recorded as `floor_by: context` -- and
    that +0.033 was the only positive number in the entire table.

    Nothing caught it because a floor is the one number in a run that nothing
    else is checked against. This is that check, and it is two lines.
    """
    from symbolic_ai_agents.envs import build as build_env
    from symbolic_ai_agents.envs.base import lift

    train = list(generate(LESSONS, n=12))
    evaluation = list(generate(LESSONS, n=6, seed0=1_000_000))
    tok = make_tokenizer(RunConfig(vocab_size=1200), train)
    envs = {name: build_env(name) for name in ("choice", "repair")}

    for name, env in envs.items():
        floor = env.floor(evaluation, tok, train, envs=envs, seed=0)
        winner = floor.get("floor_by")
        assert winner, f"{name}: no policy won the floor"

        scored = _score_policy(winner, env, envs, evaluation, train, tok)
        assert lift(scored, floor["return"]) == pytest.approx(0.0, abs=1e-9), (
            f"{name}: {winner} sets the floor at {floor['return']:.4f} and "
            f"scores {scored:.4f} against it -- the floor is a differently "
            f"fitted copy of the same policy")


def _score_policy(name, env, envs, evaluation, train, tok):
    """Run a policy the way the trainer does, not the way the floor does."""
    from symbolic_ai_agents.agents import build as build_agent
    from symbolic_ai_agents.agents.base import LearnContext
    from symbolic_ai_agents.envs.rollout import rollouts

    policy = build_agent(name, {})
    policy.fit(LearnContext(episodes=list(train), tok=tok, envs=envs, seed=0))
    return env.summarize(rollouts(env, policy, evaluation, tok=tok).totals)["return"]
