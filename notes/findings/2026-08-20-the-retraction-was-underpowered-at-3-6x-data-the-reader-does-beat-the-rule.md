---
title: The retraction was underpowered — at 3.6× the data the reader does beat the two-line rule (p=0.013)
date: 2026-08-20
status: provisional
arm: router-at-scale
retracts:
  - notes/findings/2026-08-19-on-novel-vocabulary-the-learned-reader-is-indistinguishable-from-two-lines.md (mine, from the previous day)
notes:
  - that note named this exact weakness as its own limit, and the limit was real
---

## Why this was run

Every interval in the router arm rested on **n=184** unseen items, and each note
said so. The strongest of them concluded that *"on novel vocabulary the learned
reader is not distinguishable from a zero-supervision positional-plus-
morphological rule"* — McNemar p=0.643, 19 discordant wins against 23 — and
recorded its own limit precisely:

> n=184 is the binding constraint on every number here — the paired test's power
> at 42 discordant pairs is low, and a real effect of the size seen on the seen
> slice would need roughly four times the data to show up.

A second fetch added **1,970 biographies** to the original 850. The unseen slice
grew from 184 to **663**, 3.6×. This is the same measurement on it.

## What was measured

2,820 biographies, 4-fold, same code path.
`runs/paired_reader_vs_floor.json`, `runs/heldout_router.json`.

| | n=184 (old) | **n=663 (new)** |
|---|---|---|
| reader | 0.288 | **0.303** [0.269, 0.339] |
| floor | 0.310 | **0.259** [0.228, 0.294] |
| discordant | 19 reader / 23 floor | **78 reader / 49 floor** |
| McNemar | **p = 0.643** | **p = 0.013** |
| verdict | indistinguishable | **reader separated, ahead** |

Seen slice, n=2,811: reader **0.504**, floor **0.399**, McNemar **p < 0.0001**
(530 against 234).

## The result: the retraction does not survive, and it failed exactly as predicted

**The reader beats the two-line rule on novel vocabulary.** p=0.013 on 127
discordant pairs, where 42 pairs gave p=0.643. Nothing about either system
changed; only the sample did.

So yesterday's headline — *"open-vocabulary reading belongs to WordNet plus two
lines of morphology, and the learned reader is a vocabulary model"* — is **wrong
in its strong form** and must be withdrawn. The corrected statement:

- the reader is ahead on novel vocabulary, by **+0.044**, p=0.013;
- it is ahead by more on familiar vocabulary, **+0.105**, p<0.0001;
- so learning still buys **more** on seen values than novel ones — that part
  stands — but "nothing on novel values" was a **false null from a small sample**.

**The floor also moved, and downward: 0.310 → 0.259.** That is the larger share
of the swing, and it is a warning in its own right — a hand-written rule's score
on 184 documents was optimistic by 0.05. Both sides of a comparison drift on a
small sample, not just the side being defended.

## The router at scale

| slice | reader | floor | oracle | held-out router | gain | captured |
|---|---|---|---|---|---|---|
| unseen (n=663) | 0.303 | 0.259 | 0.377 | **0.356** [0.320, 0.393] | **+0.053** | **71.4%** |
| seen (n=2811) | 0.504 | 0.399 | 0.587 | **0.544** | **+0.040** | 48.3% |

The router survives scaling intact: **+0.053** on novel vocabulary, held out end
to end, against a predicted band of +0.02 to +0.05 — just above it. Its
fold-to-fold threshold spread also **tightened sharply**, 0.581–0.956 → 0.515–0.696,
which is what the earlier note said to watch and it moved the reassuring way.

**Capture rose to 71.4%, outside the 33–63% band I published yesterday.** That
band was six pairings; it is now seven and the band is 33–71%. Recorded as
refuted rather than quietly widened.

**Agreement-only routing gets worse at scale** — −53.1% of headroom on unseen,
−120.5% on seen. That conclusion strengthens.

## What this says about the session

Three successive claims about the same quantity, each overturning the last:
**+0.266** (floor too weak) → **+0.065** → **+0.022, indistinguishable**
(underpowered) → **+0.044, p=0.013**. The first two errors were mine to catch
and I caught them. The third was catchable only by getting more data, and the
note that made it said so in its own limits section.

The reusable point is not "be careful with small n". It is that **a null needs a
power statement or it is not a result.** The p=0.643 note reported an interval
and a mechanism and read as much more settled than it was, because a null
formatted like a finding looks like a finding.

## What would refute this

The two fetches use the same Wikidata search and the same four properties, so
the 1,970 new biographies are a larger sample of the same population, not an
independent one. A genuinely different corpus could still move this. Also
untested at scale: the `employer` relation, whose numbers remain at n=158.

## Limits

One relation, one corpus, one annotation source. The floor's 0.05 drop between
samples is unexplained and deserves its own look before either number is
promoted.
