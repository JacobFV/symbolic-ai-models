"""Symbolic policies in text environments, on the same episodes the models use.

The interactive half of :mod:`symbolic_ai_models`. That package asks every
architecture two questions — the next token, a masked node — and scores each
against a hidden symbol given a perfect history. This one asks *policies* to act
in environments built from the very same ``langcurriculum`` episodes, where the
history is whatever the agent itself produced::

    choice   answer the curriculum's own question, once        (the control)
    retry    answer until right; paid 1/tries — the ranking, not the argmax
    repair   fill a term graph's hidden nodes one at a time; errors compound
    probe    the facts are redacted; pay to reveal them, then commit

``ROADMAP.md`` records the gap this closes: "prediction is a special case of
interaction ... this harness is teacher-forced scoring with no trajectories and
no reward, so it cannot reproduce those. That is a scope boundary worth stating
rather than quietly working around." This is the other side of that boundary,
and it is deliberately *not* a rewrite. The episodes, the vocabulary, the
shortcut floors, the calibrator and the masked graph view are all imported from
the model harness, and :mod:`symbolic_ai_agents.agents.wrapped` puts any
architecture from its registry into these environments directly — so the two
packages produce numbers that can be discussed in one paragraph.

Everything here is text-only and symbolic. There is no neural agent, by
construction rather than by omission: an agent in this package computes an
action rather than learning one, and a network that wants to act does so through
``wrap``.

    >>> import symbolic_ai_agents
    >>> cfg = symbolic_ai_agents.RunConfig(agent="context", lessons="unification",
    ...                                    envs=("choice", "repair"),
    ...                                    out="runs/agent-demo")
    >>> summary = symbolic_ai_agents.run(cfg)                 # doctest: +SKIP
"""

from __future__ import annotations

from .agents import (ABSTAIN, Agent, Decision, LearnContext, PolicyAgent,
                     agent_names, build as build_agent)
from .calibration import calibrate_agent
from .envs import (Environment, Move, Observation, Step, Trajectory, env_names,
                   build as build_env, rollout, rollouts)
from .train import (RunConfig, evaluate_agent, load_data, load_run, run,
                    save_agent)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    # environments
    "Environment", "Observation", "Step", "Move", "Trajectory",
    "build_env", "env_names", "rollout", "rollouts",
    # agents
    "Agent", "PolicyAgent", "Decision", "LearnContext", "ABSTAIN",
    "build_agent", "agent_names",
    # running
    "RunConfig", "run", "evaluate_agent", "load_run", "load_data", "save_agent",
    "calibrate_agent",
]
