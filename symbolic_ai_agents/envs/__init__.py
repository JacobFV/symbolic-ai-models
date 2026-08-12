"""The environments under comparison — four presentations of one episode.

Every one of them is built from the same ``langcurriculum`` episode the model
harness trains on, so a difference between two rows of a comparison table is a
difference in what was *asked*, not in what was drawn::

    choice   answer the curriculum's own question, once        (the control)
    retry    answer until right; paid 1/tries — the ranking, not the argmax
    repair   fill a term graph's hidden nodes one at a time; errors compound
    probe    the facts are redacted; pay to reveal them, then commit

``choice`` is the control on purpose. It is the only one with no interaction in
it, it is exactly what :func:`symbolic_ai_models.agent.evaluate_choices` scores a
trained model on, and any claim that one of the other three measures something
new has to survive being put next to it.

Read them in that order and they take one thing away at a time: ``choice`` gives
a perfect history and one commitment, ``retry`` asks about the rest of the
ranking, ``repair`` removes the perfect history, ``probe`` removes the facts
themselves and charges for them.

Importing this package registers everything, so ``env_names()`` is complete
after ``import symbolic_ai_agents.envs``.
"""

from .base import (Environment, Move, Observation, Step, Totals, Trajectory,
                   FLOOR_POLICIES, lift, reference_floor, summarize)
from .registry import REGISTRY, build, env_names, get, register
from .rollout import Rollouts, rollout, rollouts

# Registration happens at import; the noqa keeps a linter from tidying away the
# only thing these imports are for.
from . import choice, probe, repair, retry  # noqa: F401

__all__ = ["Environment", "Observation", "Step", "Move", "Trajectory", "Totals",
           "lift", "summarize", "reference_floor", "FLOOR_POLICIES",
           "REGISTRY", "build", "get", "env_names", "register",
           "rollout", "rollouts", "Rollouts"]
