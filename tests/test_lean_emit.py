"""The outside conformance oracle — and an honest statement that it is unrun.

There is no ``lean`` or ``elan`` on this machine, so the conformance assertion
skips. What does not skip is the shape of the emitted source, because an
emitter that has only ever been read is worth what this repo's author-designed
controls have been worth: ``notes/lessons/2026-08-13-a-control-that-could-fail.md``
rule 4.

The skipped test is deliberately left in place rather than deleted. Its presence
is the record that the claim "our kernel agrees with Lean" has **not** been
checked, which is a different and more useful thing than the claim's absence.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from symbolic_ai_core.data.curriculum import generate, lesson_ids
from symbolic_ai_lean.emit import lean_ident, lean_source


@pytest.fixture(scope="module")
def episodes():
    return list(generate(lesson_ids()[:12], n=1, seed0=500))


def test_it_emits_a_signature_for_every_lesson_it_is_given(episodes):
    for ep in episodes:
        src = lean_source(ep.graph, name=ep.lesson_id)
        assert "namespace SymbolicAI" in src
        assert src.rstrip().endswith("end SymbolicAI")
        assert "axiom" in src


def test_every_symbol_reaches_the_source(episodes):
    from symbolic_ai_lean.elaborate import elaborate
    for ep in episodes[:4]:
        elab = elaborate(ep.graph, [], mode="open")
        src = lean_source(ep.graph, name=ep.lesson_id)
        for sym in elab.decl:
            assert lean_ident(sym) in src, sym


def test_an_awkward_label_is_quoted_rather_than_mangled():
    assert lean_ident("a b") == "«a b»"
    assert lean_ident("_") == "«_»"
    assert lean_ident("λ") == "«λ»"


def test_the_emitter_is_not_reachable_from_the_gate():
    """`notes/decisions/2026-08-14-the-ir-is-a-knob.md`: no external toolchain in
    the hot path, ever. This asserts the import graph rather than the intention."""
    import symbolic_ai_lean.gate as gate
    src = Path(gate.__file__).read_text()
    assert "emit" not in src.replace("emitted", "").replace("emits", "")


@pytest.mark.skipif(shutil.which("lean") is None,
                    reason="no Lean 4 toolchain on this machine; the oracle is "
                           "out of band by design and has never been run here")
def test_real_lean_accepts_what_our_kernel_produced(episodes):   # pragma: no cover
    for ep in episodes[:3]:
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "Episode.lean"
            path.write_text(lean_source(ep.graph, name=ep.lesson_id))
            out = subprocess.run(["lean", str(path)], capture_output=True,
                                 text=True, timeout=120)
            assert out.returncode == 0, out.stderr
