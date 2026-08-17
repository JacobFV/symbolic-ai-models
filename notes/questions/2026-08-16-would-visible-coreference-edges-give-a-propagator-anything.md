---
date: 2026-08-16
author: cart scouting arm
status: idea
related: [2026-08-16-infilling-errors-clump-but-do-not-cascade-and-cart-is-a-null]
---

# Would visible coreference edges give a propagator anything to propagate?

The CART null measured an oracle headroom of **+0.0066**: committing a
neighbouring hole's *true* label buys the surrounding holes 0.7 accuracy points,
which caps everything any propagator can win.

But `relation_matrix` **withholds the coreference edges of hidden nodes**, so a
`GraphView` cannot see that two holes are the same symbol. That is exactly the
constraint a propagator would most want, and the measurement was made with it
switched off. The headroom is therefore a lower bound on "what propagation could
buy" and an exact answer to "what propagation can buy *here*".

Cheap version: re-run the interventional cascade script on a view where the
hidden-hidden `same_label` edges are restored, and see whether the oracle
headroom moves off 0.007. It is a leak, so it is a **diagnostic and never a
model** — but a diagnostic that says "0.007 becomes 0.15" would reopen the whole
direction, and one that says "0.007 becomes 0.009" closes it for good.
