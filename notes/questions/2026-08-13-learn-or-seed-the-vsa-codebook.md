---
date: 2026-08-13
author: lead
status: open
related: [2026-08-13-a-real-pretrained-seed, 2026-08-13-seeding-balance-not-provenance]
---

# The codebook should be seedable *and* learnable, and neither has been tested properly

`vsa-002` draws its codebook at random and is exactly equivariant.
`vsa_seeded-002` draws it from co-occurrence and is a null (-0.007 acc,
+0.003 bits) — and its own codebook test says why: sign-quantising a random
projection of sparse co-occurrence only doubles average off-diagonal similarity,
so the seed is weak by construction. **Neither variant tests the real question.**

Two untried directions, and they are not alternatives:

**Seed it from work already done.** A GPT-2 embedding table or a curated word
graph, sign-quantised into the same interface, changes nothing else in the model.
Re-deriving structure that exists is a cost, not a thesis.

**Learn it.** Fit hypervectors so symbols that behave alike are close, dense at
fit time, unchanged at run time — the cost thesis is untouched because inference
is still elementwise ops over one vector. The three seeding nulls say curated
*provenance* has not paid; they say nothing about a codebook fitted to this task.

Keep both: a seeded codebook that stays replaceable by a learned one is the
point, since the aim is to skip re-derivation rather than to freeze the structure.
Every seeded variant registers beside its from-scratch control or we cannot tell
what it bought.
