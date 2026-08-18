"""Tasks over bytes this repo did not author.

Distinct from :mod:`symbolic_ai_generators`, where the world is constructed and
the difficulty is a parameter I chose. Here the difficulty is whatever it is,
the ground truth was authored by strangers, and a wrong answer is possible —
which is the property the generated tasks structurally cannot have and the
reason ``$ / solved episode above floor`` had nothing to bite on until now.
"""

from __future__ import annotations

from .airport_country import (FLOOR_NAME, AirportCountryTask, evaluate,
                              load_task, predict_anchor, predict_knn,
                              predict_modal)

from .company_key import CompanyKeyTask
from .cross_source_alignment import AlignmentResult, Candidate
from .range_limited_routing import RangeNetwork
from .ultimate_parent import UltimateParentTask

__all__ = ["AirportCountryTask", "load_task", "evaluate", "predict_knn",
           "predict_modal", "predict_anchor", "FLOOR_NAME",
           "UltimateParentTask", "CompanyKeyTask", "AlignmentResult",
           "Candidate", "RangeNetwork"]
