"""Datalog: relational closure and incremental maintenance over a world.

Tier 1 of the kernel stack and the workhorse. See
``notes/decisions/2026-08-18-the-kernel-stack-is-a-set-of-projections.md``.
"""

from __future__ import annotations

from .engine import (Atom, Fact, Literal, Program, Rule, StratificationError,
                     Var, add_facts_report, evaluate, query, strata)
from .kernel import DATALOG, DatalogKernel
from .project import project_world, rule_from_dict, rules_from_world

__all__ = ["Atom", "Fact", "Literal", "Program", "Rule", "StratificationError",
           "Var", "add_facts_report", "evaluate", "query", "strata",
           "DATALOG", "DatalogKernel", "project_world", "rule_from_dict",
           "rules_from_world"]
