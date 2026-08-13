"""A run end to end: fit, score against the floor, write, reload, report.

Small on purpose — two lessons and a handful of episodes — because what is being
checked is that the pieces fit together, not that anything scores well. The
numbers a run this size produces are noise and are never asserted on.
"""

from __future__ import annotations

import json

import pytest

from symbolic_ai_agents import RunConfig, load_run, run
from symbolic_ai_agents.calibration import calibrate_agent
from symbolic_ai_agents.envs import build as build_env, rollout
from symbolic_ai_agents.report import comparison_table, config_drift, load_summaries
from symbolic_ai_agents.trace import read_trajectories, transcript

LESSONS = "unification,symbol_grounding"


def config(tmp_path, agent="context", **kw) -> RunConfig:
    return RunConfig(agent=agent, lessons=LESSONS, n_train=4, n_eval=2,
                     vocab_size=900, keep=8, out=str(tmp_path / agent), **kw)


@pytest.fixture(scope="module")
def finished(tmp_path_factory):
    root = tmp_path_factory.mktemp("agent-runs")
    return {name: (run(config(root, name)), root / name)
            for name in ("random", "context")}


def test_a_run_writes_everything_it_promises(finished):
    summary, out = finished["context"]
    for name in ("summary.json", "history.json", "tokenizer.json",
                 "agent.pkl", "trajectories.jsonl", "policy.txt"):
        assert (out / name).exists(), f"a finished run has no {name}"
    assert summary["steps"] == 0, \
        "an agent fits in one pass; a non-zero step count invites misreading"
    assert summary["final"], "no metrics"


def test_every_score_carries_its_floor(finished):
    """A score without a floor is not a result — the rule the model harness
    enforces, enforced here."""
    summary, _ = finished["context"]
    for env, metrics in summary["final"].items():
        assert "return_floor" in metrics, f"{env}: a return with no floor"
        assert "return_lift" in metrics, f"{env}: a return with no lift"
        assert metrics.get("floor_by"), f"{env}: the floor does not say what set it"


def test_the_floor_does_not_depend_on_the_agent(finished):
    """Two runs over the same episodes must agree on the floor exactly.

    A floor that moved with the agent being measured would make every lift in
    the table incomparable, and the movement would be invisible.
    """
    a, _ = finished["random"]
    b, _ = finished["context"]
    assert a["floors"] == b["floors"]


def test_reload_gives_back_a_working_agent(finished):
    _, out = finished["context"]
    agent, tok, cfg = load_run(out)
    from symbolic_ai_agents.train import load_data
    _, episodes = load_data(cfg)
    traj = rollout(build_env("choice"), agent, episodes[0], tok=tok)
    assert traj.moves and traj.moves[0].action in traj.moves[0].obs.actions


def test_trajectories_are_readable(finished):
    _, out = finished["context"]
    rows = read_trajectories(out / "trajectories.jsonl")
    assert rows, "a run wrote no trajectories to read"
    text = transcript(rows, limit=3)
    assert "did:" in text and "saw:" in text


def test_calibration_reads_the_same_moves_that_were_scored(finished):
    from symbolic_ai_agents.train import evaluate_agent, load_data, make_envs
    _, out = finished["context"]
    agent, tok, cfg = load_run(out)
    _, episodes = load_data(cfg)
    _, kept = evaluate_agent(agent, make_envs(cfg), episodes, tok, keep=64)
    report = calibrate_agent(kept["choice"])
    assert report.n == len(episodes), \
        "calibration counted a different number of decisions than were made"


def test_the_table_renders_and_warns_about_drift(finished, tmp_path):
    summaries = load_summaries([out for _, out in finished.values()])
    table = comparison_table(summaries)
    assert "lift" in table and "random" in table and "context" in table
    assert not config_drift(summaries), "identical configs reported as drifted"

    drifted = [dict(s) for s in summaries]
    drifted[0]["config"] = {**drifted[0]["config"], "probe_cost": 0.9}
    warning = config_drift(drifted)
    assert warning and any("probe_cost" in line for line in warning), \
        "a table mixing two probe costs did not say so"


def test_an_unknown_config_key_is_refused():
    with pytest.raises(ValueError, match="unknown config keys"):
        RunConfig.from_dict({"agent": "context", "learning_rate": 0.1})
