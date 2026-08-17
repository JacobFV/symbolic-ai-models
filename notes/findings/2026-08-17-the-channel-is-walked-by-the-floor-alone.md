---
date: 2026-08-17
author: agent-refuter
status: measured
related: [2026-08-17-the-channel-is-walked-and-it-took-a-conjunction-of-three,
          2026-08-17-the-per-guard-floor-keeps-the-channel-and-drops-the-chosen-constant,
          2026-08-17-i-keep-blaming-a-pipeline-stage-for-a-property-of-the-objective,
          2026-08-14-a-score-can-be-the-back-off-wearing-the-models-name,
          2026-08-15-a-floor-outside-the-models-hypothesis-class]
---

# The 0.989 survives every attack I could make on it. "It took a conjunction of three" does not.

Sent to break the two `frontier-008` findings above. **The number is real and I
could not move it.** The mechanism story attached to it is wrong, and so is a
published lesson it leans on.

Everything here is my own refit under `runs/refute-a18/`, scored by
`scripts/derived_split.py`. Nothing under `runs/derive179-*` was touched.

**Evaluation hygiene, stated up front because every number below is an
evaluation-seed number.** The derived bucket only exists at seeds ≥ 1,000,000,
and "do not tune against evaluation" is the rule this is nearest to breaking.
Nothing here selects a value: the ablations set already-registered knobs to
already-registered values (`propose_support` to its `frontier-001` default 12,
`keep_by_path` to its `frontier-001` default `False`), and `frontier-009` takes
`relative_floor` at the default `frontier-008` already ships. No threshold was
searched and none was chosen by a derived-bucket score. What was read off
evaluation is an **attribution** — which of three already-shipped changes caused
an already-published number — and that is the only thing an audit of a published
result can be.

## What reproduced

`uv run symbolic-ai-models sweep --config configs/derive179.toml --curriculum
derive:wordnet --models frontier-008` from clean produces a `summary.json` that
is **equal to the published one on every field** — `label_acc` 0.44066501051,
`label_bits` 7.137037444, `type_acc` 0.853562421, all seven floors. The sweep is
deterministic to the last digit. `derived_split.py` on those weights:

| | `derive:wordnet` | `-perm` |
|---|---:|---:|
| `frontier-008` | **0.989** | **0.143** |
| `frontier-nomap` | 0.000 | 0.000 |
| derivation floor (lookup, told the premise) | 1.000 | 0.167 |
| blind marginal | 0.167 | 0.143 |

0.989 / 0.143 as published. n = 1,325 derived fills, 704 episodes, the same 11
carrying lessons, in both arms.

## Attack 1 — is any of it the shared back-off? No. None of it.

The sharpest available version of this test is to silence the model's own votes
and rerun: `node_votes -> {}` leaves `_forward_graph` mixing `(1-c)·backoff` with
`c = 0`, plus `structural_fallback`'s context prior. That is exactly the path
`a-score-can-be-the-back-off-wearing-the-models-name` is about.

| on the 634 derived, non-copyable fills of `derive:wordnet` | acc | bits |
|---|---:|---:|
| `frontier-008` | 0.9890 | 2.36 |
| `frontier-008`, votes silenced | **0.0000** | 10.10 |

The label head **fires on 634 of 634** — it abstains on none — and the mixture's
argmax equals the firing rule's prediction on **every one**. The shared
machinery contributes nothing here; there is no version of this number that is
the back-off wearing a name.

**And the lesson's own example is wrong on this bucket.** Four published models
score an identical 0.154574132 and the lesson reads that as the back-off. It is
not: refitting `brill-001` and `ngram-001` and silencing them gives

| | acc | silenced |
|---|---:|---:|
| `brill-001` | 0.154574 (98/634) | **0.000000** (0/634) |
| `ngram-001` | 0.154574 (98/634) | **0.000000** (0/634) |

The back-off scores **zero** on this bucket for every rule-based model, because
the answer symbol is by construction on no visible node and neither the unigram
nor `_node_context`'s prior ever proposes one of the six values. The four models
agree because their **own** votes land on the same 98 fills, not because they are
silent.

What they share is not code but an idea: `brill-001`'s baseline is "commonest
label per (parent head, slot)", a private modal-label table at a finer
resolution than the shared prior's, and the other three arrive at the same 98 by
their own routes. So the diagnosis in the lesson — "that is the shared back-off
wearing five models' names" — is wrong on this bucket, and the sentence
`frontier_001/model.py`'s module docstring draws from it ("**Not one model
produces a correct derived fill from its own machinery**") is false: four of them
do, 98 times each. The lesson's general point survives and is arguably better
served by the truth, which is four independently written modal-label baselines
converging to the digit. But "it is the shared fallback" is a testable claim and
the test says no.

## Attack 2 — the population. Matched, but not "identical by construction".

