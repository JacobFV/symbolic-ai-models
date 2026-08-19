---
title: The transferable component was 85% false positives on real English
date: 2026-08-19
status: measured
arm: gate-on-real-prose
---

## The claim that had never been tested

`symbolic_ai_generators/staleness.py` is the first component here meant to
transfer across domains unchanged, and its whole claim on attention is that its
cue list is **closed-class**, so adding a domain does not add words. Every number
for it came from surfaces this repo generated with distractors this repo wrote.
"Closed-class" is an argument about how the risk *grows*, not a measurement that
it is small.

`data/sources/openalex-prose` holds 5,000 real scientific abstracts — **36,223
sentences of English nobody here wrote**. The aggregate firing rate is not the
interesting number; *which cue fires* is.

| | fires | share |
|---|---:|---:|
| **`used to`** | **443** | **53.5%** |
| `previously` | 206 | 24.9% |
| `once` | 88 | 10.6% |
| `no longer` | 23 | 2.8% |
| `former` | 22 | 2.7% |
| `before the` | 21 | 2.5% |
| `until the` | 17 | 2.1% |
| `formerly` | 14 | 1.7% |
| `ceased`, `struck` | 4 | 0.5% |

**2.29% of real sentences, and roughly 85% of those fires are wrong.**

## Two corrections, both on meaning rather than on the numbers

**1. `used to` is two constructions and only one of them cancels.** The habitual
past — *"job_0 used to cut"* — says the state is over. The passive of *use* —
*"is used to obtain"*, *"have been widely used to examine"* — says nothing of the
kind, and it is **53.5% of every fire**, 439 of 443 as the only cue in the
sentence. That is not a temporal/cancelling confusion; it is an ambiguity between
two grammars, and it separates on one observable: **the passive is preceded by a
form of *be***, usually with an adverb between. Three tokens of lookback is what
is available without a parser.

**2. Four cues mark temporal ordering, not withdrawal.** *"before the
reaction"*, *"previously reported"*, *"once-weekly"*, *"until the endpoint"*. A
sentence may bound a state in the past without taking it back — *"before the war,
X was Y"* leaves X possibly still Y. Dropped, and kept as `CANCELLING_V1` so the
earlier numbers stay reproducible.

## The result, and why it is a check rather than a fit

Real-prose firing: **2.29% → 0.34%**, a **6.8×** improvement.

And **every generated-surface number is byte-identical**: scheduling
1.000 / 1.000 / 1.000, flood 0.933 in all four cells. Removing cues can only
*reduce* firing, so the domain numbers could only have stayed or fallen — they
stayed, which is the evidence that what was removed was noise rather than signal.
Every distractor here carries a second, genuinely cancelling cue: `disused`,
`came off`, `used to` (habitual), `former`, `withdrawn`, `struck`.

The direction the corrections err in is the cheap one: a missed cancellation
leaves a claim standing, where a false positive **deletes a true one**.

## A second genre corrected it again, and differently

One corpus is not a measurement. **75,555 sentences of public-domain narrative**
(12 novels, `scripts/gate_on_narrative.py`) is the opposite draw from abstracts:
habitual *used to* genuinely occurs, and the past tense is the default.

| | abstracts | narrative |
|---|---:|---:|
| tense gate | 0.135 | **0.451** |
| cancellation, first list | 0.0229 | **0.0395** |
| cancellation, after the abstracts fix | 0.0191 | **0.0191** |

And the cue composition is **not the same distribution**:

| dominant fire | abstracts | narrative |
|---|---:|---:|
| `used to` (passive of *use*) | **53.5%** | rare |
| `struck` (the verb *strike*) | 2 fires | **29.9%** |

**Each genre surfaced a different dominant false positive, and neither was
predictable from the other.** `struck` fired twice in 36,223 scientific sentences
and 431 times in 75,555 narrative ones — *"struck him"*, *"was struck by"*. The
cancelling sense always carries a particle: **`struck from`**, **`struck off`**.
That is the correction, and it is on meaning again, not on the count.

Narrative firing after it: **1.91% → 1.35%**. Abstracts: 0.34% → **0.33%**. And
the generated surfaces are byte-identical for the third time — scheduling
1.000/1.000/1.000, flood 0.933 in all four cells.

### And a third construction, which corrects my own docstring

Narrative also measures what abstracts could not: the lookback's false-negative
rate. It suppresses **21%** of `used to`, and I recorded that as a cost. Read at
the sample it is mostly **not an error** — it is **`be used to` meaning
*accustomed***: *"he had been used to look"*, *"he has been used to her
complaints"*, *"he was soon used to be talked to"*. That is a state which may
still hold, so it correctly does not cancel. `used to` is **three** constructions,
not two.

The one genuine loss the sample showed — *"this May that we have been having,
I used to run down"* — was the window reaching across a comma into a different
clause. Bounding it at a comma or semicolon fixes that case; the residual
suppression stays at 21% because it is the *accustomed* sense.

## The residual, which needs word senses rather than more words

122 fires remain in 36,223 sentences. Their composition:

- `no longer` (19%) — sampled three, all **genuine**;
- `former` (18%) — and **77% of these are `"the former"`**, the correlative
  pronoun paired with *the latter*, a different sense entirely;
- `formerly` (11%), `ceased`, `struck` — small and mostly right.

Closing the `former` residual needs to tell a **pronoun** from an **attributive
adjective**, which no cue list can do: *"the former subsidiary"* is attributive
and *"the former value"* is correlative, and they differ only in what the word is
doing in the clause. That is a part-of-speech question, and it is where this
approach ends rather than a defect in the list. Recorded and not patched, because
the available patch — suppressing `the former` — would kill *"the former
subsidiary"*, which is exactly the phrase the intended domain uses.

## What would refute this

- Two corpora, two genres, and the **third** is the one that matters and is
  blocked: SEC EDGAR 403s without a contact **email** in the `User-Agent`, and
  the user's personal address is not mine to send to an unrelated service
  unasked. Financial filings are the genre solvency imitates and would weight
  `former`, `ceased` and `withdrawn` far higher than either corpus here.
  Unblocking it is one line from the user.
- Both corrections after the first were found by **adding a genre**, not by
  thinking harder about the list. That is the method; there is no reason to
  believe a third genre would find nothing.
- The residual composition is read off three sampled sentences per cue and one
  exact count (`"the former"`, 17 of 22). The rest is not hand-labelled.
- The three-token lookback is an approximation with a known false negative
  (*"he was tired and used to walk"*), unmeasured because this corpus has no
  narrative.
