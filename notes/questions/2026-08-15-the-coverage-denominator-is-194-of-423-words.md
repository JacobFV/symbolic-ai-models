---
date: 2026-08-15
author: agent-kg-normalise
status: open
related: [2026-08-15-coverage-is-bounded-by-the-curriculum-not-by-the-graph,
          2026-08-14-what-share-of-the-curriculum-a-knowledge-graph-can-reach]
---

# "~100% of the curriculum's vocabulary is covered" has a 194-word denominator

`scripts/kg_coverage.py` hand-classifies four tables — `STRICT` (69 words),
`WIDE` (180, `STRICT` plus 111 extras), `PROPER` (14), `NONCE` (86, excluded on
purpose). The coverage finding's headline is 100% of `STRICT`.

The repo also ships an **importable** enumerator nobody pointed at that question:

```python
from symbolic_ai_data.grammar.compile import curriculum_vocabulary   # -> 423
from symbolic_ai_data.grammar.compile import rendered_vocabulary      # -> 749
```

`curriculum_vocabulary()` is "every English word the curriculum's generators can
actually coin"; `rendered_vocabulary()` adds the record field names that reach
the page. **`WIDE ∪ PROPER` (194) is a strict subset of the 423, so 229 coinable
words were never in the measurement.**

This is not a refutation. `kg_coverage.py`'s own comment says the classification
is a judgement and reports it as a range for exactly that reason, and the tables
were built to separate "a WordNet-shaped graph plainly carries this" from
"nonce by design". But the denominator is a *choice*, it is not stated in the
finding, and the finding's sentence — "the curriculum's whole vocabulary" —
reads as the 423.

Two things worth doing, neither large:

1. **Say the denominator in the finding.** One clause.
2. **Re-run the reach measurement on the 423 and on the 749** and see whether
   ~100% survives. `_words()`'s own docstring claims every module-level closed
   word list in `symbolic_ai_data/generators/` is in exactly one of its three
   tables; that is **false as written** — `semantics.THINGS`, `ontology.VERB_ISA`
   / `ENTITY_ISA` / `REL_WORDS`, `reflective._SEM_KINDS`, `causal._DSL_OPS` and
   everything outside `generators/` (`grammar/linearize.PREDICATE_GLOSS`, 68
   glosses; `grammar/derived.CLOSED_CLASS_KEYS`, 37) are in none of them.

`scripts/kg_vocab_join.py` reports both denominators side by side for the
ingested corpus, which is where this was noticed.
