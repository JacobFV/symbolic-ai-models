---
date: 2026-08-16
author: agent-premise-selection
status: measured
related: [2026-08-16-premise-selection-preregistration,
          2026-08-16-once-deduction-is-exact-the-hard-part-is-premise-selection,
          2026-08-15-the-derivable-fill-is-worth-0833-to-a-lookup-and-nothing-takes-it,
          2026-08-16-the-derivability-channel-is-taken-and-the-price-is-the-vocabulary]
---

# Premise selection is free inside the object and costs 0.714 outside it

CoTu ([arXiv:2607.14735](https://arxiv.org/abs/2607.14735)) claims the residual
difficulty, once deduction is exact, is **premise selection**. The derived
bucket of `derive:wordnet` already had both ends of that ladder published: a
lookup **told** which sibling is the kind scores 1.000, the same lookup with the
sibling dropped scores 0.167. The 0.833 between them is selection and nothing
else. This ran the middle rung — the same table, choosing for itself.

Pre-registered at
`notes/decisions/2026-08-16-premise-selection-preregistration.md`, including
both readings, the control that would void the result, and the prediction that
the sibling scope would be uninteresting.

## The ladder

`acc | derived, not copyable`, n = 622 (treatment) / 593 (control), 8 masking
draws, eval seeds >= 1,000,000, selector fitted on training seeds 0..19 only.
Same positions, same filters and same denominator as the published rows.

| rung | candidates | `derive:wordnet` | `-perm` control | picks *this* object's kind node | picks *a* kind label |
|---|---|---|---|---|---|
| oracle premise — told the kind sibling | 1 (given) | **1.000** | 0.167 | 1.000 | 1.000 |
| self-selected, **scoped to the object** | 2.8 | **1.000** | 0.177 | 1.000 | 1.000 |
| self-selected, **whole visible graph** | 23.6 | **0.286** | 0.155 | 0.233 | **0.999** |
| blind — no premise | 0 | 0.167 | 0.143 | — | — |

The last two columns are the mechanism, and the gap between them is the finding.

The oracle and blind rows are the published ones, reproduced bit for bit
(`dfloor_n = 1345`, `blind_not_copyable = 0.16720257234726688`) by a config and
tokenizer rebuilt from `summary.json` — no weights survive under `runs/`, and
that reproduction is the gate the script aborts on.

**The control does not separate.** All four rungs in `-perm` sit between 0.143
and 0.177: a 0.034 spread, which is the empirical size of "nothing here". The
treatment's whole-graph excess over blind, 0.119, is 3.5x that whole spread; its
sibling-scoped rung is another 0.714 above again. In `-perm` the correspondence
is redrawn per episode, so there is nothing to select for, and the selector
duly finds nothing — at whole-graph scope it lands on the right node 0.5% of
the time.

The sharper form of that: in `-perm` the self-selected rungs sit **at the oracle
rung**, 0.177 and 0.155 against 0.167. Being told the premise is worth nothing
there, so choosing it badly costs nothing either. The whole ladder collapses in
the control, which is what it means for the treatment's ladder to be about
selection rather than about the lookup.

## Neither pre-registered reading won, and the third outcome is the finding

The note asked whether the middle row would land near 1.000 (selection trivial,
the difficulty is representational) or near 0.167 (selection is everything).
**It lands at both, and which one depends entirely on the candidate scope.**

The mechanism is legible and is the reason this is worth writing down. At
whole-graph scope the selector picks one of the six **kind** labels on **99.9%**
of scored positions — it has correctly identified *what sort of fact* answers
this question, out of 23.6 candidates and a vocabulary of thousands. It picks
the kind of the **right object** 23.3% of the time, which is 1/4, which is the
number of objects in a scene. It is, in effect, reading a uniformly random
object's kind.

The same two columns in `-perm` say the diagnostic is not vacuous: there the
selector lands on a kind label only 3.6% of the time, correctly reporting that
no sort of fact is useful when the correspondence is noise.

So the failure is not "it cannot tell a useful premise from a useless one". It
is that a label-keyed selector has no way to express *which object the question
is about*. It retrieves a true fact — `garment -> arm` really is a fact of this
corpus — about the wrong entity. That is exactly CoTu's residual, and it is
sharper than CoTu states it: the hard part is not ranking facts by relevance,
it is **binding** the fact to the question's argument.

## Why this is not an artefact of a weak selector

The selector scores a candidate by its evidence-shrunk mode probability,
`(max + a) / (total + 6a)`. If `a` were doing the work the number would move
with it. It does not: `acc | not copyable` at the whole-graph scope is 0.285,
0.286, 0.286, 0.283 for `a` = 0.5, 1, 10, 100 — a 0.003 range against a 0.714
effect. The sensitivity is computed by the reporting script itself, not by a
scratch one.

The two obvious leaks were closed before the run: hidden nodes are never
candidates (so the selector reads only what a model reads), and a candidate with
no training support predicts the blind marginal (so a bad choice costs the
conditional, never the marginal — the self-selected rung cannot fall below the
blind rung by construction). Both are asserted in
`tests/test_premise_selection.py`.

## What would have refuted it

Any separation in `-perm`. A self-selected rung above the blind rung there means
a within-episode leak and the treatment column would have been unreadable. It
did not happen: 0.155 and 0.177 against 0.143.

## What it changes

`notes/findings/2026-08-15-the-derivable-fill-is-worth-0833-to-a-lookup-and-nothing-takes-it.md`
should be read with one clause added. The 0.833 channel is **free** to a lookup
that already knows which object the question concerns, and 0.714 of it is
**unavailable** to one that does not. So it is not primarily a statement about
hypothesis language, and not primarily about search over hypotheses either — the
hypothesis space here is six pairs and the selector finds them. It is a
statement about **relevance scoping**: the expensive thing is the argument
binding, which is structural, and which the derived bucket supplies for free to
anything that reads the sibling relation and withholds entirely from anything
that reads labels.

That makes the pre-registered "representational" reading the closer of the two,
but for a reason the note did not anticipate: what has to be represented is the
scope, not the map.

## What is deliberately not claimed

This is a floor with an honest, no-learning selector. It is **not** commensurable
with `frontier-001` (0.532 treatment / 0.072 control on the same slice, premise
chosen by a learned guard) — that comparison is suggestive and untraced. Whether
`frontier-001`'s map form is buying the scoping rather than the map is the
obvious next question and this note does not answer it.

The candidate scopes are two points, not a curve. "0.714 of the gap is the cost
of 24 candidates instead of 3" is not established; what is established is that
the cost appears when the scope stops being the object.

Reproduce: `uv run python scripts/premise_selection.py runs/derive179-wordnet
runs/derive179-perm` — no model weights required.
