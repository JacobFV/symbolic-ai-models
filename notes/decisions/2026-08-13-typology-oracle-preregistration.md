---
date: 2026-08-13
author: agent-typology-oracle
status: provisional
related: [2026-08-13-language-conditioning-preregistration,
          2026-08-13-language-conditioning-recovers-typology-not-genealogy,
          2026-08-13-language-id-above-the-parser,
          2026-08-13-selective-rule-application-by-language]
---

# Grading the induced language representation against an oracle we did not write

Written before the language database was wired up, before any distance matrix
existed, and before any correlation was computed. Everything below is a
commitment, including the parts I expect to lose.

## Why this experiment, and why now

Every number this repo has published is scored against a floor **we wrote**.
The one result that graded a learned representation against an external
structure — `notes/findings/2026-08-13-language-conditioning-recovers-typology-not-genealogy.md`
— had to grade it against a four-point genealogy hand-typed into
`scripts/language_clustering.py`, and reported "10th of 20 triples" because
that is the strongest statement four data points support.

There is a real oracle on this machine:
`/home/brandonin/Documents/formal-language-cirriculum/.build/site-languages.db`,
58 languages, 640 rows of WALS typological coding over 18 parameters, plus
`family`, `macroarea`, `script` and `glottocode` per language. **46 languages
carry WALS features — 1,035 pairs.** WALS is coded by the linguists who study
these languages and none of it was written for this repo.

## The circularity, stated first because it decides how everything is read

`symbolic_ai_data/grammar/typology.py::derive_profile` **builds each derived
grammar's word order from WALS**. A language rendered by `DerivedGrammar` is a
deterministic function of its WALS row. So:

> Any representation that recovers word order from derived-language prose
> recovers WALS **by construction**, and a correlation with the WALS features
> the renderer reads is not evidence about linguistics.

This is not a reason to abandon the oracle. It is a reason to split it. From
`derive_profile`, the features it **reads** are

    81A 87A 88A 89A 85A 86A 93A 98A 30A 37A 38A 55A 143A   (+51A, recorded)

and the features present in the database that it **never reads** are

    26A 33A 49A 92A

So two typological distances get reported, never one:

| distance | built from | what a correlation means |
|---|---|---|
| `T_read` | the 13 features the renderer consumes | an upper bound / positive control. A representation that cannot recover *these* cannot recover anything. |
| `T_heldout` | 26A, 33A, 49A, 92A — never read by the renderer | **the honest test.** These reach the prose only through cross-linguistic covariation among WALS features, not through the generator. |

`family` (genealogy), `macroarea` (geography) and `glottocode` are likewise
never read by the renderer. `script` **is** read — `Typography` takes
`word_joiner`, `capitalizes` and `rtl` from it — so script is a *read* variable
and is the confound this whole note is about.

## Hypotheses, with refutation conditions

Induced distance `D` is the pairwise Euclidean distance between per-language
vectors of what the system learned. Two representations are measured, defined
in the next section.

- **H1 — there is a real per-language signal.** Mean pairwise `D` exceeds what
  a permutation of episode-level language labels produces. *Refuted if* real
  sits inside the shuffled distribution. (The seven-pack run got 33 SD; I
  expect this to survive at 46 languages, and if it does not, the pipeline is
  broken rather than the finding interesting.)
- **H2 — script dominates.** `D` correlates with the script-disagreement matrix
  at Mantel `r` higher than with `T_heldout`, `family` or `macroarea`.
  *Refuted if* any of the other three beats script.
- **H3 — the crux. Typology does not survive controlling for script.** The
  partial Mantel correlation of `D` with `T_heldout` given script is
  indistinguishable from zero (|r| < 0.05, permutation p > 0.05).
  *Refuted if* it is significantly positive.
- **H4 — the positive control passes.** Partial Mantel of `D` with `T_read`
  given script is positive and significant for at least the richer
  representation. *Refuted if* even the features the renderer is a function of
  cannot be recovered — which would mean the induced representation carries no
  word-order information at all, and would make H3 uninformative rather than
  null.
- **H5 — genealogy is recovered only through script and typology.** Partial
  Mantel of `D` with `family` given script is ~0.
  *Refuted if* it is significantly positive.
- **H6 — the incumbent representation is orthographic and the order
  representation is not.** `R_order` (below) beats `R_claw` on `T_read` given
  script by a wide margin, while both are ~0 on `T_heldout` given script.

**My expectation, to be confirmed or refuted:** H1 passes, H2 passes, H3 is a
null, H4 passes for `R_order` and fails for `R_claw`, H5 is a null, H6 passes.
That is: **the current representation is orthographic; a representation that
reads relative order recovers exactly the parameters the generator was given
and nothing beyond them.** A null on H3 is the expected outcome and is fully
publishable — it names the target for a representation that is not orthographic.

## The two representations

