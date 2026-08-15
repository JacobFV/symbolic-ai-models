---
date: 2026-08-15
author: agent-r090
status: provisional
related: [2026-08-14-the-mask-rate-curve-moves-the-opportunity-not-the-ability,
          2026-08-14-generation-is-parse-tree-infilling,
          2026-08-13-the-renderer-is-deterministic,
          2026-08-13-a-ranking-is-a-property-of-a-metric,
          2026-08-14-an-unmeasured-confound-has-an-unknown-sign]
---

# The render bound was the wrong way round, and rung 4 is not answered after all

**All 179 lessons, 711 scored evaluation episodes, `mask_rate=0.15`,
`mask_mode=scatter`, `runs/refit-node-r015` — a from-scratch refit whose
`final`, `floors`, `renaming` and `masking` blocks are bit-identical to the
published `runs/infill-node-r015`, and whose `episode_labels_exact` reproduces
the published 0.0380 / 0.0338 / 0.0295 / 0.0281 / 0.0281 / 0.0225 to the digit.**

## The claim, and why it does not follow

`notes/findings/2026-08-14-the-mask-rate-curve-moves-the-opportunity-not-the-ability.md`
and `scripts/graph_exact.py` both said:

> The render is a deterministic function of the term, so
> `exact_match <= graph exact-match`.

Determinism gives the **opposite** implication. A function maps equal inputs to
equal outputs, so *a graph that is exactly right renders to text that is exactly
right*:

    exact_match  >=  graph exact-match.

The published inequality needs the render to be **injective** — two different
terms never rendering to the same text. Nothing in this repo has measured that,
and `notes/findings/2026-08-13-the-renderer-is-deterministic.md`, which is the
note it leans on, establishes only that the render path performs no random draw.
It is a claim about determinism and was read as a claim about injectivity.

The failure is concrete, not pedantic. A hidden symbol that the prose never says
can be predicted wrongly at **no cost to the rendered text**, so an episode can
have a wrong graph and a right render.

## The bracket, measured

`scripts/graph_exact.py` now also scores the surfacing side: a fill *surfaces* if
its symbol is a word of the prompt, and `surf exact` is the share of episodes
whose surfacing fills are **all** right, the rest free. Under the natural
implementation of rung 4 — patch the true term at the masked positions with the
model's predictions and render, which is the only version in which the graph's
own lossiness (`max_nodes`, float rounding, exploded strings) does not
contaminate the measurement — `lbl exact` bounds `exact_match` from below and
`surf exact` estimates it from above.

| `mask_rate=0.15` | `label_acc` | `lbl exact` | surfacing | acc on those | **`surf exact`** |
|---|---:|---:|---:|---:|---:|
| `corefer-001` | 0.357 | 0.0380 | 0.667 | 0.426 | **0.1505** |
| `ptrgen-001` | 0.336 | 0.0281 | 0.667 | 0.402 | **0.1449** |
| `routes-001` | 0.323 | 0.0281 | 0.667 | 0.382 | **0.1392** |
| `vsa_perm-002` | 0.326 | 0.0338 | 0.667 | 0.367 | **0.1266** |
| `evidence-001` | 0.219 | 0.0225 | 0.667 | 0.262 | **0.0999** |
| `grammar-001` | 0.187 | 0.0295 | 0.667 | 0.183 | **0.0661** |
| `corefer-001` at 0.90 | 0.181 | 0.0000 | 0.676 | 0.216 | **0.0014** |

**A third of all scored fills never appear in the prompt at all**, so the
inequality is not just backwards, it is loose: `corefer-001`'s rung-4 number
lies somewhere in **[0.038, 0.15]**, and 0.15 is one episode in seven rather than
"essentially unachieved". At `mask_rate=0.90` both ends are ~0 and the ladder's
conclusion is safe; at 0.15, which is the setting every published number in this
repo is measured at, it is not.

And the ranking moves again. On `lbl exact`, `grammar-001` (0.0295) beats
`ptrgen-001` and `routes-001` (0.0281). On `surf exact` it is last of the six by
a wide margin, because its accuracy on the fills that actually reach the page is
0.183 against `corefer-001`'s 0.426. Third metric, third ordering.

## What the upper end rests on, stated rather than buried

`surf exact` assumes **a symbol reaches the rendered text only if its own string
is a word of that text.** Both failure directions are real and neither has been
measured, so this is `an-unmeasured-confound-has-an-unknown-sign`:

- a symbol that surfaces through a lexicon or a number word would be missed, and
  the estimate is then too high;
- a symbol that coincides with a prompt word without being printed by *this* node
  is counted, and the estimate is then too low.

Per node type, the share whose symbol is a word of the prompt:

| type | n | surfacing |
|---|---:|---:|
| `num` | 821 | 0.922 |
| `token` | 127 | 0.882 |
| `char` | 102 | 0.745 |
| `pred` | 1,749 | 0.695 |
| `field` | 386 | 0.588 |
| `ident` | 2,023 | 0.537 |

Nothing here is 0.000 or 1.000, which is what a clean proxy would look like. The
**lower** bound needs no assumption and is the part to quote: `exact_match` is at
least 0.0380 for `corefer-001` at 0.15, and the published claim that it is at
most 0.0380 is wrong.

## The judgement call: rung 4 is worth running, and not in this session

The previous agent's reasoning was *the bound already establishes the
conclusion, so the number is not worth the compute*. With the bound pointing the
other way that reasoning is gone, and the honest state is: **rung 4 is open, and
the interval is wide enough to change what the ladder concludes.**

It is still not the best next hour, because it is implementation and not compute:

- `Episode` carries `prompt` and `graph` and **no term**, so the render needs the
  episode regenerated from `(lesson_id, seed)` and a map from graph index back to
  term node. `graph_from_json` is a bounded BFS with several fiddly cases —
  `record`/`app` fields sorted into their own nodes, `str` exploded into `char`
  pieces and truncated, the whole walk cut at `max_nodes` — and the map has to
  reproduce all of them.
- There is no `from_json`, so the patch has to be applied to the `Term` itself
  rather than to `Lesson.structured`'s JSON.

What makes it tractable is that it is **self-verifying**: patch with the *true*
labels, render, and require the result to be byte-identical to `ep.prompt` on all
716 episodes. Any error in the index map shows up as a mismatch, so the machinery
cannot be silently wrong — which is exactly what "its own correctness burden"
was worrying about. That guard should be the first thing written, before any
model is scored.

Recorded as the recommendation rather than done: the priority this session was
the 0.90 split, and correcting a published inequality that points the wrong way
is worth more than a number that inherits it.

## What would refute this note

- An injectivity argument for the render that I have missed, which would restore
  `exact_match <= graph exactness`. It would have to explain how a symbol absent
  from the prose changes the prose.
- The surfacing share coming out at 1.000 under a proper measurement — every
  hidden symbol reaching the page — which would collapse the bracket to a point
  and make the two numbers agree after all. Measured by the proxy it is 0.667.
- The end-to-end render landing outside [0.038, 0.15]. Below 0.038 would refute
  the determinism argument itself; above 0.15 would refute the proxy.
