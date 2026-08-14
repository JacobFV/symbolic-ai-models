---
date: 2026-08-13
author: agent-typology-oracle
status: idea
related: [2026-08-13-typology-oracle-preregistration,
          2026-08-13-language-conditioning-recovers-typology-not-genealogy,
          2026-08-13-compositional-parser,
          2026-08-13-is-the-chinese-score-grammar-or-a-fingerprint]
---

# The corpus is 42 languages wide now, and several parked questions are suddenly cheap

`symbolic_ai_core/data/langdb.py` makes every ISO code in `site-languages.db`
renderable — 58 languages, 46 WALS-coded, 12 scripts — at about 0.2 s per
(language, 179 lessons, one seed). The graph stays byte-identical across all of
them, so this is an exact parallel corpus 42 languages wide rather than a bigger
one. Things that were "not worth building for seven packs, five of which are
European or English twice":

- **The cross-language parser table.** `RESEARCH_LOG.md` reports `cky-001`
  keeping 0.06 of its English bracket F1 in Chinese and `template-002` keeping
  0.46, on four languages. With 42 the same table becomes a *curve* against
  script, morphological richness and word order, and the standing claim —
  "script and tokenisation dominate the language axis, not grammar versus
  vocabulary" — becomes something with error bars.
- **The held-out-language test the routing note asks for.** "An eighth language,
  never seen: can the system notice it is new and bootstrap a parser from the
  shared grammar plus a small lexicon?" There are now 41 held-out languages, and
  leave-one-language-out is a real protocol rather than an anecdote.
- **Grammar alignment across languages.** Induce a grammar per language on the
  same terms and ask whether there is a bijection on nonterminals under which
  the production sets agree. At 42 languages the control is no longer "shuffle
  the one family we have".
- **`language_id_head.py` at 42 classes.** 0.8388 against a 0.1429 floor was
  measured on seven packs where two render byte-identically. A 42-way version
  with 12 scripts prices the oracle far more honestly, and the script-blind
  version of it is the interesting one.
- **Whether the layout fingerprint survives.** "Is `template-002`'s Chinese
  score grammar or is it punctuation?" — 42 languages give 12 scripts and
  several punctuation conventions to separate those with, instead of one.

**The caveat that has to travel with all of it.** These are tier-2 and tier-3
languages: WALS-derived word order, a Wiktionary lexicon, UniMorph morphology
only where it exists. Nobody has read them. A Vietnamese episode still contains
English content words. They are good enough to be a *structured perturbation* of
the same corpus and are not good enough to be quoted as a presentation of the
language.
