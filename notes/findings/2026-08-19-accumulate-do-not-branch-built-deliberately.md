---
title: Accumulate, do not branch — built deliberately
date: 2026-08-19
status: measured
arm: accumulating-readers
---

## A rule from one accidental case is a hypothesis

The packing result produced one actionable rule — *accumulate, do not branch* —
and it was derived from flood being the **only** reader that survived a packed
sentence, which it did by accident: `read_content_roles` folds crossings into
links rather than selecting a branch, for reasons that had nothing to do with
packing. That is a hypothesis, not a design principle, until it is built on
purpose somewhere it did not already hold.

`read_signature_accumulating` in both collapsed domains. For each sentence it
extracts **every** claim pattern instead of choosing one branch by shape:

- solvency — two or more entities enrol members; a money value with a date files
  a figure, bound to the entity **nearest the money**;
- scheduling — a machine sentence yields its capacity **and** any capability
  words in it, rather than one of them.

The binding matters and is content-free: in *"group owns sub_0, which reported
105.87 USD, filed 29 May 2026"* the filer is **sub_0**, the entity beside the
number, not the subject of the sentence. That is positional adjacency — the same
signal flood uses to attach a demand to its site.

## It works, and it costs nothing

| reader | unpacked | **packed** |
|---|---:|---:|
| solvency, branch | 1.000 | **0.567** *(its floor)* |
| solvency, consolidated | 1.000 | **0.567** |
| **solvency, accumulate** | **1.000** | **1.000** |
| scheduling, branch | 1.000 | **0.658** *(its floor)* |
| **scheduling, accumulate** | **1.000** | **1.000** |

And on every **honest** surface the accumulating readers are **identical** to the
branching ones:

| solvency | clean | owns cued | owns uncued | both uncued |
|---|---:|---:|---:|---:|
| branch / consolidated / **accumulate** | 1.000 | 0.475 | 0.475 | 0.433 |

| scheduling | clean | hard machine | hard job |
|---|---:|---:|---:|
| branch / **accumulate** | 1.000 | 0.767 | 0.967 |

**Strict domination.** A more permissive reader could have admitted claims the
branching one correctly refused — the precision failure this repo keeps finding —
and the honest-surface columns are where that would show. It does not show.

## What this settles

The rule is now built on purpose in two places where it did not hold before, and
it recovers everything packing took, at no cost. So *accumulate, do not branch* is
a **design principle** rather than a description of one lucky reader.

It also sharpens what the packing theorem does and does not forbid. The theorem
says no reader can decide a packed sentence's kind **from its signature**, because
a signature is a function of the sentence. It does **not** say the claims are
unrecoverable — they are all still there, and a reader that scans for patterns
rather than selecting on shape gets them. What the signature loses is the
*classification*; what accumulation recovers is the *content*.

## What would refute this

- Two domains, one packing pattern each. A packing that made two claims share a
  *pattern* rather than a sentence — two money values in one sentence, say — would
  need a binding rule the nearest-money heuristic does not supply.
- The nearest-money binding is untested against a sentence with two filings.
- The published readers are kept registered beside these, so no number attached to
  their names has moved.
