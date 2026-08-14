"""The policies under comparison — one interface, seven mechanisms.

There is no neural family here. An agent in this package computes an action
rather than learning one, and the seven differ in *what they compute from*::

    random      nothing                       chance, reproducibly
    shortcut    the shape of the options      the parameter-free cheats, ranked
    context     the shape of the situation    a lookup table — the model
                                              harness's own masked-node floor
    recall      its own rollouts              the return each action actually
                                              earned, credited Monte Carlo
    careful     the same table, plus doubt    buys information when unsure
    wrap        another package's model       any symbolic_ai_models
                                              architecture, read as text
    graphread   the same model's graph head   the same architecture, read
                                              through the `action` readout

The first three are also the :data:`~symbolic_ai_agents.envs.base.FLOOR_POLICIES`,
so each appears in the comparison table with zero lift on whichever environment
it is the strongest floor for. That is the table naming its own baseline rather
than a defect in it — the same way ``ngram`` is both a registered model and the
counting baseline the rest of the rule-based family has to beat.

The four that are not floors are each aimed at one thing the model harness
cannot ask. ``recall`` is fitted on reward instead of on labels. ``careful``
decides whether to find something out. ``wrap`` takes a model that was scored
under teacher forcing and puts it somewhere its own mistakes come back.

``graphread`` is ``wrap`` with one thing changed, and is registered beside it
rather than replacing it for exactly that reason: the two rows share a model, a
prior, a calibrator and a set of environments, and differ only in **what the
model's output is read as**. ``wrap`` scores the rendered s-expression as text;
``graphread`` reads the graph emission through
:class:`symbolic_ai_agents.readouts.action.ActionReadout`. The gap between the
two columns is therefore a measurement of the readout, which is what the
``wrap`` docstring's admission that "the graph head is not used" had made
impossible to take.

Importing this package registers everything, so ``agent_names()`` is complete
after ``import symbolic_ai_agents.agents``.
"""

from .base import (ABSTAIN, Agent, Decision, LearnContext, PolicyAgent,
                   Preference, training_views)
from .registry import REGISTRY, agent_names, build, get, register

# Registration happens at import; the noqa keeps a linter from tidying away the
# only thing these imports are for.
from . import (careful, context, graphread, random_agent, recall,  # noqa: F401
               shortcut, wrapped)

__all__ = ["Agent", "PolicyAgent", "Decision", "Preference", "ABSTAIN",
           "LearnContext", "training_views",
           "REGISTRY", "build", "get", "agent_names", "register"]
