"""A filed company name -> its canonical key. The low-context end of the curve.

The three real-data tasks so far all sit where the substrate is strong: the
answer lives in structure a model would have to be *given* — a route graph, an
ownership filing — and the advantage runs from 6,750x to 1.85e11 with the size
of that context.

This task is deliberately chosen from the other end. Normalising
``Chocoladefabriken Lindt & Spruengli AG/ADR`` to
``chocoladefabriken-lindt-spruengli-ag-adr`` needs **~10 tokens of context** and
a great deal of knowledge about how company names work — which suffix is legal
boilerplate and which is part of the name. That is the shape a language model is
good at and a rule is bad at, and every cost comparison in this repo so far has
*assumed* the two reach equal accuracy.

So the point of this task is to measure the assumption rather than make it. If a
careful symbolic rule cannot reach what a model would plainly reach here, the
advantage curve is not a curve in cost alone and the honest conclusion is a
threshold: below some context size, use the model.

Ground truth: 8,021 ``same_as`` bridges filed in the SEC EDGAR snapshot.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

__all__ = ["CompanyKeyTask", "load_task", "evaluate", "slugify",
           "predict_slug", "predict_stripped", "predict_interior",
           "fit_strip_set", "predict_fitted", "LEGAL_SUFFIXES"]

#: Legal-form boilerplate, most frequent first. Ordered so the floor sweep can
#: ask what the long tail is worth: the list is truncated to the first ``k``.
LEGAL_SUFFIXES: tuple[str, ...] = (
    "inc", "corp", "ltd", "co", "plc", "llc", "lp", "sa", "nv", "holdings",
    "incorporated", "corporation", "company", "limited", "group", "holding",
    "trust", "partners", "spa", "ab", "as", "oyj", "bv", "kk", "gmbh",
)


@dataclass(frozen=True)
class CompanyKeyTask:
    labels: Mapping[str, str]      #: entity id -> filed name
    truth: Mapping[str, str]       #: entity id -> canonical key

    @property
    def ids(self) -> tuple[str, ...]:
        return tuple(sorted(self.truth))


def load_task(base: Path) -> CompanyKeyTask:
    import pyarrow.parquet as pq

    labels, truth = {}, {}
    for f in sorted(base.rglob("cik_name*.parquet")):
        pf = pq.ParquetFile(f)
        if not {"id", "label", "same_as"} <= set(pf.schema_arrow.names):
            continue
        for batch in pf.iter_batches(columns=["id", "label", "same_as"]):
            for row in batch.to_pylist():
                if not row["same_as"]:
                    continue
                labels[row["id"]] = row["label"] or ""
                truth[row["id"]] = row["same_as"].rsplit(":", 1)[-1]
    return CompanyKeyTask(labels=labels, truth=truth)


def slugify(name: str) -> str:
    """Punctuation to spaces, lowercase, hyphen-joined.

    ``&`` becomes a separator rather than the word "and": the filed keys show
    ``Lindt & Spruengli`` as ``lindt-spruengli``, so expanding it would be a
    guess dressed as a normalisation.
    """
    return "-".join(re.sub(r"[^a-z0-9]+", " ", name.lower()).split())


def predict_slug(task: CompanyKeyTask) -> dict[str, str]:
    """The floor: slugify and strip nothing."""
    return {i: slugify(task.labels.get(i, "")) for i in task.ids}


def predict_stripped(task: CompanyKeyTask, *, k: int | None = None
                     ) -> dict[str, str]:
    """Slugify, then drop trailing legal-form tokens.

    Trailing only, and repeatedly: ``Murata Manufacturing Co., Ltd.`` needs two
    removals, and a rule that stripped the suffix set *anywhere* would turn
    ``Co-operative Bank`` into ``operative-bank``.
    """
    stops = set(LEGAL_SUFFIXES if k is None else LEGAL_SUFFIXES[:k])
    out = {}
    for i in task.ids:
        parts = slugify(task.labels.get(i, "")).split("-")
        while len(parts) > 1 and parts[-1] in stops:
            parts.pop()
        out[i] = "-".join(parts)
    return out


def evaluate(task: CompanyKeyTask, pred: Mapping[str, str]) -> float:
    ids = task.ids
    return sum(pred.get(i) == task.truth[i] for i in ids) / len(ids)


def predict_interior(task: CompanyKeyTask, *, k: int | None = None
                     ) -> dict[str, str]:
    """Drop legal-form tokens anywhere except the first position.

    The trailing-only rule leaves 68.9% of its residual on one pattern:
    ``WATERS CORP /DE/`` puts the legal form in the *middle*, before a state
    code, so nothing trailing matches. Stripping everywhere would destroy
    ``Co-operative Bank``; stripping everywhere **but the head** keeps the
    company's own name intact, since no filed name in this snapshot begins with
    its own legal form.

    This is the version to compare against a language model. Concluding "a rule
    cannot do this" from the weaker rule would have been a claim about my
    first attempt, not about rules.
    """
    stops = set(LEGAL_SUFFIXES if k is None else LEGAL_SUFFIXES[:k])
    out = {}
    for i in task.ids:
        parts = slugify(task.labels.get(i, "")).split("-")
        kept = [p for j, p in enumerate(parts) if j == 0 or p not in stops]
        out[i] = "-".join(kept) if kept else "-".join(parts)
    return out


def fit_strip_set(task: CompanyKeyTask, ids: Sequence[str], *,
                  min_count: int = 3, threshold: float = 0.5) -> frozenset[str]:
    """Learn which non-head tokens the canonical key drops.

    Written after two hand-authored suffix lists scored 0.8870 and 0.9479 and I
    was on the point of concluding that the residual needed world knowledge. It
    did not. Every token in this data is treated **perfectly consistently** —
    ``trust``, ``partners``, ``limited`` and ``sa`` are kept in 100% of cases,
    ``inc``, ``corp``, ``ltd``, ``group`` and ``holdings`` dropped in 100% — so
    the ceiling for a name-only method is 1.0 and my lists were simply wrong
    about four tokens.

    ``min_count`` is the guard that matters: a token seen twice and dropped
    twice is not evidence of a rule, and admitting it would fit the split.
    """
    kept: dict[str, int] = {}
    dropped: dict[str, int] = {}
    for i in ids:
        parts = slugify(task.labels.get(i, "")).split("-")
        gold = set(task.truth[i].split("-"))
        for j, tok in enumerate(parts):
            if j == 0:
                continue
            (kept if tok in gold else dropped)[tok] = \
                (kept if tok in gold else dropped).get(tok, 0) + 1
    out = set()
    for tok, d in dropped.items():
        n = d + kept.get(tok, 0)
        if n >= min_count and d / n > threshold:
            out.add(tok)
    return frozenset(out)


def predict_fitted(task: CompanyKeyTask, strip: frozenset[str],
                   ids: Sequence[str] | None = None) -> dict[str, str]:
    """The fitted rule, applied to whichever ids are asked for."""
    out = {}
    for i in (task.ids if ids is None else ids):
        parts = slugify(task.labels.get(i, "")).split("-")
        kept = [p for j, p in enumerate(parts) if j == 0 or p not in strip]
        out[i] = "-".join(kept) if kept else "-".join(parts)
    return out
