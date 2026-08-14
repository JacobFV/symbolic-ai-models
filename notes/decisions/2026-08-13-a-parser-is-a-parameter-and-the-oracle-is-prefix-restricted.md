---
date: 2026-08-13
author: agent-ae944e68
status: measured
related: [compositional-parser, language-id-above-the-parser]
---

# A parser is a model parameter, and the oracle one is restricted to the prefix

## The fork

`tasks/lm.py` sets `rel=None`, so the text surface hands a model a flat token
chain and nothing else, while `masked_node` hands it the true term graph. Every
model that scores well scores on the graph. That leaves one question unanswered
and it is the important one: **is the text-surface failure a parsing failure or
a reasoning failure?**

Two ways to find out were available:

1. Build a better parser and see whether the reasoners improve. Rejected: the
   best exact graph recovery in `symbolic_ai_parsers` is 0.016, so a null would
   be uninterpretable — it would say "this parser is bad", which is known.
2. **Give the model a parser as a parameter and put an oracle in the slot.**
   Taken. The parser then becomes a measured variable rather than an assumption,
   and the oracle row is a *ceiling*: how well the reasoner would do if parsing
   were solved. If the ceiling is low, parsing is not the bottleneck and we stop
   investing there.

## The hypothesis, written before the numbers

**H**: with a perfect parse of the prompt, a structure-conditioned reasoner can
emit the answer token; without one it cannot. Concretely, `answer_acc` with the
oracle parser clears the LM answer floor by a wide margin and the same reasoner
on `template-002` / `retrieve-001` does not.

**What refutes it**: the oracle row scoring at or near its own floor. That would
say the reasoning, not the parse, is what is missing — and it would be an
argument for spending nothing further on `symbolic_ai_parsers`.

> **Outcome (added after the sweep):** the second half of H held emphatically —
> the same reasoner with no parse scores 0.000 and with a bag of words 0.030. The
> first half did not. `template-002` and `retrieve-001` *did* clear the floor, by
> +0.26 and +0.28, so the "without one it cannot" clause was wrong about real
> parsers as well as about the oracle. And the ceiling is only 0.387: a perfect
> parse still gets 61% of answers wrong. See
> `notes/findings/2026-08-13-a-perfect-parser-does-not-rescue-the-text-surface`.

**What would make it worthless**: the oracle reading the answer off the graph.
85.3% of answers on the full curriculum are literally a label of some node of
the episode's graph — 179 lessons, the sweep's own 3,580 training episodes, and
84.5% on its 716 eval episodes — so an unrestricted oracle would score
spectacularly and mean nothing.

## What "the structure of a prefix" means here — the core design decision

At position `t` the oracle may return only structure derivable from
`tokens[:t+1]`. The definition chosen, and it is the load-bearing choice:

> **The prefix parse is the true term graph restricted to the nodes whose symbol
> the reader has already read.** A node carrying label `L` is available at
> position `t` iff `L` has already occurred, as a complete word, in
> `decode(tokens[:t+1])` at least as many times as that node's rank among the
> nodes sharing `L`. A node carrying no symbol — `list`, `record`, `tuple` — is
> available once any of its descendants is. Unavailable nodes are deleted and
> their children re-attached to the nearest available ancestor.

The property this buys, and the reason it is the right definition:

**The oracle never names a symbol the model has not already read.** It supplies
*relations among seen symbols*, which is exactly what a parser supplies, and it
cannot supply vocabulary, which is what a leak would look like. A word still
being typed does not count — a prefix ending mid-word drops its last word, since
`fran` may yet become `frank` or `france`.

Two alternatives were considered and rejected:

- *Align nodes to text spans by the renderer's trace.* There is no trace; the
  renderer is vendored and structures and renders in two separate calls.
- *Return the true graph and mask the answer node.* Rejected outright: it needs
  to know which node the answer is, which is the thing being predicted, and any
  mistake in that masking is a silent leak of exactly the kind this repo has
  already been bitten by twice.

## Why the oracle is not registered in `symbolic_ai_parsers`

It is not a parser. `Parser` is `str -> Graph` and the oracle cannot be that: it
needs the episode's answer key. Registering it would put a by-construction
perfect row in the parser scoreboard next to rows that had to work for theirs.
It lives in `symbolic_ai_models/prefix.py`, is flagged `needs_truth = True`, and
is the only thing in the repo that is ever handed `meta["graphs"]` on a text
batch. Real parsers reach the same seam through `TextPrefix`, which adapts the
`symbolic_ai_parsers.Parser` protocol rather than duplicating it.

## Why the bare name does not resolve to the oracle

`gparse-003` is the *deployable* row (`template-002`). The ceiling is
`gparse-oracle`, a word-suffixed variant, which under
`symbolic_ai_core.registry` must be asked for by its full name. A sweep that
says `--models gparse` must not silently train the thing that cannot be
deployed and print it under the model's name — that is the `ptrgen-argmax`
failure, and the ceiling is a far more dangerous row to mislabel than a control
that is merely worse.
