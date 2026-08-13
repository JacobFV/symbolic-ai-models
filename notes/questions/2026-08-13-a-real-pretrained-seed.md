---
date: 2026-08-13
author: lead
status: idea
---
`vsa_seeded-002` is a null (-0.007 acc, +0.003 bits) and its own codebook test
says why: sign-quantising a random projection of sparse co-occurrence only
doubles the average off-diagonal similarity, so the seed is weak *by
construction*. That asks for a real table (GPT-2 embeddings, WordNet) rather than
refuting seeding. Needs a local download; the interface takes one unchanged.
