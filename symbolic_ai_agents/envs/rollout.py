"""Running an agent in an environment, and nothing else.

One loop, every agent, every environment — the counterpart of
:func:`symbolic_ai_models.train.evaluate_model`, and kept just as plain for the
same reason. The loop is a control: every agent gets the same observations in
the same order under the same horizon, so a difference in the numbers is a
difference between the agents.

The one judgement in here is what happens when an agent runs out of horizon
without committing. It is scored as an unsolved episode rather than skipped.
Skipping would let an agent improve its average by declining the hard episodes,
which is the oldest way there is to produce a good-looking table.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from symbolic_ai_models.data.curriculum import Episode
from symbolic_ai_models.data.tokenizer import SymbolTokenizer

from .base import Environment, Move, Totals, Trajectory

__all__ = ["rollout", "rollouts", "Rollouts"]


def rollout(env: Environment, agent, ep: Episode, *,
            tok: SymbolTokenizer) -> Trajectory:
    """One episode, from ``reset`` to ``done`` or to the horizon."""
    obs = env.reset(ep, tok=tok)
    traj = Trajectory(env=env.name, lesson_id=ep.lesson_id,
                      instance_id=ep.instance_id)
    agent.begin(env, obs)
    for _ in range(max(env.horizon, 1)):
        decision = agent.act(obs)
        step = env.step(decision.action)
        move = Move(obs=obs, action=decision.action,
                    confidence=float(decision.confidence), step=step)
        agent.observe(move)
        traj.moves.append(move)
        if step.done or step.next_obs is None:
            break
        obs = step.next_obs
    return traj


@dataclass
class Rollouts:
    """Every trajectory, plus the counts they sum to."""

    env: str
    trajectories: list[Trajectory] = field(default_factory=list)
    totals: Totals = field(default_factory=Totals)

    #: How many episodes were run, which is not ``len(self.trajectories)``
    #: whenever ``keep`` capped what was retained.
    n_episodes: int = 0

    def __len__(self) -> int:
        return len(self.trajectories)


def rollouts(env: Environment, agent, episodes: Iterable[Episode], *,
             tok: SymbolTokenizer, keep: int | None = None) -> Rollouts:
    """Run every episode. ``keep`` caps how many trajectories are retained.

    The counts are always complete; only the stored trajectories are capped,
    because a full sweep over 179 lessons holds tens of thousands of them and
    the only thing they are needed for afterwards is reading a sample.
    """
    out = Rollouts(env=env.name)
    for ep in episodes:
        traj = rollout(env, agent, ep, tok=tok)
        out.totals.add(traj.counts())
        out.n_episodes += 1
        if keep is None or len(out.trajectories) < keep:
            out.trajectories.append(traj)
    return out


def episode_returns(rolls: Rollouts) -> list[float]:
    """Per-episode return, for anything that wants the distribution rather than
    the mean — a macro-average over a bimodal set describes neither mode, which
    :class:`symbolic_ai_models.agent.CurriculumReport` makes the case for at
    length."""
    return [t.total_reward for t in rolls.trajectories]
