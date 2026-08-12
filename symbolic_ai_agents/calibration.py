"""Does an agent's confidence mean anything?

The same question :mod:`symbolic_ai_models.calibration` asks of a model, asked of
a policy — and the machinery is imported from there rather than rebuilt, so the
two answers are computed the same way and can be put in one sentence.

What differs is what is being measured. A model's stated confidence is the
probability its output distribution puts on its own top symbol. An agent's is
the probability its *mixture* puts on the action it took, which is a
statement about a decision rather than about a token, and it is the number a
caller would act on: an agent that says 0.9 and is right half the time is not
merely wrong, it is wrong in a way nothing downstream can notice.

There is a second reason to care here that the model harness does not have.
:mod:`symbolic_ai_agents.agents.careful` *uses* its own confidence — it probes
when the number is low — so a miscalibrated agent does not merely mislead a
reader, it acts wrongly. Its threshold is fitted against the same quantity this
module measures, which is what makes the two consistent.

Only committing moves are scored. A probe is neither right nor wrong, so
including it would dilute the buckets with steps that have no outcome.
"""

from __future__ import annotations

from typing import Iterable, Sequence

import numpy as np

from symbolic_ai_models.calibration import CalibrationReport, calibrate

from .envs.base import Trajectory

__all__ = ["calibrate_agent", "confidence_outcomes"]


def confidence_outcomes(trajectories: Iterable[Trajectory]
                        ) -> tuple[np.ndarray, np.ndarray]:
    """``(stated confidence, was it right)`` over every committing move."""
    confidence: list[float] = []
    correct: list[float] = []
    for traj in trajectories:
        for move in traj.moves:
            if move.step.correct is None:
                continue                    # a probe: no outcome to compare to
            confidence.append(float(move.confidence))
            correct.append(float(move.step.correct))
    return (np.asarray(confidence, dtype=np.float64),
            np.asarray(correct, dtype=np.float64))


def calibrate_agent(trajectories: Sequence[Trajectory],
                    n_bins: int = 10) -> CalibrationReport:
    """Bucket the agent's stated confidence; compare each bucket to what happened.

    Read straight off the trajectories the run already produced, so this cannot
    disagree with the headline numbers: the moves counted here are the moves
    that were scored, not a separately drawn sample that might differ.
    """
    confidence, correct = confidence_outcomes(trajectories)
    return calibrate(confidence, correct, n_bins=n_bins)