**`R_claw` — the incumbent.** Per-language firing rate and hit rate of each of
`omegaclaw_textlang-002`'s fourteen claws, exactly as
`scripts/language_clustering.py` builds them, re-derived and asserted equal to
the fitted model's own `claw_evidence` before anything is computed. 28
dimensions. Predicted to be near-orthographic: `Lesson.structured` takes no
language, so the eleven graph claws have identical reliability everywhere by
construction and 99.05% of the between-language variance sat in the three
surface claws last time.

**`R_order` — proposed, and argued for.** The surface claws already compute
`Surface.position` — the character offset of a node label's first mention in
the prose — and then throw the ordering away, keeping only "which candidate is
named most". The parallel corpus makes the discarded quantity the interesting
one: the term graph is **byte-identical across languages**, so for a pair of
graph nodes `(i, j)` in a fixed structural relation, *which of the two the
prose mentions first* is a direct measurement of that language's linearisation.
`R_order` is, per language, the vector of

    P(first mention of i precedes first mention of j | (i, j) stand in relation r)

over structural relation types `r`, plus the coverage of each `r`.

This is a richer readout of a channel the model already has, not a new oracle:
every quantity in it is computable by `omegaclaw`'s existing `Surface` index.
It is what a representation would have to look like if it were to carry word
order at all, which is why H4/H6 are stated as they are — and because the
generator's word order *is* WALS, `R_order` succeeding on `T_read` is a
sanity check on the method, not a discovery.

## Discipline, fixed in advance

- **Which languages, by rules fixed before any correlation existed.** Three
  filters, in this order, each with its reason:
  1. **46** of the database's 58 languages carry at least one WALS feature.
  2. Four of those — `spa`, `tur`, `swh`, `cmn` — are shadowed by a verified
     hand-written grammar (`grammar/grammars/__init__.py` registers each pack
     under its ISO code so a checked grammar outranks a generated one).
     Rendering four rows through a different pipeline would put a pipeline
     difference inside the distance matrix, so they are dropped. **42 languages
     are rendered and swept.**
  3. The correlations are computed on the languages whose WALS row is thick
     enough to define a distance: **at least 8 of the 14 rendered features and
     at least 2 of the 4 held-out features.** That is **33 languages, 528
     pairs**, and *the same 33 for all five oracles* — different N per oracle
     would make "script wins" possibly an N effect rather than a finding. The
     nine dropped (`ady`, `apw`, `mww`, `nmn`, `quz`, `ryu`, `twf`, `yag`,
     `yua`) are dropped for thin coding, never for their score, and they stay
     in the H1 signal test and the dendrogram where no oracle is involved.
- **`R_order` deliberately drops the word-boundary gate that `R_claw` has.**
  `Surface` matches a label with `\b...\b`, and Python's `\b` never fires
  between an ASCII identifier and a CJK character, which is the whole of why
  Chinese sat at a 0.285 verbatim rate. Keeping that gate inside `R_order`
  would guarantee the order representation is *also* orthographic and make H6
  untestable. `R_order` therefore locates a label by longest-first substring
  match with no boundary requirement, and only keys observed at least 30 times
  **in every language** enter the vector, so per-language coverage — which is
  orthography — cannot leak into it through an imputed value.
- **Mantel, not Spearman on flattened matrices.** Distance-matrix entries are
  not independent; every test is a permutation test over the 46 language labels
  (rows and columns permuted together), 9,999 permutations, and the partial
  correlations permute the residuals the same way.
- **Both metrics, always.** Mantel `r` and its permutation `p`, for all four
  oracles, for both representations, marginal and partial. No column is chosen
  after seeing it.
- **THE INVARIANT.** `tests/test_curriculum_fingerprint.py` must still report
  the global digest `68be4d098db17e28`. Enabling more languages must not change
  how the existing seven render. The known mechanism by which it could:
  `grammar/grammars/vocab.py::Vocabulary.database` imports vocabulary into the
  *hand-written* packs whenever `LanguageDB.exists()` is true. So the database
  is wired in **without touching `store.DB_PATH`** — the derived registry gets
  its own handle — and a test asserts the seven-pack fingerprint is identical
  with derived languages enabled and disabled. If the digest moves, stop and
  report.
- The 102 MB database is not committed. It is decompressed on demand into a
  cache outside the tree.
- Seeds >= 1,000,000 are eval only; the representations are fitted on training
  episodes.
- The sweep is the authority. Any scratch number may form a hypothesis and may
  not appear in the finding.

## What I am not claiming, whatever the numbers say

That these 46 renderings are good presentations of those languages. Tier 3
means "derived grammar, real lexicon, no morphology", and a Vietnamese episode
comes out with English content words in it. The claim under test is about the
**representation's sensitivity to a known external structure**, and a poor
rendering weakens the signal rather than inventing one — but a *reader* should
not take a Mantel `r` here as a statement about Yoruba.
