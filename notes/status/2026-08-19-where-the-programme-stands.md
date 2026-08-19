---
title: Where the programme stands — an executive summary
date: 2026-08-19
status: assessment
---

An assessment of the whole bet, written at the end of a long session on reading,
checking and cost. Not a finding: no new measurement is introduced here, and every
number is cited from a note under `notes/findings/`. What it adds is the shape —
what has been established, what it costs, how it sits against the existing
narrative about symbolic AI, and what should happen next.

---

## 1. The bet, and what the evidence now says

The bet is a **language-understanding substrate whose cost per correct answer is a
different order of magnitude from neural inference, and whose reasoning is
inspectable rather than inferred.**

| claim | status |
|---|---|
| symbolic reasoning is cheap | **true and nearly vacuous** — flood's decision is a polynomial max-min Dijkstra, solvency's is a sum; only scheduling justifies a solver at all |
| the cost advantage is real | **true but narrow** — per answer, at inference time, *on a task a reader already exists for* |
| reasoning is inspectable | **true, and much weaker than advertised** — explanations are wrong more often than answers |
| the world can be read from text | **this is the whole problem, and it is unsolved** |

The single most important number is the stage split: reading is **1.9% / 0.9% /
96.1%** of wall clock across flood, scheduling and solvency, and error
concentrates wherever the signature is ambiguous. **We have priced reading, not
reasoning.** The thesis silently assumed the first was free.

---

## 2. The trajectory, in four moves

### Move 1 — from leaderboard to pipeline

The repo began as 51 scored models on a 179-lesson curriculum that is
teacher-forced and 98.6% scaffolding: it was measuring memorisation. The pivot to
`text → world IR → kernels → answer + explanation` was right and is now complete
across three domains with genuinely different shapes — a set answer over a routing
graph, a boolean over a bitemporal sum, and an NP-hard packing.

### Move 2 — the benchmark was easier than it looked

**Every distractor in all three domains was inert by construction.** Flood's
reader *admits* its disused-track distractor on 60/60 cases and it never mattered,
because the generator pointed it at regions appearing nowhere else. Scheduling's
and solvency's readers never even type theirs (0/60 each).

| domain | published | **honest** | with the components built since |
|---|---:|---:|---:|
| flood | 0.988 | **0.679** | 0.933 |
| scheduling | 1.000 | **0.790** | 1.000 |
| solvency | 1.000 | **0.450** *(floor 0.550)* | 1.000 |

Solvency on the honest surface was **worse than answering "no" every time**, and
its `$/solved-above-floor` was literally `inf` — it had bought nothing.

### Move 3 — a theory of self-checking

The part most likely to be a real contribution:

> **Soundness is a property of the pairing (channel, check), never of the check.**
> **Detection** needs a *second reading* of the same fact and is gated by the
> role's **arity**. **Insensitivity** needs a decision that provably ignores the
> claim and is gated by **aggregation**. A multi-valued role inside an aggregating
> decision admits neither — and that is exactly where the damage is.

With prices attached, via `cost.break_even_wrong_cost`: flood's certificate pays
if a wrong answer costs **0.595** of a right one, scheduling's at **2.948**,
solvency's membership certificate is **free**. And the sting: **the detectable
errors are the harmless ones.** Arity has nothing to do with damage.

### Move 4 — first contact with real text

168 Wikipedia company intros against Wikidata `P749`, with *former* parents
labelled by `P582`. Four regexes get **0.369** against a **0.696** ceiling — and
the repo's most distinctive idea did not survive the trip.

---

## 3. How this sits in the existing narrative

### Against the GOFAI post-mortem

The standard story is the knowledge-acquisition bottleneck and brittleness. We
reproduced it **with numbers** rather than as history: reasoning free, reading
everything, and maintenance the term that stops it amortising. But we also found
something the standard story does not say — **the brittleness was hidden by the
evaluation, not merely tolerated by it.** A hand-built benchmark contains
hand-built distractors, and hand-built distractors are the ones the author already
knew how to reject. That should generalise well past this repo.

### Against the neuro-symbolic pitch

