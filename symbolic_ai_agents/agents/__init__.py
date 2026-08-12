"""The policies under comparison — one interface, six mechanisms.

There is no neural family here. An agent in this package computes an action
rather than learning one, and the six differ in *what they compute from*::

    random      nothing                       chance, reproducibly
    shortcut    the shape of the options      the parameter-free cheats, ranked
    context     the shape of the situation    a lookup table — the model
                                              harness's own masked-node floor
    recall      its own rollouts              the return each action actually
                                              earned, credited Monte Carlo
    careful     the same table, plus doubt    buys information when unsure
    wrap        another package's model       any symbolic_ai_models
                                              architecture, asked to choose

The first three are also the :data:`~symbolic_ai_agents.envs.base.FLOOR_POLICIES`,
so each appears in the comparison table with zero lift on whichever environment
it is the strongest floor for. That is the table naming its own baseline rather
than a defect in it — the same way ``ngram`` is both a registered model and the
counting baseline the rest of the rule-based family has to beat.

The three that are not floors are each aimed at one thing the model harness
cannot ask. ``recall`` is fitted on reward instead of on labels. ``careful``
decides whether to find something out. ``wrap`` takes a model that was scored
under teacher forcing and puts it somewhere its own mistakes come back.

Importing this package registers everything, so ``agent_names()`` is complete
after ``import symbolic_ai_agents.agents``.
"""

from .base import (ABSTAIN, Agent, Decision, LearnContext, PolicyAgent,
                   Preference, training_views)
from .registry import REGISTRY, agent_names, build, get, register

# Registration happens at import; the noqa keeps a linter from tidying away the
# only thing these imports are for.
from . import careful, context, random_agent, recall, shortcut, wrapped  # noqa: F401

__all__ = ["Agent", "PolicyAgent", "Decision", "Preference", "ABSTAIN",
           "LearnContext", "training_views",
           "REGISTRY", "build", "get", "agent_names", "register"]
