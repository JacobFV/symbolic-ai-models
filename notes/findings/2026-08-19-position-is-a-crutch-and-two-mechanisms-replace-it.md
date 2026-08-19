---
title: Paragraph position is a crutch, and two mechanisms replace it — 72 worlds to 2.5 and a bound from 0.0% to 60.6% decided, with no content word read
date: 2026-08-19
author: lead
status: provisional
tags: [reader, ambiguity, external-knowledge, world-ir, structural-coreference]
---

## The question

The five-paragraph surface hands the reader **section headings and a fixed
paragraph order**, and position does most of the disambiguation. Ablating it
leaves **72 consistent worlds** and a bound deciding **0.0%** of the fleet — the
world carries the ambiguity soundly and says nothing useful.

So: can anything replace position that is cheaper than a document template?

## Two mechanisms, measured

| arm | worlds | sound | cert. IN | cert. OUT | open | **decided** |
|---|---:|---:|---:|---:|---:|---:|
| no external knowledge | 72.0 | 1.000 | 0.00 | 0.00 | 3.00 | **0.0%** |
| + **value registry** | 9.0 | 1.000 | 0.91 | 0.18 | 1.91 | **36.4%** |
| + registry + **adjacency** | **2.5** | 1.000 | 1.41 | 0.41 | 1.18 | **60.6%** |

**Soundness is 1.000 throughout.** Neither mechanism ever excludes the true
reading; they only shrink the set of readings consistent with the text.

**The value registry** exploits disjoint vocabularies — mass `{1200,1800,2600,
3200}`, capacity `{1500,2500,4000}`, demand `{900,1400,2100}` — so a number's
value settles which role it plays. It collapses the vehicle and bare groups
entirely.

**Adjacency** is the mechanism that already resolved the capacity pronoun,
applied to a second referent. Once the registry says *which* bare quantity is the
demand, the **needs site is the lone region immediately preceding it**: *"A
request has come in from region_3. It is for 1400 kg of supplies."* No content
word is consulted — only document order and type signature.

> **60.6% decided at 2.5 worlds** puts this inside the ≤4-world band that
> `notes/findings/2026-08-19-carrying-ambiguity-is-always-sound-and-rapidly-vacuous.md`
> identified as the regime where a bound is actually actionable. Position is a
> crutch, and a value list plus recency replaces it.

## Where the structural signal genuinely runs out

The residual is **depot versus flooded** among the two leftover regions — 2.5
worlds on average, and exactly that distinction.

Both readings are internally coherent, both give different answers, and no value
signal separates them: `depot` and `flooded` are both bare region mentions with
no quantity. Adjacency does not help either, because neither is bound to a
quantity that would locate it.

**This time the boundary is established rather than assumed.** The last one I
claimed turned out to be a missing branch in my own code, so this one is stated
with what was tried: signature, position-free adjacency, value vocabulary, and
domain invariants (depot never flooded, needs never flooded — verified over 200
cases and useless, because any assignment of three roles to three distinct
regions satisfies them automatically). What would close it is *relational*
knowledge — that a depot is where vehicles start, that flooding is an event — and
that is a different kind of external knowledge from a value list.

## Stated honestly

- **The registry is the generator's own draw sets**, so the 36.4% row is a
  ceiling on what a value vocabulary buys. Ablatable, so the assumption is
  visible.
- **Adjacency is a property of this surface's discourse.** The demand follows its
  region mention here; a document that stated the demand first would defeat it,
  and the mechanism is recency rather than understanding.
- **60.6% decided is a bound, not an answer.** A caller still gets "one of these,
  we cannot say which" on 1.18 vehicles per case.
- **40 cases, one domain.**

## Reproduce

```python
signature_worlds(text, registry=VALUE_REGISTRY, adjacency=True)
```
