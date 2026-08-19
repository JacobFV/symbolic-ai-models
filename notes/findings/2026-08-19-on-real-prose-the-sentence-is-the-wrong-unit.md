---
title: On real prose the sentence is the wrong unit
date: 2026-08-19
status: measured
arm: wikipedia-parents
---

## The first task in this repo with real prose and a real answer

Every number here is measured on text the repo generated, and every structured
source on disk — cfpb, senate-lda, sec-edgar, patentsview, cskg, gutenberg — has
been normalised into node/edge tables with the prose stripped. Checked, not
assumed.

Wikidata's `P749` (*parent organization*) plus the English Wikipedia intro is
**paired** prose and fact, and it is the real-world analogue of solvency's
`owns`. Better still, a `P749` statement carrying an **end time** (`P582`) names a
parent the company *used to* have, and Wikidata keeps both — so this is a
labelled **staleness** set, not merely a labelled ownership set.

168 companies, fetched through CirrusSearch and the entity API because WDQS was
rate-limiting to one request a minute. *(An earlier draft of this note quoted the
numbers at n=148, mid-fetch; the table below is the completed set and the
conclusion is unchanged.)*

## The context, before any arm

- **The current parent is named in the intro on only 0.696 of articles.** Nearly a
  third are unanswerable from the text given, whatever reads them.
- Wikidata lists a **former** parent for 0.155, and the intro actually names one
  on **0.113**.
- **`stale_by_cancellation` flags a sentence on 0.339 of these articles** —
  against 0.004 of scientific abstracts. Company prose is *dense* in cancellation
  language, which is exactly the condition under which a sentence-level gate is
  dangerous.

## Three arms

| arm | answers | correct | precision | picks a **former** parent |
|---|---:|---:|---:|---:|
| naive patterns | 0.589 | **0.369** | 0.626 | 0.024 |
| **+ sentence gate** | **0.542** | **0.327** | 0.604 | **0.024** |
| **+ clause gate** | 0.583 | 0.357 | 0.612 | **0.018** |

**The sentence gate loses coverage and accuracy and removes no staleness at all.**
It costs eight answers and 0.042 accuracy, and the former-parent error does not
move. The clause gate keeps the coverage and is the only arm that reduces the
error the gates exist for.

The worked example is **Miramax**, whose Wikidata record lists *beIN Media Group*
and *Paramount Global* as current and *Filmyard Holdings* and *The Walt Disney
Company* as former:

```
sentence gate -> 'Walt Disney Company'   <- a FORMER parent
clause   gate -> 'Qatari'                <- wrong, but not a dead owner
```

The sentence gate kept the sentence naming the dead owner and deleted the one
naming the live one. Three more — *Disney–ABC Domestic Television*, *CBS Media
Ventures*, *Sun Microsystems* — go from an answer to **no answer at all** under
the sentence gate and keep one under the clause gate.

## What this says about everything built today

On the generated surfaces **one sentence carries one claim**, so deleting a
flagged sentence is free: measured, `stale_by_cancellation` leaves all three
byte-identical. Real prose packs several claims into a sentence — *"Formerly a
subsidiary of X, it was acquired by Y in 2015"* carries the dead parent and the
live one — and a sentence-level gate cannot be right about it.

> **The unit of staleness is a clause, not a sentence, and the generated surfaces
> could not have shown that** because they never put two claims in one sentence.

That is a defect in the **benchmark's granularity**, not in the gate. Every
claim-level mechanism in this repo — the audit's spans, `unconsumed`,
`evidence_conflict`, `filter_stale` — assumes one claim per sentence, and that
assumption has never been tested against text nobody here wrote.

## And the proportion is the sobering part

The former-parent error is **2.4% of articles**. Precision among answered
articles is **0.63** against a ceiling of 0.696. So on real text, the staleness
problem that took a day is a **small slice** of the error and the dominant one is
that extraction is simply hard. Getting staleness perfectly right here would move
accuracy 0.369 → 0.393.

## What would refute this

- 168 articles, one relation, one language, one encyclopedia's register.
  Wikipedia intros are unusually well-structured prose.
- The naive extractor is four regex patterns and its 0.63 precision bounds every
  arm. A better extractor could change which gate helps.
- `P749` is itself noisy: several companies list three current parents (joint
  ventures), and "correct" credits any of them.
- The clause splitter is a comma-and-conjunction split, which is a crude proxy
  for a clause and will merge or split wrongly on long sentences.
