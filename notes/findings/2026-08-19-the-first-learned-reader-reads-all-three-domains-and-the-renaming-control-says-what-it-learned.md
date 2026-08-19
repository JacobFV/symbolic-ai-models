---
title: The first learned reader reads all three domains, and the renaming control says what it learned
date: 2026-08-19
status: measured
arm: learned-reader
---

## What was built

`symbolic_ai_core/reader/learned.py` — one reader, **no domain lexicon in its
source**, fitted three times. It is given aligned `(sentence, claim)` pairs and
induces the predicate inventory, what counts as a name, the role signature of
every predicate, each role's filler type, the unit of every quantity, the
temporal envelope, and which roles are filled from earlier text rather than from
the sentence. Two averaged perceptrons do the work: a unit classifier over
abstracted n-grams plus the signature counts, and a role ranker over a
candidate's index and the words either side of it.

What stays in the code is knowledge of **English**: sentence segmentation, a
tokenizer, and two date formats. Everything else is fitted.

## 1. In distribution it is perfect, and beats every hand-written reader

400 training documents, 60 held-out (seeds from 1,000,000), 4 phrasing variants,
`hard_distractors=True` in all three domains. Claim sets compared **up to
renaming of entities the document never names** — see §4.

| domain | arm | P | R | F1 | end-to-end |
|---|---|---|---|---|---|
| solvency | learned | 1.000 | 1.000 | **1.000** | **1.000** |
| | hand (`read_signature`) | 0.914 | 1.000 | 0.955 | 1.000 |
| scheduling | learned | 1.000 | 1.000 | **1.000** | **1.000** |
| | hand (`read_signature`) | 0.912 | 1.000 | 0.954 | 0.767 |
| flood | learned | 1.000 | 1.000 | **1.000** | **1.000** |
| | hand (`read_content_roles`) | 0.966 | 1.000 | 0.983 | 0.400 |

Oracle world is 1.000 end-to-end by construction in all three.
`runs/learned_reader.json`.

## 2. The control that must fail, failed: 1.000 → 0.000 under renaming

Every entity in the held-out documents renamed to a form the fit never saw
(`region_3` → `zone_5123`), consistently in the case, so the document is
re-rendered rather than string-substituted (§5).

| domain | in distribution | renamed |
|---|---|---|
| solvency | 1.000 | **0.000** |
| scheduling | 1.000 | **0.000** |
| flood | 1.000 | **0.000** |

Total collapse, and the induced lexicon says why: **9 memorised forms and no
productive shapes.** These corpora contain about ten distinct entity names in
total, so nothing in the fit could establish that `region_*` is a *kind* of name
rather than a list of them. The 1.000 in §1 is a reading of a memorised
vocabulary.

## 3. Identity generalisation costs exactly one augmentation

Refit on 400 documents whose entities are renamed per document. The shape `a_9`
now appears with hundreds of distinct fillers and becomes **productive**, so an
unseen name is recognised by its form.

| domain | fit | renamed test | in-distribution test | end-to-end (renamed) |
|---|---|---|---|---|
| solvency | augmented only | 0.955 | 0.514 | 1.000 |
| | **union** | **0.955** | **0.955** | **1.000** |
| scheduling | augmented only | 1.000 | 1.000 | 1.000 |
| | **union** | **1.000** | **1.000** | **1.000** |
| flood | augmented only | 0.994 | 0.992 | 1.000 |
| | **union** | **0.994** | **0.992** | **1.000** |

The augmented-only column carries a lesson of its own: solvency falls to 0.514
**in distribution** after augmenting, because its parent entity is called
`group` — no number, so shape productivity cannot reach it — and augmenting every
document destroyed the memory that was carrying it. A name that does not follow a
productive shape must be memorised, and the union fit is what holds both ends.

`runs/reader_survives.json`.

## 4. Two mechanisms the surfaces forced, both general

**Minting.** flood's bridges are in the world and in no sentence: the prose says
*the road bridges the river*, and `bridge_4` is the generator's private
bookkeeping. A reader must invent an identity, so the reader mints one from the
mentions in the same unit — `~region_1|region_2`. `bridge_on` and `load_limit`
are stated in different paragraphs and mint the *same* id without either naming
it. Whether a role is minted or resolved by reference is **induced**: the fit
records how often a filler is absent from its sentence (`external`) and how often
it is absent from the whole document (`latent`), and those are different acts.

Scoring compares up to renaming of the unnamed — a fingerprint of the claims an
unnamed entity takes part in — applied identically to gold and to every arm.
Comparing minted names to `bridge_4` would measure whether a reader guessed the
generator's numbering, which the hand reader was told and a learned one cannot be.

**Entity schema is not reading.** Which profile an entity carries, and that a
vehicle declares a `payload` variable for the SMT step, appear in no sentence.
The hand reader hard-codes them. Here they are induced from the training worlds
as `(predicate, role) -> type` and `type -> facet template`, and supplied
identically to every arm.

## 5. Three bugs, and what each cost

- **The averaged perceptron's clock counted mistakes, not examples.** Once the
  ranker converged the clock stopped, so the average was dominated by the first
  few chaotic updates. Symptom: solvency's `owns` inverted parent and child on
  two of its four phrasings, 0.796 F1. One line; 1.000 after.
- **The mention history advanced only on claim-bearing sentences.** flood
  introduces a vehicle in a sentence written to be pure scaffolding and then says
  *"It can take a further N kg"*. Skipping scaffolding lost the antecedent and
  attached the payload to a region two paragraphs back — one wrong claim per
  document, and the answer wrong every time.
- **Renaming by string substitution shifted every alignment after it**, because
  spans are character offsets. It read as a catastrophic reader failure and was a
  broken control. Rename the case and re-render.

## 6. What this does not show

- Four phrasing variants, generated. **Held-out phrasings are the honest
  generalisation test and they are much harder** — 0.850 / 0.754 / 0.770 F1 with
  end-to-end 0.567 / 0.583 / 0.333 when fitted on 2 variants and tested on 4.
  Recorded in the companion finding on what claim F1 does and does not predict.
- The reader is a perceptron over n-grams, not a neural encoder. That is a
  feature for the cost ledger and a limit on what these numbers say about
  scaling.
- Nothing here is real text. The real-text arms of this session measured
  extraction at chance against critical error mass at 0.946, and no part of that
  is contradicted by a generated-surface result.

## What would have refuted it

The renaming control surviving at 1.000 (it would have meant the lexicon was
doing something other than memorising, and the diagnosis was wrong), or the
augmented fit failing to restore it (it would have meant something *else* was
memorising and the headline was not what it appeared to be).
