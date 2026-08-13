---
date: 2026-08-13
author: agent-a8d3c1e7
status: measured
related: [2026-08-13-vendoring-the-generator-is-byte-identical]
---

# Vendor the generator verbatim, and check the corpus before touching the wiring

The fork taken while internalizing `langcurriculum` as `symbolic_ai_data/`, and
what was rejected.

## Decided

**1. Fingerprint first, wire second.** The checksum
(`symbolic_ai_models/data/fingerprint.py`) was recorded against the old git
dependency and *committed* before the seam moved, so the comparison could not be
adjusted after seeing the result. Three commits in order: record, vendor, switch.

**2. Copy byte for byte; substitute nothing.** Every internal import was already
relative so no rename was needed. Rejected: `sed s/langcurriculum/symbolic_ai_data/`,
which would have rewritten

```python
SPACE_KEY = b"langcurriculum/address/v1"     # address.py
```

— the domain separator for the Feistel permutation behind `draw` and `batch`.
Renaming it reshuffles every batch index, and the diff would have read as a
no-op. A test now pins the constant.

**3. Provenance in a module, not a README.** `symbolic_ai_data/_vendor.py` holds
the source URL, the pinned commit, the omitted files and the added ones as data,
so tests can assert against it. It is the only file in the package written here.

**4. Leave the 22 MB behind.** `site-languages.db.gz` is a website build
artefact. Verified before the decision, not after: no module mentions `gzip` or
the archive, and its uncompressed form was already absent from the installed
dependency, so the derived-grammar path was already inert when every published
episode was rendered. Rejected: vendoring it "to be safe", which would have put a
22 MB binary in git for a code path nothing runs.

**5. Do not redesign the API.** `lesson_ids`, `generate`, `Episode`, the
graph/term handoff and language rendering are unchanged. A rename or a cleanup is
a later, separate change, measured separately. Vendoring and refactoring in one
commit would have made "did the corpus move?" unanswerable.

## The rule this creates

Owning the generator means it can now be modified, and the repo's
new-model-beside-the-old rule applies to lessons and render modes **with more
force**: editing a model in place invalidates one row, editing generation in
place invalidates every row at once. Anything that varies surface realization
goes in as a new lesson or a new `Presentation` registered beside the existing
one — a new address, not a new rendering of an old one — and the fingerprint
stays green because it pins the default presentation, which is what every
published number was drawn from.

If the corpus is ever *meant* to change, the sequence is: change it, re-record
with `python -m symbolic_ai_models.data.fingerprint --write`, say so in a note,
and re-run everything downstream. The test's failure message says this, because
the tempting response to a red fingerprint is to re-record it and move on.