The usual claim is *symbolic = verifiable, symbolic = explainable*. Both need
qualifying:

- **Verifiable only along channels with redundancy**, and redundancy is a property
  of the domain's arity, not of anyone's effort. A multi-valued fact that nothing
  corroborates cannot be checked.
- **Explainable is not free.** The complete renderer fabricates on **7.6%** of the
  answers it gets *right*; solvency's stated total is wrong on **98.5%** of cases
  while its verdict is wrong on 48.5%. At a **0.1% reading error the answer is
  perfect and the explanation is wrong 985 times in 1,000**, because a derived
  figure is wrong whenever *any* input is while the answer is wrong only when the
  error crosses a decision boundary. **An explanation's error rate is not bounded
  by the answer's.**

The constructive half is the interesting one. **A certified answer is explained
honestly for free** — 0.022 falsehood against 0.378, and it cites *no*
uncorroborated link — because certification and load-bearing-ness are questions
about the same thing. And where you cannot verify, you can **mark**:
`render.uncorroborated` flags **88 of 88** fabrications inside **7.5%** of the
text.

### Against "just scale it"

The ledger says no accuracy closes the price gap on a task a reader exists for —
break-even accuracy is **337 to 1.3M×**, and accuracy cannot exceed 1. But the
claim is narrow in exactly the way that matters: it says nothing about a task
nobody has written a reader for, which is what a general model is bought for.
Break-even **episode counts** are 0.9M–2.2M at $1,000 of engineering, and
**maintenance is unpriced** — a reader revised whenever the surface changes never
finishes amortising.

---

## 4. The uncomfortable part, which is the useful part

On real prose, the ideas this repo is proudest of underperformed the one it
dismissed.

