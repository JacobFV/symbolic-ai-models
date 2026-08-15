---
date: 2026-08-14
author: lead
status: provisional
related: [2026-08-14-the-curriculum-has-one-object-sort,
          2026-08-14-five-of-seventeen-node-types-are-dead,
          2026-08-13-vendor-verbatim-rather-than-rename,
          2026-08-13-generator-templating-limits-transfer,
          2026-08-14-generation-is-parse-tree-infilling]
---

# The curriculum draws words by part of speech and nothing else, and that is the substrate every result here sits on

## The defect, in one line of code

`symbolic_ai_data/generators/base.py`:

```python
objs.append({"id": f"o{i}", "color": rng.choice(COLORS), "shape": rng.choice(SHAPES), ...})
```

Six colours, six shapes, six names, **drawn independently**. A red cube and a
purple rod are equiprobable. `alice` and `frank` are interchangeable. There is no
fact of the matter about which adjective goes with which noun, because nothing
ever made them differ.

Two agents hit the consequence from opposite directions on the same day, neither
looking for it:

- **`006`:** every entity symbol in an episode collapses into a **single
  metavariable component**. `alice`, `apple` and `manipulate` share a type. Only
  `Nat/Str/Chr/Prop` are rigid and those come from literals. A typechecker had
  nothing to check.
- **`005`:** **five of seventeen** declared node types never occur; the type head
  is a 9-way problem wearing a 17-way name.

Put that beside what was already measured — a type floor of **0.860** reachable
from tree shape alone, **0.54 bits** of long-range order structure at d=128 where
real English prose has ~0, and 179 rigid templates on which a lookup with **no
parsing in it** beats every compositional parser — and the diagnosis is one
sentence. **The models are not the binding constraint and neither is the harness
any more. The curriculum is.**

## The change

Impose **semantic** constraint on top of the existing syntactic and procedural
structure, sourced from one or more real knowledge graphs. A lesson anchors some
of its free variables outright, and the rest are bound by walking a **dependency
DAG**: once `o0` is a *penguin*, what it can be coloured, where it can be, and
what it can do are no longer uniform draws.

What that buys, and each item is currently missing rather than weak:

- **Node labels carry information.** Today a label is a token identity and
  nothing else, which is why capacity spent on symbol identity is measured as
  wasted. Under a KG a label has a class, a hypernym chain and relations.
- **The type head becomes a real question.** It is currently a tree-shape lookup
  that nothing has beaten; `metta_type-005` read what a node *contains* and moved
  +0.201 and still lost to the floor.
- **Generation becomes falsifiable.** You cannot score "the red idea sleeps
  furiously" as wrong when nothing says an idea has no colour. See
  [[2026-08-14-generation-is-parse-tree-infilling]].
- **Inference gets something to infer.** A dependency DAG means some answers are
  *derivable* rather than *copyable*, which is the first mechanism proposed here
  for moving the copy ceiling rather than approaching it.

## The four rules this change has to obey, and why each has already been paid for

### 1. Beside, never instead — at the *data* level

`RESEARCH_LOG.md`'s central convention is that a new model is registered beside
its predecessor, because editing one in place silently redefines every published
number carrying its name. **That has already happened twice with models.** A
curriculum change is the same hazard with the blast radius of the entire repo:
*every* number here is defined on the current generator.

So the KG curriculum is a **new, separately named curriculum**, both registered,
and a sweep prints rows on both. `symbolic_ai_core/data/fingerprint.py` hashes
179 lessons x 5 seeds x 7 languages and fails if any cell moves — **that test
firing is the guard working, not an obstacle**, and it must not be regenerated to
make a change quiet.

### 2. The scrambled-KG control, and it is load-bearing

A KG makes the data *denser* as well as *meaningful*, and those are different
things. The control is a **degree-preserving edge permutation** of the same
graph: identical node count, identical degree distribution, identical density,
correspondence to meaning destroyed.

This is exactly the control that carried today's strongest embedding result —
`vsa_hks_shuf_pure-004` permutes the signature rows across nodes, preserves the
Gram's value multiset bit-identically, and falls from +0.107 to −0.071. Without
its analogue here, "semantics helped" cannot be told from "more structure
helped" or from "the model memorised the KG".

### 3. The copy ceiling must be recomputed, and the renaming column changes meaning

**The ceiling is a property of the curriculum, not a constant.** It is 0.7305
because 71.9% of scored answers sit on a visible node of the same episode. Adding
derivable answers changes that fraction by construction, so every "share of
reachable signal" claim in `RESEARCH_LOG.md` must be recomputed rather than
carried across. (It also has to be recomputed on its own denominator — the
published 0.7216 was over `label_n` and quoted against a head scored over
`copy_scored_n`.)

Subtler and more important: **renaming stops measuring what it measures now.**
Today a permutation of all 2,105 symbols is nearly free for a structural model
*because symbol identity carries no information*. Under a KG it carries real
information, so the equivariance column stops asking "did it memorise the
vocabulary" and starts asking "did it use the semantics". That is a **better**
measurement and it is **not the same one**. Old and new renaming numbers are not
comparable and must not be tabulated together.

### 4. Vendor it verbatim, and treat it as an oracle nobody here wrote

The WALS integration is the precedent worth copying: 640 rows of coding this repo
did not author, which is what let it grade the language representation against
something with no stake in the outcome. A vendored KG has the same property. Same
rules as `symbolic_ai_data`: verbatim, licensed, byte-identical test, no runtime
dependency on an external service.

## What would refute the whole idea

- **The scrambled control matches the real KG.** Then the gain is density or
  degree, the semantics never mattered, and this is an expensive way to make the
  curriculum harder. Cheapest possible death; run it first.
- **Every model's score simply drops.** A harder curriculum that reorders nothing
  has told us nothing. The interesting outcome is a **reordering** — some method
  that was mid-table becoming first because it can use semantics.
- **The KG leaks the answer.** If a model can recover the KG from training
  episodes and the "semantic" win is lookup, this reproduces the repo's oldest
  mistake in a new costume. The guard is the same one already used: a model that
  wins must still win when the symbols are permuted *and* the KG permuted with
  them.
- **Coverage.** If only a handful of the 179 lessons can be given semantic
  constraints, the effect will be diluted to nothing by macro-averaging over
  lessons that did not change. Measure the share of lessons the KG can reach
  **before** building models on it.

## Rejected

- **Replacing the current curriculum.** Rejected on rule 1.
- **Generating a KG from the curriculum's own vocabulary.** Rejected: it would be
  this repo grading its own homework, and the whole value of an outside oracle is
  that nobody here wrote it.
- **Waiting for the large KGs before building anything.** Rejected. The *seam* —
  a dependency DAG that binds variables under constraint — is testable with a
  small vendored graph now, and swapping a larger one in later is a data change
  rather than a design change. Building the seam first also means the scrambled
  control exists before the first flattering number does.
