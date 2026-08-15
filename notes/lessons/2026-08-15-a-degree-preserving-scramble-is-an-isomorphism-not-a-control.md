---
date: 2026-08-15
author: agent-kg-semantics
status: provisional
related: [2026-08-15-the-kg-arms-are-a-null-and-the-quarter-that-mattered-did-not-move,
          2026-08-13-a-control-that-could-fail,
          2026-08-14-a-kg-curriculum-may-need-a-model-that-knows-english,
          2026-08-14-an-unmeasured-confound-has-an-unknown-sign]
---

# A control the treatment cannot beat is not a hard control, it is the same experiment twice

## The mechanism

The repo's best habit is
[[2026-08-13-a-control-that-could-fail]]: build the condition under which the
signal cannot exist, and believe the result only if the control loses. The
failure mode nobody had written down is the mirror image — a control so strong
that **the treatment cannot win either**, because the two are the *same problem
under a relabelling*.

That is not a weak experiment. It is a **null by construction**, and it is
indistinguishable from a real null in every artefact it produces: the sweep
runs, the control's census matches, the table is flat, and the write-up says
"the semantics did not help" when what happened is that no experiment took
place.

## What happened here

The semantic-constraint line's control is a **degree-preserving edge
permutation** of the vendored graph: identical node count, identical per-node
in- and out-degree in every relation, identical density, taxonomy still acyclic,
lemma strings untouched, correspondence to meaning destroyed. It is a good
control by every check this repo has — and it was checked, node by node, in
`tests/test_kg.py`.

Then ask what a *learner* sees. Every model here trains on this corpus and
nothing else. What the binder hands it is: some kinds drawn from one family,
some attributes drawn from what the graph licenses for each kind, some verbs
admitted by an animacy. Under the scramble, all of those sets are different sets
— and they are **just as consistent across episodes**, just as concentrated,
just as large. A permutation of a fixed graph is a fixed graph. To a model with
no outside knowledge of English, "penguins license beaks" and "penguins license
tin sheets" are the same statement about symbols.

So the treatment and the control present isomorphic learning problems, up to two
residuals that are thin and were named in advance:

* **lemma strings.** The scramble permutes edges, not names, so in the real
  graph a family's members share morphology and in the scramble they do not. A
  model reading subwords or characters can see this; one treating symbols as
  atoms cannot.
* **higher-order structure.** Degree is preserved; clustering and assortativity
  are not. Which also means that if a treatment *had* beaten this control, the
  win would not have been attributable to meaning without a second,
  clustering-matched control.

Measured, on 179 lessons and 15 models: pooled `label_acc` differs by **+0.004**
on average, and on the non-copyable quarter — the part the whole line was for —
by **−0.001**, with no consistent sign.

## What it cost, and what it did not

It did not cost a wrong claim: the pre-registration
[[2026-08-14-preregistering-the-curriculum-arms]] put the odds of the control
matching at better than even and said why, before any arm ran, so the null
arrived already interpreted. That is the guard working.

What it cost is **four full sweeps and a curriculum** to establish something
that was derivable from the design. The pre-registration wrote the argument down
as a *risk*; nothing turned it into a *precondition*.

## The guard

Before building a control, ask the question one step further than "could the
signal be absent here":

> **Is there any channel by which the treatment could reach this learner that
> the control does not also carry?** Name the channel. If the only honest
> answers are "the strings look different" and "some third-order graph statistic
> differs", the experiment has no power and the control is an isomorphism.

Three practical consequences:

1. **A control that permutes structure tests knowledge the learner brought.** It
   is the right control for a *pretrained* model and the wrong one for a model
   trained from scratch on the same corpus, where it is guaranteed to tie.
2. **Where the isomorphism holds, the informative arm is the one that changes
   the learning problem rather than relabelling it** — for a KG curriculum,
   stating the graph's facts *inside* the episode so an answer becomes derivable
   from what is on the page, which is a different manipulation and has a
   different control.
3. **Say the expected power out loud in the pre-registration.** "I expect this
   to tie for a structural reason" is a sentence that should stop a sweep, not
   decorate it.
