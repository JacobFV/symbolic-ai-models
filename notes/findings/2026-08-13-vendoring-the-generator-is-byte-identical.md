---
date: 2026-08-13
author: agent-a8d3c1e7
status: measured
related: [2026-08-13-vendor-verbatim-rather-than-rename, 2026-08-13-the-renderer-is-deterministic]
---

# Vendoring the generator moved nothing, and here is the hash that says so

`symbolic_ai_data/` is `langcurriculum` copied byte for byte from commit
`504e1182`, the commit `uv.lock` pinned and therefore the one every number in
`RESEARCH_LOG.md`, `README.md` and `runs/*` was generated from.
`symbolic_ai_models.data.curriculum._lc()` now imports it; the git dependency is
gone.

## The slice: there isn't one

This is the **full** grid, not a sample.

| | |
|---|---:|
| lessons | 179 — every implemented one |
| seeds per lesson | 5 — three training, two in the eval range at 1,000,000 |
| languages | 7 — all the hand-written packs |
| digests compared | 1,432 |
| digests that differ | **0** |
| global digest, before the switch and after | `68be4d098db17e28` |

Two digests per lesson because they fail differently: the raw `structured()`
dict moves if the term changes at all, including in parts this repo's `Graph`
discards; the full `Episode` moves if either surface changes or if the handoff
between them does.

Eval seeds are in the grid deliberately. Nothing may be *tuned* against them,
and hashing is not tuning — a fingerprint covering only training seeds would
leave unprotected exactly the half of the corpus every published lift rests on.

## What would have refuted it

Any non-zero cell count. Written down before the switch: the fingerprint was
recorded against the old dependency, committed, and only then was the seam
moved. The comparison could not be tuned after the fact because the golden file
was already in git.

## The controls, and their weakness

Three, all designed by me, which is why this is worth a second reader:

1. **The digest notices.** `test_the_episode_digest_actually_covers_both_surfaces`
   perturbs the prompt by one space and one graph label by one character and
   asserts the digest moves. Without it, a fingerprint that hashed nothing would
   sit there green.
2. **It does not depend on hash randomisation.** Checked under `PYTHONHASHSEED=1`
   against `999`, in child processes, the same way the rule-based models are
   checked. A corpus checksum that flapped between processes would be worse than
   none: it would fail at random and be silenced.
3. **`compare` is tested against a bent copy of its own golden file**, so a
   failure reports the cells that moved rather than only "the curriculum
   changed".

## Why this was worth doing at all

A dataset here is a *cache* of `generate(lessons, n=, seed0=)` and the train/eval
split is a seed range, not a manifest. So there is no file on disk whose
checksum would have changed. A generator that rendered one word differently
would have produced a different corpus under the same seeds, re-based every
floor, and left the entire test suite green. This was the only silent
invalidation path in the repo and it is now closed.

Cost: about six seconds in `pytest`.

## The trap it nearly walked into

The obvious tidy-up is `sed s/langcurriculum/symbolic_ai_data/`. In
`address.py`:

```python
SPACE_KEY = b"langcurriculum/address/v1"
```

That is not a package name. It domain-separates the Feistel permutation behind
`draw` and `batch`, so renaming it reshuffles every batch index — and it would
have read as a no-op in review. As it turned out no substitution was needed
anywhere: every internal import is already relative. None was made, and
`test_vendored_generator.py` pins the constant.

**Correction to the commit message.** That commit says the old name "appears in
code exactly three times, all of them constants or docstrings", from a grep whose
filter was too narrow. Exactly three are *executable* — `SPACE_KEY`, the
argparse `prog=`, and the `--version` string, the last two cosmetic. The name
also appears in about seventy Sphinx cross-references in docstrings
(`:class:`~langcurriculum.grammar...``), which are now stale references to a
package this repo does not install. Harmless — nothing resolves them — but a
blanket rename would have been ~70 harmless edits carrying one catastrophic one,
which is exactly the ratio that gets a bad diff approved.

## What was left behind

22 MB of the 26 MB package: `site-languages.db.gz`, a build artefact for the
upstream website. Checked before deciding rather than after — no module mentions
`gzip` or the archive, and its uncompressed form was **already absent from the
installed dependency**, so `LanguageDB.exists()` was already `False` and the
several-hundred-language derived-grammar path was already inert when every
published episode was rendered. The seven hand-written packs did the rendering
and they are here. A test asserts all three facts, because the risk is a later
upstream sync bringing in code that reads what is no longer there.
