---
title: The streaming path is bounded end to end — 400 episodes from a 6-trillion-address split cost 271 KiB against 473 KiB from a 24-address one — and the tokenizer no longer needs a corpus
date: 2026-08-19
author: lead
status: provisional
tags: [streaming, training, memory, infrastructure]
---

## What was already done, and what was not

`symbolic_ai_core.data.stream` gives batches from a keyed permutation with a
bounded window and a resumable cursor, and `tests/test_streaming.py` (18 tests)
covers most of the streaming requirements: sample-key replay, disjoint worker
shards, a pinned finite eval split, resume-at-the-same-next-key, and constant
memory on a 10^12-address split.

**That last test iterates `ds.keys()` only.** Enumerating addresses cheaply is
worth nothing if turning an address into an *episode* materialises the corpus
behind it, and nothing measured that. `build_tokenizer` also still took a
`Sequence[Episode]`, so fitting a vocabulary required the corpus to exist.

## Measured end to end

`symbolic_ai_models/streaming.py`, `peak_bytes_for` — peak traced bytes
**generating episodes**, not keys:

| | tiny — 24 addresses | huge — **6,000,000,000,000** | ratio |
|---|---:|---:|---:|
| 40 episodes | 418.2 KiB | **239.5 KiB** | **0.57×** |
| 400 episodes | 473.4 KiB | **271.0 KiB** | **0.57×** |

> **Resident memory is independent of the address space, and of how much is
> drawn from it.** A 6-trillion-address split costs *less* than a 24-address one
> — the finite split does extra epoch bookkeeping — and drawing 10× the episodes
> costs 13% more, which is the bucketing window and nothing else.

## The tokenizer no longer needs a corpus

`fit_tokenizer_from_stream` fits from a bounded prefix of the stream, keeping the
same two-part budget the materialising version uses — pieces from prose, then
whole node labels, because a label like `o2` is two pieces in text and must land
on one id for the masked-node head to name it.

**1024 ids from a 64-episode prefix of 6e12 addresses**, and a test requires two
fits of the same prefix to agree exactly: the order is a pure function of
`(dataset, split, epoch, worker)`, so the prefix is the same on any machine and
after any interruption. A shuffled index array cannot have that property once it
no longer exists.

## What is deliberately not done

**`train()` is untouched**, and that is a scope decision rather than an
omission:

- Fifty-one published models depend on that path.
- **Floors and one-pass rule induction genuinely want the whole training set.**
  A floor fitted on a prefix is a different floor, and this repo has more dead
  claims from floors than from anywhere else.
- Only the **batch-consuming** learner benefits from streaming, and that is the
  neural control, which `CLAUDE.md` keeps off by default.

So this closes the named requirement — bounded memory, deterministic replay,
resumable cursor, tokenizer from bounded samples — **without claiming it changes
capability**, and the trainer can adopt it when a learner exists that wants it.

## What would refute it

- **`tracemalloc` measures Python allocations**, not RSS. A C extension holding
  memory outside the tracer would not show up. The ratio across two address-space
  sizes is the claim, and it is measured the same way on both.
- **Six lessons, not 179.** The address space is virtual either way, but episode
  generation cost per sample is a property of the lesson mix.
- **The prefix determinism test compares two fits in one process.** Cross-process
  stability rests on `keyed_seed`, which `tests/test_streaming.py` covers
  separately.

## Reproduce

```bash
uv run pytest tests/test_streaming_training.py
```
