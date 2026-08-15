---
date: 2026-08-15
author: agent-r090
status: open
related: [2026-08-15-rung-fours-bound-points-the-other-way,
          2026-08-13-the-renderer-is-deterministic]
---

Rung 4's bracket is [0.038, 0.15] and its upper end rests on a proxy: *a symbol
reaches the rendered text only if its own string is a word of the prompt*. Per
node type that proxy gives `num` 0.922, `token` 0.882, `char` 0.745, `pred`
0.695, `field` 0.588, `ident` 0.537 — nothing near 0 or 1, which is not what a
clean proxy looks like.

**What would answer it, and it needs no model at all**: take a true episode,
change one node's symbol, re-render, and diff the text. Repeat per node type.
That is a direct measurement of which parts of the term the renderer prints, and
it turns the upper end of the bracket from an estimate into a bound. It also
answers whether the render is injective on the reachable set, which is the
property the original `exact_match <= graph exactness` claim needed and never
had.

Two things make it more than bookkeeping. `field` at 0.588 is the suspicious one
— field names are ordinary English words, so a coincidence rate that high is
plausible and would mean the upper end is too *low*. And `ident` at 0.537 is
38% of all scored fills, so whichever way it resolves moves the bracket most.
