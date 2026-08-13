---
date: 2026-08-13
author: agent-a11dfe7b
status: idea
related: [2026-08-13-core-owns-the-types-data-stays-vendored, 2026-08-13-split-symbolic-ai-core]
---

# What the `symbolic_ai_core` split deliberately left alone

Parked, not judged. Each was out of scope for a behaviour-preserving refactor
because it is an API change or a redesign, and none is urgent.

**`invariance.__all__` omits `label_accuracy`.** It always has, while `train.py`
and three test files import it, so the deprecation shim has to name it by hand.
One-line fix, but adding a name changes what `import *` means, so it wants its
own commit.

**`report.py` is still two things.** Its comparison table has model-specific
columns — which is why it stayed — but the table-rendering and summary-loading
underneath is generic, and `symbolic_ai_parsers` has its own separate table
code. Worth asking whether the *renderer* belongs in core with the columns left
behind, or whether two small table functions are cheaper than one shared one.

**Two packages are called "parsers".** `symbolic_ai_models/parsers/` produces a
`ParseResult` and is scored by pairwise class agreement; `symbolic_ai_parsers/`
produces a `Graph`. Both docstrings work hard to explain that they are not the
same thing, which is a sign the names are wrong rather than a sign the
explanation is needed. Renaming either invalidates no numbers — nothing is
registered across them — so this is cheap whenever someone is annoyed enough.

**The deprecation shims have no expiry.** They exist for `symbolic_ai_agents` on
the `omegaclaw` branch. Once that branch merges and its imports are updated, the
shims in `symbolic_ai_models/` (`data/`, `calibration.py`, `invariance.py`,
`shortcuts.py`, `asymptotics.py`) are dead weight and should go in one commit.
`tests/test_layering.py::MOVED` is the list to delete them from.