Same 11 lessons, same 704 episodes, same 1,358 derived positions, same 1,325
scored fills, same masking draws in both arms. `arms_for` puts treatment and
control in the same family and both print the same lesson list. That holds.

Two claims around it are stronger than the measurement:

* `configs/derive179.toml` says the copyable share is "identical by
  construction — checked in `tests/test_kg_derive.py`". Measured: **0.522** in
  the treatment against **0.530** in the control, so `acc | derived, not
  copyable` has **634** fills in one arm and **623** in the other. The test it
  cites asserts a ±0.05 tolerance, not identity. A permuted value can collide
  with an unrelated node elsewhere in the graph, and the collision structure is
  preserved only *among the derived objects*.
* `derived_split.py` prints its own void condition — the blind row "must sit at
  1/6 in **both** arms, or they differ in the marginal and not only in the
  conditional". It reads **0.1672** in the treatment and **0.1433** in the
  control. The arms do differ slightly in the marginal.

Both are ~1.5% effects against a 0.846 gap, so neither touches the conclusion.
They should stop being described as exact.

## Attack 3 — leakage. Clean, and the bucket is certifiably the derived bucket.

`_view` sets `labels[i] = None` and `types[i] = None` at every masked node;
`relation_matrix` zeroes a hidden node's `same_label` edges in both directions;
`siblings(i)` excludes `i`; `_path_labels` returns `MISSING` at any path landing
on a hidden node. `frontier` reads only the `GraphView` — never `batch.meta`
(which carries the prompt), never `batch.label_group` (which is built over
hidden nodes too, and would be a leak if any model read it). `copyable` means
what the bucket claims: `target_source[b, i]` is set only to a **visible** node
carrying the identical label string.

Independent certification of the population, which is worth more than the code
reading: collect the (kind sibling label → true answer) pair at every one of the
634 scored fills.

* `derive:wordnet` — **6 distinct pairs**, and they are the pinned map:
  `building→annex, auto→buffer, ship→bay, shoe→lace, body→abdomen, garment→arm`.
* `derive:wordnet-perm` — **36 distinct pairs**, 6 kinds × 6 values.

The bucket is the derived bucket, and the control removes exactly the
correspondence and nothing else.

## Attack 4 — the cross-fit. Sound, one false sentence, one latent hazard.

`fold.append(idx % 2)` with `idx` from `training_views(with_index=True)` is
stable across mask repeats: `idx = start + b` names the episode, so every repeat
of one episode lands in one fold. ✔

**Unremarked**: `generate` is lesson-major with the seeds inner, and `n_train`
is **20**, so `idx % 2 == seed % 2`. The two folds are exactly *even training
seeds* and *odd training seeds*, not an arbitrary split. It is harmless only
because the control's permutation is keyed on `graph|perm|lesson_id|seed`. Key
it on the seed alone with an odd `n_train` and episodes sharing a permutation
would straddle the boundary and the control would leak. Worth a guard.

**False, and now corrected in the docstring**: `_refit` claims "nothing about
which hypotheses survived depends on this pass". `_prune` runs *after* `_refit`
and `_Rule.dominates` compares `set(other.table) <= set(self.table)` — the
deployed, both-fold tables. The surviving rule set does depend on the refit. It
is benign (training fills only; the pass can only remove a rule and cannot raise
a held-out precision) but "benign" and "does not happen" are different claims.

## Attack 5 — the per-guard floor and noise. The void condition could not have fired.

The pre-registration says: if the treatment rises and the control rises with it,
the floor is admitting noise and the result is void. **That condition is not
diagnostic of what it was written to detect.** A rule fitted to noise on this
bucket still emits one of the six values and is right about 1/6 of the time,
which is indistinguishable from "chance" — so the control reads ≈0.14 whether or
not the floor admits noise.

Measured, and it does admit them: in `-perm` `frontier-008` fires on **623 of
623** fills, abstaining on none, through five `map` rules each right at about
1/7. The floor admits rules carrying no conditional information whatsoever, and
accuracy cannot see it.

What can see it is bits, and this is the number the control should have been
quoted with:

| `derived, not copyable` | acc | bits | its own silenced back-off |
|---|---:|---:|---:|
| `derive:wordnet` | 0.9890 | **2.36** | 10.10 |
| `derive:wordnet-perm` | 0.1429 | **9.28** | 10.09 |

In the control the rules buy 0.8 bits — the *marginal*, "the answer is one of
six values" — and none of the conditional. In the treatment they buy 7.7. That
is the separation the arm is really measuring, and it is much sharper than the
accuracy pair.

The floor also earns its keep, and here is the concrete case
`an-average-cannot-see-a-sub-population` asked for: 199 of the 950 label rules
have held-out precision below 0.5, and **290 of the 627 correct answers** come
from one of them — `[slot=1] -> map:sib@2`, p = 0.443, a table of **1,268**
entries — which is right **290 / 290** on the derived fills. An average over the
guard's whole population says 0.443; the sub-population says 1.000. Which is
also the honest description of what was induced: a 1,268-entry symbol→symbol
table at slot 1, six of whose entries are the planted map.

