---
title: The ambiguity machinery has only met a shallow forest — the dense graph and a genuine cross-source property conflict are both available
date: 2026-08-18
status: idea
tags: [fusion, ambiguity, gleif, openflights, geonames, next]
---

Two arms the last two findings kept naming as their own limits, both buildable
from data already on disk.

**1. The dense graph.** Scoped enumeration, additive bounds and the solver rung
were all measured on GLEIF ownership: 92.2% leaves, amplification 1.0x, a query
reading a median of zero conflicts. The route network is the opposite extreme
already measured on this substrate (amplification 8.3x to 44x, dense and nearly
connected). Predictions worth writing down before building it: read sets there
will be *large*, so scoped enumeration refuses often; shortest path is not a sum
of independent per-conflict terms, so `additive_bounds` does not apply at all;
and set propagation — wrong on 19/19 pairs in GLEIF but only asked 19 times —
would be asked constantly. If scoping buys nothing on a dense graph, the honest
summary of both findings changes from "a query pays for what it reads" to "a
query pays for what it reads, **on a forest**".

**2. A real cross-source property conflict.** Every mixture measured so far is
either one source contradicting itself (GLEIF's 251 and 4,992) or an *identity*
ambiguity (SEC->GLEIF alignment). The retention finding's standing limit —
"two different sources disagreeing about one property is the case the federation
layer is really for, and the corpus still offers none" — may be wrong:
**openflights and geonames both carry a country for a place**, and the airport
task already aligns airports to countries. Aligning openflights airports to
geonames places (name plus coordinate, both sources carry both) would produce
genuine two-source disagreement about `core.country`, with `prefer_measured`
having nothing to rank on because both are measured. That is the first mixture
where the fusion registry's *original* purpose is exercised on real bytes.

Neither is started. Both are cheap enough to scout in an afternoon each, and the
second one would retire a limitation that three findings have now repeated.
