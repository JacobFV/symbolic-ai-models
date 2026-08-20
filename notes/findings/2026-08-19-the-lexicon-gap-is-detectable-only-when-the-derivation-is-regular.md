---
title: The lexicon gap is detectable only when the derivation is regular — and the hardest case is the invisible one
date: 2026-08-19
status: measured
arm: relation-readability
---

`country`'s hand reader beats a **perfect classifier** (0.692 against an oracle
ceiling of 0.458), and the mechanism claimed was that it reads a form the gold
never contains. That produced a triage rule with no way to apply it, so this
built one: a **morphological proxy needing no lexicon** — does some token start
with the gold's first five characters (`Japan` → `Japanese`)?

| relation | gold | exact | prefix | **gap** | verdict |
|---|---|---|---|---|---|
| `parent` | 1788 | 0.598 | 0.589 | −0.008 | model problem |
| `country` | 2349 | 0.579 | 0.632 | **0.054** | *"model problem"* |
| `headquarters` | 2394 | 0.553 | 0.481 | −0.072 | model problem |
| `founder` | 1017 | 0.446 | 0.367 | −0.080 | model problem |
| `industry` | 2058 | 0.241 | 0.657 | **0.416** | **LEXICON problem** |

**Predicted `country` would show the largest gap. It shows 0.054 and the
diagnostic calls it a model problem — which is wrong.**

## Measuring the truth directly

| on 2,349 articles with `country` gold | |
|---|---|
| literal country name present | 0.579 |
| nationality adjective present and mapping to gold | **0.739** |
| **adjective present, literal absent** | **0.293** |

**29.3% of `country` articles state the country only adjectivally.** The mechanism
claimed last turn is confirmed and is larger than the claim: it fully accounts for
the hand reader's 0.234 advantage over a perfect classifier.

## Why the proxy missed it, and what that means

A five-character prefix catches `Japanese`/`Japan` and `German`/`Germany`. It
cannot catch `French`/`France`, `Dutch`/`Netherlands`, `British`/`United Kingdom`,
`American`/`United States`, `Spanish`/`Spain` or `Chinese`/`China` — **the common
ones are suppletive or irregular**, sharing no stem with the country name.

So the diagnostic is **one-sided**, and that is the finding:

> A prefix gap **proves** a lexicon problem when it is large. A small gap
> **does not prove its absence**, because the derivations that matter most are
> exactly the ones morphology cannot recover — irregular, suppletive, or an
> entirely different word.

`industry` is the regular case and the proxy nails it: gold `automotive industry`
against text *automotive company*, gap **0.416**, and its oracle ceiling of 0.164
is far below what a paraphrase-aware reader could reach. `country` is the
irregular case and the proxy is blind to it.

## What is actually usable

- **A large prefix gap is a reliable positive.** `industry` was flagged with no
  lexicon, no hand reader and no model — which is what the triage rule wanted.
- **A small gap means "no evidence", not "no problem".** Detecting the
  `country` class requires the lexicon it is telling you to build, which is
  circular, and the honest response is to say so rather than to trust the zero.
- **The one-sidedness is the practical rule**: use the gap to *find* lexicon
  problems cheaply, never to *rule them out*.

That leaves `country`-class gaps discoverable only by noticing that a hand-written
reader beats a measured ceiling — which is how this one was found, and which
requires having built the hand reader first.

## What would have refuted it

The 0.054 being the true figure — the earlier mechanism claim would then have been
wrong and `country` really would be a model problem. Direct measurement puts the
adjective-only share at 0.293, five times what the proxy sees.
