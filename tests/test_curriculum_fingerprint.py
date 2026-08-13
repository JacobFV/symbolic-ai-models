"""The corpus has a checksum now, and this is where it is checked.

Nothing else in this repo can notice that generation moved. There is no dataset
file to diff — a "dataset" here is a cache of ``generate(lessons, n=, seed0=)``,
and the train/eval split is a seed range rather than a manifest. So a generator
that renders one word differently produces a different corpus under the same
seeds, every published lift is then measured against a different floor on
different episodes, and every test in the suite still passes.

These tests are the only thing standing between that and a silent invalidation
of ``RESEARCH_LOG.md``, ``README.md`` and ``runs/*``.
"""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from symbolic_ai_core.data import curriculum as C
from symbolic_ai_core.data import fingerprint as F


@pytest.fixture(scope="module")
def golden():
    return F.load_golden()


def test_the_curriculum_still_hashes_to_what_the_published_runs_used(golden):
    """The invariant. If this fails, the generator moved.

    It was recorded against the ``langcurriculum`` git dependency at the commit
    every number in the repo was produced from, and re-checked after that
    generator was vendored into ``symbolic_ai_data``. A failure here is not a
    broken test: it means the episodes behind the published numbers can no
    longer be reproduced, and the numbers have to be re-run or withdrawn.
    """
    got = F.curriculum_fingerprint()
    problems = F.compare(golden, got)
    assert not problems, (
        f"{len(problems)} cells of the curriculum moved. The first few:\n  "
        + "\n  ".join(problems[:10])
        + "\n\nThis invalidates every published number unless the change was "
          "intended, in which case re-record with "
          "`python -m symbolic_ai_core.data.fingerprint --write` and say so "
          "in RESEARCH_LOG.md.")
    assert got["global"] == golden["global"]


def test_the_grid_is_wide_enough_to_be_worth_trusting(golden):
    """A fingerprint over three lessons in English would pass through almost
    any change worth catching. Pin the coverage, not just the digests."""
    assert golden["n_lessons"] == len(C.lesson_ids()) >= 179
    assert len(golden["languages"]) >= 5
    assert "chinese" in golden["languages"] and "turkish" in golden["languages"]
    # Both seed ranges: training seeds start at 0 and evaluation at 1,000,000,
    # and the published numbers come from the second.
    assert min(golden["seeds"]) == 0
    assert max(golden["seeds"]) >= 1_000_000
    assert len(golden["seeds"]) >= 3


def test_generation_does_not_depend_on_hash_randomisation():
    """Sets and frozensets iterate in a per-process order. A generator that let
    one reach the surface would be reproducible in any single test run and
    different between them — the exact failure mode ``RESEARCH_LOG.md`` records
    for the rule-based models. Checked the same way: two child processes with
    different ``PYTHONHASHSEED``.
    """
    import os

    code = ("import json,sys;"
            "from symbolic_ai_core.data import fingerprint as F;"
            "print(F.curriculum_fingerprint("
            "lessons=sorted(F.C.lesson_ids())[:12])['global'])")
    out = []
    for seed in ("1", "999"):
        env = dict(os.environ, PYTHONHASHSEED=seed)
        r = subprocess.run([sys.executable, "-c", code], capture_output=True,
                           text=True, env=env, timeout=600)
        assert r.returncode == 0, r.stderr[-2000:]
        out.append(r.stdout.strip())
    assert out[0] == out[1], f"generation is process-dependent: {out}"


def test_the_episode_digest_actually_covers_both_surfaces():
    """A fingerprint that only hashed the prompt would sit there looking green
    while the term graph drifted. Perturb each surface in turn and check the
    digest notices — otherwise this whole file is decoration."""
    eps = list(C.generate(["symbol_grounding"], n=1, seed0=0))
    base = F._digest([F._canon(eps[0].to_dict())])

    moved_text = C.Episode(**{**eps[0].to_dict(), "graph": eps[0].graph,
                              "prompt": eps[0].prompt + " "})
    moved_graph = C.Episode.from_dict(eps[0].to_dict())
    moved_graph.graph.labels[-1] = moved_graph.graph.labels[-1] + "x"

    assert F._digest([F._canon(moved_text.to_dict())]) != base
    assert F._digest([F._canon(moved_graph.to_dict())]) != base


def test_the_recorded_file_is_the_shape_the_checker_expects(golden):
    """`compare` is the thing a future failure will be read through, so it gets
    a test of its own rather than being trusted."""
    assert F.compare(golden, golden) == []
    bent = json.loads(json.dumps(golden))
    lid = sorted(bent["lessons"])[0]
    bent["lessons"][lid]["raw"] = "0" * 16
    lang = sorted(bent["lessons"][lid]["text"])[0]
    bent["lessons"][lid]["text"][lang] = "0" * 16
    problems = F.compare(bent, golden)
    assert len(problems) == 2
    assert any("term graph" in p for p in problems)
    assert any(f"[{lang}]" in p for p in problems)