| feature | precision |
|---|---:|
| **position — take the first match** | **0.626** |
| crude entity typing | 0.609 |
| candidate agreement *(emit-don't-collapse)* | 0.603 |
| mention-count ranking | 0.535 |

**Everything that *replaced* position lost.** The only things that beat it are
*filters over* it — pattern strength and corroboration, composing to **0.735**.

> **Position was an artefact there and is a signal here.** In a generated surface
> the ordering is imposed by a template: destroyed by shuffling, therefore a leak.
> In an encyclopedia intro it is **editorial convention**, stable across documents
> written by independent authors, therefore a feature. The separating test is the
> one this repo already runs: **does shuffling destroy it?**

Likewise, *emit rather than collapse* transfers nothing to real text because
**agreement is a test for mutually exclusive alternatives**, and real prose
supplies none — *Sony Music Entertainment* and *Sony Music Group* are one answer at
two granularities. **Corroboration** does transfer (0.718 against 0.346, graded by
mention count) because it is a property *of one* candidate rather than of the
relation *between* them.

Three independent routes name the same missing capability — **entity resolution
and entity typing**. Agreement fails because names are not resolved; ranking fails
because non-entities are not filtered; and the whole signature discipline works at
all only because entities are called `region_0`. **Ambiguity mass on real prose is
≥ 0.44 against the 0.000 the generated surfaces post**, because a signature never
looks at the **verb**.

---

## 4b. Addendum, after the strategic correction: the reader's target is an equivalence class

The frame was reset mid-session to a single question — *what information must be
recovered, with what fidelity, for cheap structured computation to remain useful?*
— with the formalism `X --R--> Ŵ --K--> Y` and `W₁ ~_K W₂ ⟺ K(W₁) = K(W₂)`. Four
arms followed, and they changed the shape of the argument more than anything
earlier in the day.

**The standard extraction metrics are worthless for this.** On 130 flood cases,
claim recall, claim precision and raw symmetric-difference size all rank a correct
answer ahead of a wrong one at **AUC 0.506 / 0.473 / 0.506** — chance. The reader
makes 2.2 errors on the cases it gets right and 2.3 on the ones it gets wrong.
**Critical error mass** — influential claims in the symmetric difference — reaches
**0.946**, and one direction is exact: **zero mass ⇒ correct, 82/82**. That is a
characterisation of `[W]_K`, not a predictor of it.

**The milestone was met.** 168 independently authored intros → three relation
families → one world → a composed query (`parent JOIN country`) whose answer no
sentence states. It scores **F1 0.138**, against per-relation accuracies of 0.819
(country), 0.327 (parent) and 0.241 (headquarters). Two things fall out: **a
composed query is bounded by its weakest relation**, and **set-valued composition
degrades faster than the product of its parts** — 0.268 expected per company, 0.138
achieved, because misses and false positives accumulate on both sides rather than
averaging.

**And the controlling quantity took three narrowings, each forced by a
measurement.** `d`, the share of claims whose loss changes the answer, spans
**0.010 to 0.866 on identical claims** across existence / argmax / union queries —
so the value of task-weighted reading is ≈ `1/d`, and at `d ≈ 0.01` an existence
query makes 99% of reading effort irrelevant. But *why* moved three times:

1. **aggregation shape** — refuted, because `d` did not swap when the enumerated
   and filtering relations were exchanged;
2. **value redundancy** — right variable, wrong form: `P(sole support)` predicts
   `parent` (0.922 vs 0.866) and fails completely for `country` (0.000 vs 0.574);
3. **bridges times path survival** — `d(country) ≈ 0.922 × 0.589 = 0.543` against a
   measured 0.574, a reliability quantity rather than an aggregation property;
4. and finally **bridges over the *error* distribution**, because the structural
   share on flood is **0.245** against **0.169** for the reader's actual errors —
   a phantom link is more likely to be redundant than a real one, so the offline
   number is an upper bound and over-states by 1.4×.

**What did not survive contact:** entity resolution supplied as a given buys
nothing — only **1.2%** of candidate pairs are the same entity, so the granularity
story behind three earlier conclusions was unrepresentative. And the value-of-
information rule `d·(1−acc)` is directionally right and quantitatively weak: a
measured gain ratio of **16.0** against a predicted **5.45**.

## 5. Where the next stretch should go

1. ~~**Entity resolution as a given.**~~ **Done, and it buys nothing** — 1.2% of
   candidate pairs are the same entity. Entity **typing** helps a little (the
   ranker's largest single gain, 0.535 → 0.638). ~~The missing primitive is
   relation typing.~~ **Corrected by the residual taxonomy:** 51% of the errors
   are **non-organisations** and direction errors are essentially absent, so the
   lever is the **typer's recall** — it rejects *BBC* and *Bertelsmann* — plus
   more ownership patterns. Two of the remaining errors are evaluation defects, so
   the 0.696 ceiling is itself slightly low.
   **Patterns: done.** Naming the latent category — *state* of ownership versus
   *event* of transfer — and ordering by it beats growing the list: state-first
   with an event fallback is **strictly better on all three columns** than the
   published reader (0.601 / **0.393** / 0.653 against 0.589 / 0.369 / 0.626), and
   with corroboration reaches **0.750** precision. Event-only precision is 0.304
   against state-only's 0.683, which is what earns the ordering. **The typer's
   recall is the one remaining named build.**
2. **A second real genre.** Every correction to the shared components came from
   *adding a genre*, never from thinking harder: the cue list was 85% false
   positives on real English and needed three passes, each surfacing a different
   dominant error. SEC filings are the genre solvency imitates and are one line
   from unblocked — EDGAR requires a contact email in the `User-Agent`, which is
   the user's to give.
3. **Stop reporting accuracy without its explanation-fidelity column.** The two
   come apart, they are governed by different variables, and only certification
   aligns them.
4. **Re-run anything measured on the default surfaces.** `hard_distractors=True`
   and the accumulating readers are the honest settings now.

---

## 6. Health of the process, stated plainly

3,792 tests green. Roughly thirty findings written in the session this summarises,
of which **six were refutations of predictions made in advance** and **four were
corrections to numbers published hours earlier** — including a bug in a metric
shipped that same morning. That rate is high, and the honest reading is that the
benchmark had been too easy for a long time rather than that the work is unstable.

Hold the published numbers loosely. Hold the **laws** — arity governs
detectability, aggregation governs certifiability, explanation error is unbounded
by answer error — more loosely still: they are two- and three-point fits.
