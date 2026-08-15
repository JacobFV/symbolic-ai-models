"""Check our atomspace against the real one — out of band, never a dependency.

``hyperon`` publishes no wheel for this project's Python 3.13, and more to the
point ``APPROACH.md``'s whole premise is a CPU cost budget that a C extension
inside a 179-lesson sweep would break. So the real system is an **outside
conformance oracle**: this script writes our spaces out as MeTTa source, runs
the same queries under a real hyperon in *its own* interpreter, and asserts the
two agree. It is run by hand, it is not imported by anything, and it skips
cleanly when hyperon is absent.

That is the ``symbolic_ai_data`` pattern — vendored verbatim, byte-identical
test — and the WALS pattern — an oracle nobody here wrote — and both have
already worked here.

Why an oracle is worth having at all
-------------------------------------
Every property this repo asserts about the ``005`` encoding is asserted by code
this repo also wrote. ``notes/lessons/2026-08-13-a-control-that-could-fail.md``
is explicit that author-designed controls can be constructed to pass, and a
pattern matcher agreeing with its own test suite is exactly that shape. An
independent implementation of MeTTa disagreeing is the one signal that cannot
come from our own assumptions.

What is compared, and what deliberately is not
------------------------------------------------
Compared: for a sample of real curriculum graphs, the **set of bindings** each
of a fixed list of queries returns. That is the operation the models use and
nothing else.

Not compared: evaluation semantics. Our ``(= lhs rhs)`` only ever *adds* ``lhs``
when ``rhs`` is satisfied, where real MeTTa's ``=`` is also the function
definition form and the interpreter reduces on evaluation. The subset's
omissions are listed in ``symbolic_ai_atomspace/metta.py``; an oracle that
compared semantics we never claimed to implement would fail for the right reason
and tell us nothing.

Usage, in its own interpreter::

    python3.12 -m venv /tmp/hyperon-env
    /tmp/hyperon-env/bin/pip install hyperon
    uv run python scripts/metta_hyperon_oracle.py --emit /tmp/oracle
    /tmp/hyperon-env/bin/python scripts/metta_hyperon_oracle.py --check /tmp/oracle
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

#: The queries the oracle runs. Deliberately the ones the role schedule uses,
#: plus the derived-sibling rule, because those are what a wrong answer would
#: actually corrupt.
QUERIES = (
    "(child $p $k $q)",
    "(: $q pred)",
    "(label $q $s)",
    "(root $q)",
)


def emit(dest: Path, n_lessons: int, seeds: int) -> int:
    """Write MeTTa source plus *our* answers, for the oracle to disagree with."""
    from symbolic_ai_atomspace import (AtomSpace, graph_to_atomspace,
                                       parse_atom, print_atom)
    from symbolic_ai_core.data import curriculum as C

    dest.mkdir(parents=True, exist_ok=True)
    lessons = C.lesson_ids()[:n_lessons]
    cases = []
    for k, ep in enumerate(C.generate(lessons, n=seeds, seed0=0,
                                      on_error="skip")):
        space = graph_to_atomspace(ep.graph)
        source = space.to_metta()
        (dest / f"case{k:04d}.metta").write_text(source, encoding="utf-8")
        # Round-trip our own source before recording an answer against it: an
        # oracle fed source we cannot read back ourselves would be testing the
        # printer, and the printer already has its own test.
        assert AtomSpace.from_metta(source) == space, ep.lesson_id
        answers = {}
        for q in QUERIES:
            found = space.query(parse_atom(q))
            answers[q] = sorted(
                " ".join(f"{name}={print_atom(atom)}"
                         for name, atom in sorted(b.items()))
                for b in found)
        cases.append({"file": f"case{k:04d}.metta", "lesson": ep.lesson_id,
                      "seed": ep.seed, "atoms": len(space), "answers": answers})
    (dest / "cases.json").write_text(json.dumps(cases, indent=1),
                                     encoding="utf-8")
    print(f"wrote {len(cases)} cases to {dest}")
    return 0


def check(src: Path, selftest: bool = False) -> int:
    """Run the same queries under a real hyperon and compare. Skips if absent.

    ``selftest`` deletes one binding from one recorded answer before comparing.
    A conformance check that cannot fail is not a check —
    ``notes/lessons/2026-08-13-a-control-that-could-fail.md`` — and this one has
    an obvious way of passing vacuously: if hyperon returned nothing for every
    query and we had recorded nothing, the counts would agree perfectly. So the
    run prints the binding counts it compared, and ``--check --selftest`` must
    exit non-zero.
    """
    try:
        from hyperon import MeTTa                             # type: ignore
    except ImportError:
        print("hyperon is not installed in this interpreter -- skipped.\n"
              "That is the designed behaviour, not a failure: the oracle is out "
              "of band and never a dependency. See the module docstring for how "
              "to build its environment.")
        return 0

    cases = json.loads((src / "cases.json").read_text())
    bad = compared = 0
    for k, case in enumerate(cases):
        source = (src / case["file"]).read_text(encoding="utf-8")
        runner = MeTTa()
        runner.run("!(bind! &kb (new-space))")
        for line in source.splitlines():
            if line.strip():
                runner.run(f"!(add-atom &kb {line})")
        for query, ours in case["answers"].items():
            if selftest and k == 0 and ours:
                ours = ours[:-1]                              # must now disagree
            got = runner.run(f"!(match &kb {query} {query})")
            theirs = sorted(str(a) for a in (got[0] if got else []))
            compared += len(theirs)
            if len(theirs) != len(ours):
                bad += 1
                print(f"{case['lesson']} seed={case['seed']} {query}: "
                      f"ours {len(ours)} bindings, hyperon {len(theirs)}")
    print(f"{len(cases)} cases, {compared} bindings compared, "
          f"{bad} disagreements")
    if not compared:
        print("NOTHING WAS COMPARED -- this run proves nothing")
        return 1
    return 1 if bad else 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--emit", type=Path, help="write cases here (our side)")
    ap.add_argument("--check", type=Path, help="read cases and run hyperon")
    ap.add_argument("--lessons", type=int, default=12)
    ap.add_argument("--seeds", type=int, default=1)
    ap.add_argument("--selftest", action="store_true",
                    help="corrupt one answer; the check must then fail")
    args = ap.parse_args(argv)
    if args.emit:
        return emit(args.emit, args.lessons, args.seeds)
    if args.check:
        return check(args.check, args.selftest)
    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