## Attack 6 — the conjunction. **Refuted.** It took one thing, not three.

The finding's stated methodological result — "single-factor ablation cannot find
a conjunctive cause… that is worth more than the number" — rests on seven
candidates that were all nulls. The single-factor ablation on the *winning*
model was never run. It was cheap. Run, on the 634 fills of `derive:wordnet`:

| variant | what differs from `frontier-001` | correct | acc |
|---|---|---:|---:|
| `frontier-001` (published) | — | 337 | 0.5315 |
| `frontier-002` (published) | `propose_support=2` | 337 | 0.5315 |
| `frontier-005` (published) | `keep_by_path` (soft) | 199 | 0.3139 |
| `frontier-006` (published) | both, floor still 0.5 | 337 | 0.5315 |
| **`frontier-001`, `min_precision=0.2`** | **floor only** | **618** | **0.9748** |
| **`frontier-001`, `relative_floor`** | **floor only** | **618** | **0.9748** |
| `frontier-007`, `keep_by_path=false` | floor + `propose_support` | 618 | 0.9748 |
| `frontier-008`, `keep_by_path=false` | floor + `propose_support` | 618 | 0.9748 |
| `frontier-007`, `propose_support=12` | floor + `keep_by_path` | 627 | 0.9890 |
| `frontier-008`, `propose_support=12` | floor + `keep_by_path` | 627 | 0.9890 |
| `frontier-007` / `frontier-008` (published) | all three | 627 | 0.9890 |

* **The floor alone moves the bucket 0.5315 → 0.9748.** A single sufficient
  cause, on the unmodified `frontier-001`, with either the constant 0.2 or the
  relative floor.
* **`propose_support = 2` is exactly inert.** Identical to six decimals with it
  on and off, in both `frontier-007` and `frontier-008`. The account in both
  findings — that a *two-atom* guard `[slot=1, nsib=2]` had to be proposed —
  does not describe the fitted model. There is no `[slot=1, nsib=2] -> map:sib@2`
  rule in it. The rule carrying the extra 290 fills is at the **one-atom** guard
  `[slot=1]`, which round zero proposes whatever the gate is.
* **`keep_by_path` is worth +0.0142**, and only once the floor is already
  lowered. With the floor at 0.5 it is worth exactly **zero** on the decision
  list — `frontier-006` has it and lands on `frontier-001`'s 0.5315 to six
  decimals — and on the soft readout it *costs* 0.129 (`frontier-soft` 0.4432 →
  `frontier-005` 0.3139).

And the floor-only model is *better everywhere else*, same curriculum and seeds:

| | `acc\|der,not` | control | `acc\|rest,not` | pooled acc | bits | type |
|---|---:|---:|---:|---:|---:|---:|
| `frontier-001` + relative floor | 0.975 | **0.111** | **0.299** | **0.4493** | **7.066** | **0.8637** |
| `frontier-008` | **0.989** | 0.143 | 0.277 | 0.4407 | 7.137 | 0.8536 |

Its control is *further* below chance than `frontier-008`'s — treatment −
control is **+0.864** against +0.846. Registered as `frontier-009` beside the
others, after the fact and labelled as such in its docstring; its swept
`summary.json` is **identical field for field** to the `--extra
{"relative_floor": true}` run these numbers came from, which is what says the
registration did not quietly become a different model.

## What this leaves standing, and what it does not

**Standing.** The channel is walked. 0.989 reproduces bit for bit, it is the
model's own rules end to end, the population is certifiably the derived bucket,
the control removes the correspondence and the score collapses to chance and
below, the in-class floor (`frontier-nomap`) is 0.000, and the derivation floor
that is *told* the premise is 1.000. Nothing I did moved any of it.

**Not standing.** "It took a conjunction of three, and that is why seven
candidates were nulls." It took one, and the single-factor ablation would have
found it — the seven nulls were seven variants that all left the floor at 0.5.
This is the next instance of
`i-keep-blaming-a-pipeline-stage-for-a-property-of-the-objective` and it is a
sharper one, because the lesson was already written and the fix still shipped
with two innocent stages bundled into the cause.

**One caveat neither note makes.** The treatment column contains exactly **six**
distinct (kind → answer) pairs. The 634 fills are 634 applications of six
learned table entries, not 634 independent tests, and a binomial interval on
627/634 is not an interval on the claim. "Six pairs is a small map" is named as a
weakness; that it is also the entire sample size for the induction is not.

## Verdict

Both notes should be **promoted on the number** — the 0.989/0.143 headline
survives an adversarial pass and is now independently refit and rescored — and
the mechanism section of `…-took-a-conjunction-of-three` should be **retracted
and rewritten** around the floor as a single cause.
