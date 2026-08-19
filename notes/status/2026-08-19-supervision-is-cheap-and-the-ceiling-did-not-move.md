---
title: Supervision turned out cheap, and the ceiling did not move — the fork is now sharper, not resolved
date: 2026-08-19
kind: status
---

A programme-level assessment after the real-text arc closed. Every number is
cited from a note under `notes/findings/`; this introduces no measurements. It
supersedes `notes/status/2026-08-19-the-boundary-is-built-priced-and-bounded.md`,
which predated the corpus closure, the composed-query work, the bottleneck
pricing, the bootstrapping arm and three methodological corrections.

## Where we are

**The supervision question is closed, and the answer is that supervision is
cheap.** Two results settle it:

- Matching four hand-written patterns takes **384,874 articles** — a two-point
  fit that was then **verified on twelve points**, four sizes by three shuffles
  inside one code path. That quantity costs **$0.032 of compute**, 27,000 batched
  requests and 349 MB. The pattern side is an expert's afternoon, one to three
  orders of magnitude more in money.
- And the knowledge base is not even required. **Bootstrapping from a 210-article
  seed exceeds full distant supervision on 2,102 articles**, on 3/3 splits, +37%
  relative at round 2 — and *every* round from 1 to 8 is at or above that
  ceiling, so the procedure is safe even though **no unsupervised signal finds
  the peak**.

**The reader ceiling did not move.** Everything in that paragraph lives between
0.09 and 0.18 on `parent` against hand-written patterns at **0.393**. Eight
distinct interventions have now been closed: multi-instance pruning, WordNet
supersenses, frames on the classifier, class balancing (twice, at both corpus
scales), answer aggregation, frames on the ranker, ten times the text, and
self-training. Only two ever moved the number — more text (+55%) and the query
(+4%) — and the crossover says the first runs out at 385,000 articles.

**So the explanation "we need better or more supervision" is now excluded.** That
is the change since the last assessment. The fork it leaves is the same one and
it is sharper: what remains is the **representation**, and `CLAUDE.md` scopes the
neural half as a control not to be invested in. **The evidence and the scope
still disagree, and the space of alternative explanations has shrunk.**

## How things progressed, including what went wrong

The arc was: build the world at scale → measure composed queries → attack the
economics → audit the method → price the bottleneck → try to escape it.

**Three headlines were withdrawn or corrected, all mine, all within hours.**

- *"The composition law holds to within 0.001"* — six successes in 191 chains,
  inside an interval admitting ratios from 0.4 to 2.1.
- *"The union's gain grew sevenfold with scale"* — an **ordering artefact**; the
  corpus file is 1,661 articles followed by 841 hubs, which only enter at the
  largest prefix. Shuffled, the gain is −9% at 200 articles and **plateaus at
  17–20%**.
- *"The Heaps exponent replicates to three decimals"* — the same prefix defect;
  shuffled, content-word β is 0.669–0.728 against a published 0.648, a ±0.03
  spread around an agreement of 0.007.

Two lesson notes came out of them — **a rate without its numerator is not a
result** and **a prefix is not a sample** — and both were then applied to
everything sharing the pattern. That is where the value was: the third sweep
found the crossover **survives at full strength**, which matters because the
cheap failure after two corrections is to start discounting everything.

**Two results got stronger under attack.** The pattern reader's clumping
replicated on an independent chain population, then its *mechanism* was confirmed
directly — `P(parent read right | child read right) = 0.288` against a marginal
0.171, **p = 0.006** — and then replicated on a second relation. And the
persistence economics survived being re-based from an unfair comparison (an API
re-reading the whole corpus, 9,050x) to a fair one (iterative retrieval,
**54.5x at a single query**).

## Trajectory

**Do:** decide the fork. It is now a decision rather than a research question,
because the alternatives have been tested and closed. The three honest options
are unchanged — extend the scope to a small CPU encoder; accept 0.18 on real text
and spend effort where the numbers are strong; or change the task so features
suffice — but the first is now the only one with an untested mechanism behind it.

**Stop:** feature-level work on the real-text reader, and any further supervision
work. Eight closed levers is enough.

**Keep:** two things that pay regardless of the fork, with one of them since
demoted. **Error topology** — a reader's failures cluster or do not, it is
measurable at p = 0.006, and it changes which reader you want for composed
queries independently of accuracy. And **in-degree**, which predicts where errors
are expensive before any reading — but as a **diagnostic only**: three
interventions have now been tried on it (corroboration, selective ingestion,
weighted training) and all three failed, the last because hub articles are hard
for reasons duplication cannot fix. It is something to report to a user, not
something to optimise.

That makes **two signals this session that are real and diagnostic-only**, the
other being sensitivity. A quantity measured *about* a reader is not
automatically a quantity that reader can be steered by, and this programme has
now produced two of each.

## How this fits the narrative

The **knowledge-acquisition bottleneck** is the thing the symbolic-AI post-mortem
says killed the programme. This work says it **moved rather than vanished**: from
rules to labels, and the labels turn out to cost about **200 examples plus
self-training** for a relation with any public curation, or $0.03 and a machine-day
for one with a lot. That inverts the classical cost story, and it does not rescue
the programme — because what the labels buy tops out at 0.18 where a person's
afternoon buys 0.393.

The honest reading is uncomfortable for both camps. **Against the symbolic
tradition**: hand-written rules still win at this scale, and they win by encoding
what English does with ownership, which is knowledge no amount of this corpus
supplies. **Against the scaling position**: the winning artefact is four regular
expressions, and the measured exchange rate says beating them takes a third of a
million documents.

## What should make an outside reader sceptical

- **One relation family, one genre, one source.** A second genre was looked for
  and is not on disk: OpenAlex abstracts mention their affiliation 3.7% of the
  time.
- **Composed-query claims rest on single-digit event counts.** 415 chains at a
  few per cent is 6 to 21 successes, and this assessment quotes none of them as a
  point estimate.
- **Three withdrawn headlines in one session**, and the withdrawals were found by
  controls the same author designed.
- **No LLM accuracy anywhere.** Every cost comparison is a price sheet plus the
  symbolic side's own accuracy, and the claim survives only because it is drawn
  at accuracy 1.000 on the generated domains.
- **The bootstrapping result is 3 splits with per-split significance of 1.02,
  2.38 and 1.14** — direction 3/3, magnitude large, individual tests mostly not
  significant.
