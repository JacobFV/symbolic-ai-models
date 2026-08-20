---
title: A perfect sentence classifier is worth 2–3x and would beat the hand patterns — except where the patterns use knowledge the corpus lacks
date: 2026-08-19
status: measured
arm: relation-readability
---

The decomposition says the classifier is the lowest factor in all five relations.
The proposed critical path is to replace that one component. **Its value can be
bounded without building it**: replace the classifier with an oracle — a sentence
is labelled for relation `R` exactly when it contains a gold `R` filler — and
leave the proposer, ranker, role filling and supervision untouched.

`runs/oracle_classifier_headroom.json`, 2,502 articles, `PhraseMentions`.

| relation | learned | **oracle classifier** | hand-written | oracle/learned |
|---|---|---|---|---|
| `parent` | 0.136 | **0.413** | 0.201 | **3.0x** |
| `country` | 0.192 | 0.458 | **0.692** | 2.4x |
| `headquarters` | 0.231 | **0.439** | 0.228 | 1.9x |
| `founder` | 0.110 | 0.261 | — | 2.4x |
| `industry` | 0.025 | 0.164 | — | 6.6x |

## Fixing the classifier is worth two to three times, everywhere

Not a marginal gain — it **doubles to triples every relation measured**, and 6.6x
on the one where the classifier is weakest. That is the size of the prize for the
component twelve interventions failed to move, and it is now measured rather than
argued.

**Predicted the oracle would land just *below* the hand reader on `parent`
(≈0.36 against 0.393). Wrong on both numbers.** The oracle reaches **0.413**, and
the hand reader on *this* corpus reads **0.201** — its 0.393 was measured on the
168-article set, and the closed corpus is enriched with hub articles that read
worse. On like-for-like data a perfect classifier would put the learned reader at
**twice the hand-written patterns** on `parent`, and it already beats them on
`headquarters` (0.231 against 0.228) before any fix.

## The exception says exactly what hand-written knowledge is for

`country` inverts it: the hand reader reads **0.692** against an oracle ceiling of
**0.458**. It beats a *perfect classifier* by half again.

The mechanism is declared and is not a trick: `read_country` carries a
nationality-adjective map, so it reads *"a Japanese company"* as `country=Japan`.
The string `Japan` never appears, so **distant supervision cannot see that
sentence at all** — containment for `country` is 0.579 and the oracle inherits it.

That is the clearest statement this session has produced of what hand-written
rules buy:

> Hand-written knowledge beats any amount of corpus-internal learning **exactly
> when it reads a form the corpus never states literally.** Where the relation is
> stated in the text, learning wins once its binding factor is fixed. Where the
> relation is *implied* by a form the gold never contains, no amount of
> supervision on that gold can reach it.

## What this changes about the critical path

The recommendation given earlier — that a perfect classifier would still not beat
four regexes, so the ceiling is the corpus — **is wrong for three of the five
relations and right for one**. Corrected:

- **`parent`, `headquarters`, `founder`, `industry`**: fixing the classifier is
  worth 1.9x–6.6x and takes the learned reader past the hand-written baseline
  where one exists. The critical path is the classifier, and the prize is large.
- **`country`**: the ceiling really is the corpus, because the relation is
  expressed adjectivally and containment-based supervision is blind to it. No
  classifier fixes that; a **morphological rule or a lexicon** does, and the
  existing hand reader already has one.

The two cases want different work, and the four-factor table tells you which one
you are in before you start: a relation whose `containment` is far below its true
statement rate is a lexicon problem, not a model problem.

## What would have refuted it

The oracle landing near the learned reader — the classifier would then not be the
binding factor and the decomposition would be wrong about where the loss is. It
is 1.9x to 6.6x above it in five of five relations.

## Limits

- The oracle uses gold containment, so it is an **upper bound on any classifier**
  that works from the sentence alone; a real one will land below it.
- `industry`'s 0.164 is on 2,058 articles but only 51 correct at the learned
  arm — the ratio is better founded than the small end of it.
- Hand-reader figures are on this corpus and are not comparable to the
  168-article numbers quoted earlier in the session.
