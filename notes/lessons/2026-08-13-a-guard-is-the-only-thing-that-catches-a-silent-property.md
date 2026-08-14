---
date: 2026-08-13
author: lead
status: measured
---

# Four failures, one shape: something was true of the repo that nothing would surface

None of these was a wrong number. Each was a *property* of the repository that no
test, no document and no amount of care would have revealed, because nothing was
looking.

| what was silently true | what it cost | the guard now |
|---|---|---|
| the tokenizer deleted `_` | 9/85 answers unreachable; `exact_match` pinned at 0 | pretokenizer is **total** (catch-all branch); tests assert on the alphabet, not a fixture |
| `runs/` was entirely gitignored | every number the docs cite died on a fresh clone | `summary.json` + `rules.txt` tracked — 556K against 732M |
| `symbolic_ai_agents` was **never on `master`** | 29 modules, half the repo, invisible for 94 commits | `tests/test_packages.py`: every package tracked, importable, in the README |
| the agents floor was a differently-fitted copy of its own baseline | the only positive number in the table | a policy that sets the floor must score **exactly zero** lift |

**Why documentation does not substitute.** The README described a five-package
repo while listing three, and passed review for 94 commits. `_vendor.py` recorded
`site-languages.db.gz` as "no Python in the package reads it" — the second half
true, the first false, and on that basis 58 languages were unreachable and *every
published number was measured on seven because a file was absent, not because
seven was the design*.

**Why the strongest existing guard was not enough.** The causality test — perturb
later tokens, earlier predictions must be bit-identical — is this repo's best
leak guard, and it **could not** have caught a graph-side leak, because the graph
does not move when tokens do. The guard that works is different in kind: adding
graph nodes labelled with symbols the text never contains must leave every logit
bit-identical.

**The rule:** when a failure turns out to have been invisible, do not resolve to
be more careful. Assert the property directly, in a test, and prefer the
assertion that would have failed *before* the fix.
