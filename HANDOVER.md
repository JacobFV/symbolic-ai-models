# Handover — 2026-08-18 (second revision, after the certificate arm)

For the next agent picking this repo up cold. `ROADMAP.md` says what the work
*is*; `CLAUDE.md` says how to work here; this says **where the live edge is, what
is already known so you do not re-derive it, and what is believed but unproven so
you do not inherit it as fact.**

Read in this order: `CLAUDE.md` (working agreements — they are binding and they
were each paid for), `APPROACH.md` (the argument), then this, then `ROADMAP.md`.
`notes/lessons/` is the shortest path to not repeating six specific mistakes.

---

## 1. Where the live edge is

The programme pivoted on 2026-08-18 from *model zoo + language curriculum* to a
**typed world-program runtime over real federated data**. The curriculum is a
development harness, not the benchmark. The live frontier is:

> **Maintaining an answer instead of re-deriving it: what an answer actually
> depends on, how much smaller that is than what the computation read, and what
> the difference is worth per corpus update.**

That is a move from the previous revision's frontier ("computing with
disagreements no source is entitled to settle"), which is not abandoned but is
no longer where the open questions are. The move happened because the
certificate arm found that the *only* claim of ours that survived a realistic
opponent — naming what an answer rests on — is worth **0.3x to 1.0x** the way
the previous handover proposed building it, and **13,987x** built differently.

The corpus that made it measurable is new: **two filed SEC 13F snapshots**,
December 2025 and the quarter after, 2,282,570 → 2,360,678 holdings edges,
333,014 positions closed and 411,122 opened, 8,425 filings. It is the first real
corpus *update* this repo has had, as against a corpus. Everything in §3b was
measured on those bytes and nothing in it is injected.

## 2. What is built

| thing | where | what it does |
|---|---|---|
| `fuse`, `prefer_measured`, `ClaimGroup` | `symbolic_ai_core/runtime/fusion.py` | groups competing claims, ranks by derivation, **refuses a tie**, retains the mixture |
| `possible_answers` | `symbolic_ai_core/runtime/ambiguity.py` | answers under every consistent world; refuses an explosion rather than truncating |
| `possible_answers_scoped` | same | **answers under only the conflicts the query reads.** The read set is discovered by handing the computation a recording assignment — no annotation, no static analysis |
| `additive_bounds`, `Bounds` | same | exact, attained extremes for a sum of independent per-subject terms, in linear time |
| `exposure`, `rank_by_exposure` | same | what a conflict costs *before* enumerating it |
| `AmbiguityExplosion.read` | same | a refusal that **names the conflicts the query depends on** |
| `certify`, `revalidate`, `RecordingStore` | `symbolic_ai_core/runtime/certificate.py` | the same recording trick over **facts** rather than conflicts: run a computation once against a mapping that remembers, and its dependency set is the answer. Works on an arbitrary computation, including one that shells out to clingo |
| the tasks | `symbolic_ai_tasks/` | `ultimate_parent`, `company_key`, `cross_source_alignment`, `airport_country`, `range_limited_routing` |
| the experiments | `scripts/gleif_scoped_ambiguity.py`, `gleif_ambiguity_ladder.py`, `alignment_bounds.py`, `ambiguity_advantage.py`, `retrieval_rounds.py`, `gleif_fund_exposure.py` | every number in §3 |

Tests: `tests/test_ambiguity.py` (38), `tests/test_fusion.py`,
`tests/test_certificate.py` (17), `tests/test_witness.py` (12). Full suite
**3,394 passed, 10 skipped**. One test in that run was a ~25% flake that raced
the solver against itself; it is fixed and verified over 25 runs.

## 3. Measured. Do not re-derive these.

They are on disk, they are reproducible by the scripts named above, and
re-running them to confirm is the thing `CLAUDE.md` tells you not to do.

**Computing with a retained mixture** —
`notes/findings/2026-08-18-a-query-pays-for-the-conflicts-it-reads-and-4992-of-them-cost-one.md`

| | 251 conflicts (filed vs filed) | 4,992 (closure vs filed) |
|---|---|---|
| `possible_answers` on the whole world | refused (2^251) | refused (2^4992) |
| scoped: point queries | **117,129 in 0.3 s** (2.8 µs) | same |
| conflicts read per query | p50 0, **max 1** | p50 0, max 1 |
| answers undetermined, with alternatives | 253 (0.216%) | **5,006 (4.274%)** |
| anchor: scoped == full enumeration | 410/410 | 410/410 |
| retention vs collapsing | **2.8x** | **3.4x** |

**Where the query reads everything** — `additive_bounds`: 598 ambiguous
SEC→GLEIF alignments give a US-domiciled count of **[2824, 3062] in 2.4 ms**
against 2^598 worlds; bounds equalled enumerated extremes **3,273/3,273** times.

**The solver rung** —
`notes/findings/2026-08-18-the-solver-rung-is-needed-on-15-hubs-out-of-3044.md`.
On concentration beneath a hub, the **maximum is closed-form** and the
**minimum is NP-hard**. Over 3,044 hubs the cheap lower bound is already exact
on **99.5%**; the solver changes the answer on **15**. 3,044 exact optima in
**1.6 s** (1.29 clingo calls/hub), largest a 2^197-world mixture. `#minimize`
over `#max` did **not finish in 13 minutes**; the decision-problem encoding
takes 1.6 s. *The price of a kernel is the price of its encoding.*

**The cost argument, and what it is worth** —
`notes/findings/2026-08-18-the-advantage-curve-was-mostly-the-framing-and-what-is-left-is-a-constant.md`
and
`notes/findings/2026-08-18-retrieval-can-certify-determinacy-in-four-rounds-what-it-lacks-is-a-stopping-rule.md`

| opponent | $/query | advantage |
|---|---:|---:|
| handed the whole corpus (the old published framing) | $61.18 | 5.01e12 |
| **realistic agentic retrieval** (ideal recall, 2.08 rounds) | $4.10e-02 | **3.36e9** marginal, 1.30e9 amortised |
| oracle retrieval (already knows the dependency) | $6.15e-04 | 5.03e7 |
| us, workload of **one** query, ingest included | $2.26e-06 | **271x** |

Necessary context for a point query: **41 tokens** mean (p50 32, max 288)
against 4.08M for the corpus. Retrieval over-fetches **46x**. Four query classes
spanning five orders of magnitude of naive advantage land within **1.2x** of
each other once both sides pay for the dependency.

**Topology** — GLEIF ownership is a wide shallow forest: 92.2% leaves, chain
length p50 2 / max 10, amplification **1.0x**. Exposure spans **1 to 3,848**
inside one relation, so the cost of a conflict is a property of *the node*, not
the graph. The route network is the opposite (amplification 8.3x–44x).

## 3b. Measured on the 13F update. The certificate arm.

Four findings, in the order they were run, each correcting the one before it.
Scripts: `cert_maintenance_13f.py`, `cert_freshness_13f.py`,
`cert_dependency_size.py`, `cert_bound_asymmetry.py`, `cert_witness_path.py`.

**Per quarter, a read-set certificate is worth nothing, and often less.** Four
query classes spanning four orders of magnitude of compute cost, all certified
by one generic mechanism with no per-query rule:

| query class | read set | compute/answer | speedup | survive | **advantage** |
|---|---:|---:|---:|---:|---:|
| `holder_count(S)` | 1 | 748 ns | 0.6x | 33.0% | **0.3x** |
| `is_widely_held(S,100)` | 1 | 739 ns | 0.7x | 33.0% | **0.3x** |
| `portfolio_overlap` | 2 | 6,048 ns | 3.7x | 0.4% | **0.6x** |
| `min_filers_covering(12)` | 12 | 6,745,104 ns | **1,582.6x** | **0.0%** | **1.0x** |

Speedup and survival are **anticorrelated** — the read set that makes a
certificate cheap to check is the one that makes it likely to be hit — and they
cancel to ~1.0x. A query-supplied **stability margin** survives 93.6% against the
read set's 33.0%, and that is the rung the recording mechanism cannot produce.

**Per filing it is worth 37x to 1,342x**, and the quarterly row is the far end
of that curve, not the value of the mechanism. 8,425 filings, 89.3 keys each
(0.185% of the corpus). The whole-quarter endpoint reproduces the table above
(0.36 / 0.71 / 1.00 against 0.3 / 0.6 / 1.0), so the two experiments agree.

**The ceiling, verified on both axes independently:**

```
advantage = min( compute/check , 1/P_hit ),    P_hit ~ r x keys_per_update / total_keys
```

Sweeping `r` 1→48 with the kernel fixed: 364.8x → 11.7x, meeting the `1/P`
prediction at 11.3x. Sweeping kernel cost over six orders of magnitude with `r`
pinned at 1: the advantage rises and then **saturates at that sample's ceiling**,
269.7x measured against 269.5x predicted. **Cost decides only whether the ceiling
is reached; dependency size is the ceiling.**

**And the recorded read set is not the dependency.** On shortest co-holding path
the BFS read 1,328.6 keys where the claim depends on 0.5 — an over-approximation
of **6,591x**. Once the certificate is minimal, the **complete answer** `= d`
(not a bound) is maintained at **13,987x**:

| certificate | dependency | P(hit)/filing | advantage |
|---|---:|---:|---:|
| witness (the path's edges) | 2.5 edges | 0.0034% | 29,182x |
| optimality — **recorded** frontier | 1,328.6 keys | 30.6067% | **3.3x** |
| optimality — **hand-derived minimal** | 0.5 keys | 0.0046% | 21,534x |
| **full answer** (witness + minimal) | — | 0.0071% | **13,987x** |

Set cover's 95x witness/optimality gap **survives** this attack because its
optimality read set genuinely *is* the dependency; shortest path's does not.
Whether a recorded read set is tight is a property of the **problem**, and
nothing in the mechanism tells you which case you are in. A second agent
measured the same over-reading independently on the route network the same day
at **66x**.

**And the 13,987x is an artefact of the instance.** The route network at a
2,000 km limit has a real diameter (hops p50 6), and the minimal optimality
dependency — computed meet-in-the-middle, the strongest honest version — grows
with the ball while the witness grows linearly:

| d | witness | minimal optimality | ratio | % of graph |
|---:|---:|---:|---:|---:|
| 2 | 2 | 4 | 2.0x | 0.01% |
| 4 | 4 | 152 | 38.0x | 0.56% |
| 6 | 6 | 876 | **146.0x** | 3.21% |
| 10 | 10 | 8,745 | **874.5x** | **32.08%** |

Overall 148x against 13F's 0.2x; control, the `d <= 2` pairs, median 3 edges and
comparable to 13F. So **the settled statement, after four corrections in one
day**, is:

> An existential claim's minimal dependency is the size of its **witness**,
> which grows linearly in the answer. Its universal complement's is the size of
> the **search space that has to be excluded**, which grows with the ball.
> Logical form decides the growth *rate*; the instance decides whether you have
> gone far enough along it to notice.

The bound/answer asymmetry is therefore the **general** case and the 13,987x the
special one — which makes the set-cover note closer to right than the note that
corrected it, for a reason neither had.

Anchors, all of which had to be zero and were: 15,300 answers recomputed on the
new snapshot with **0 false survivals** on every rung; 300/300 cover witnesses
well-formed; 222/300 path witnesses intact with **0** failing to chain.

**The opponent throughout** re-derives every answer per update, which is what an
LM or retrieval agent must do and is emphatically **not** what a database would
do. Against incremental view maintenance (DBSP, differential dataflow) these
advantages would be far smaller and possibly inverted. What survives that
comparison is narrow and should be stated narrowly: this gets delta-proportional
maintenance for an **arbitrary computation including an external solver**, with
no per-query delta rule.

## 3c. The constant we retracted is the amortisation constant

`notes/findings/2026-08-18-the-framing-factor-we-retracted-is-the-amortisation-constant.md`

Every advantage number in §3 and §3b begins at the **second** arrow of
`APPROACH.md`'s thesis. All 19 catalogued sources arrive already structured —
verified across the 14 GB: every table is `(id, label, kind, body, source_url)`
or `(source_id, target_id, kind)`, `body` is key-value metadata or empty
(patentsview's 8.5M bodies are 0 characters), the longest natural-language field
in the corpus is a **patent title** at 59.4 chars mean, and courtlistener is a
77M-edge citation map with no text column. So `observations -> typed world` has
never been priced and there is nothing on disk on which it could be.

Pricing it needs no experiment:

```
breakeven = (corpus_tokens x rate) / (dependency_tokens x rate)
          = corpus_tokens / dependency_tokens = 4.08e6 / 41 = 99,512 queries
```

— identical on both price sheets, because our per-query cost is eleven orders
below either. **99,512 is the 99,738x in §5**, the factor retracted as "just the
framing", to within 0.23% rounding. They are the same quantity by construction.

The retraction was right about the claim and wrong about the number. Handing a
model the whole graph *per query* is indefensible; handing it the whole graph
*once* is the **build step**, and it is what our side gets for free. So:

> The symbolic advantage is an **amortisation argument** and always was. The
> ~5e7 per-query figure is real and lives entirely on the far side of a
> crossover nobody had located. At 13F's 32% quarterly churn, a corpus that must
> be re-extracted needs **~350 queries a day** to stay ahead of its own
> rebuilding.

**Boundary condition of the programme, stated precisely.** The advantage is
measured and large where structure is **already filed** — regulatory,
bibliographic, geographic — because a registry paid the extraction cost and
externalised it, which is why nothing published here is wrong. It is
**unmeasured** where structure must be **derived from observation**, which is
the domain `APPROACH.md` names as the target.

## 3d. The first arrow, measured

`notes/findings/2026-08-18-the-first-arrow-is-cheap-and-bad.md`. §3c named
acquiring a raw-observation corpus as the highest-value data need. There is one:
**5,000 OpenAlex works, 5,992,167 characters of abstracts, 44,446 affiliation
strings** at `data/sources/openalex-prose/`, paired with the ROR institution ids
OpenAlex resolved them to. It is the first raw prose this repo has held.

**The crossover does not transfer; the dependency does.**

| | GLEIF ownership | OpenAlex prose |
|---|---:|---:|
| **dependency per query** | **41 tokens** | **302.3 tokens** |
| crossover | 99,512 queries | **5,242 queries** |

The formula held and the number moved **19x**, because `corpus` scales with
corpus size — **never quote the crossover as a constant across corpora**. The
corpus-independent term is the dependency, and that is the re-pricing §4 asked
for: **7.4x larger on prose**.

**Extraction, work-disjoint split, 11,954 held-out strings of which 84.1% were
never seen.** A ladder of four rungs, each reported as a fraction of a ceiling
the task itself imposes:

| | F1 unseen | % of ceiling | precision |
|---|---:|---:|---:|
| memoriser | 0.000 | 0% | 0% |
| v0 component vote | 0.303 | 42.2% | 29.1% |
| v1 + IDF | 0.377 | 52.6% | 39.9% |
| v2 + word-overlap fallback | 0.366 | 51.0% | 36.1% |
| **v3 + specificity-first** | **0.379** | **52.9%** | **54.7%** |
| *ceiling* | *0.717* | *100%* | *72.8%* |

**The ceiling is the most useful number and was not designed for.** On strings
seen *verbatim*, agreement is only 58.1% exact / F1 0.717, because OpenAlex
assigns institutions **per author** rather than per string — the label is not a
function of the input. Anything above 0.717 is using more than the string.

**A cost comparison that does not need the credentials §6 is blocked on**, by
bounding the model at perfection: 14,091 ns / **$7.83e-11** against **$4.56e-04**
for input tokens alone. Per *correct* extraction that is **≥1,766,210x whatever
the model scores**, since it cannot exceed F1 1.0.

> **The first arrow is cheap and bad.** F1 0.379 builds a world that is mostly
> wrong, and a millionth of the price does not repair it. Three principled
> improvements over the naive dictionary bought +0.077 and left 47% of the
> ceiling unreached, so the weakness is real rather than a lazy first attempt.
> Every advantage in §3, §3b and §3c sits downstream of this.

Two things inside the ladder outlive its top line: **v2 made it worse** — a
fallback firing where the extractor knows least, guessing worse than abstaining,
the same shape as the largest harness effect in this repo's history — and **F1
is insensitive to the operating point**, so the precision/recall *frontier* is
the object.

**CORRECTION, same day.** The 0.717 "ceiling the task imposes" was **my own task
construction**: the fetcher flattened authorships, labelling each raw string with
every institution its author listed. Re-fetched preserving the boundary (new
snapshot beside the old), the ceiling is **F1 0.988 / 98.2% exact** — the label
*is* a function of the input. The correction makes this **harsher**: the
extractor misses 51% of an *achievable* target, not 47% of a noisy one. The
ladder now **measures** its ceiling from data rather than pinning a constant,
which is what would have caught it.

## 3e. Knowledge beats data, and still plateaus

`notes/findings/2026-08-18-a-zero-shot-registry-beats-a-learned-dictionary-and-both-plateau-at-62-percent.md`

The residual was localised to generalising to an unseen *wording*, so the
registry was the obvious test of this repo's stated principle that **external
resources are givens**. ROR: **135,710 institutions, 449,658 name variants**,
CC0, unauthenticated, now at `data/sources/ror/ror-v2.11-2026-08-03/`.

Three splits, because the ladder had been iterated six times on one. Mean % of a
measured ~0.99 ceiling:

| v0 learned | v3 best learned | **v4 zero-shot registry** | v5 hybrid | **v6 + abbrev/containment** |
|---:|---:|---:|---:|---:|
| 38.2% | 47.4% | **54.2%** | 59.8% | **62.3%** |

**Ordering identical on all three splits, and the tuned split gives the lowest
v6** — the tuning debt did not bite, which is measured rather than assumed.

> **Positive:** a **zero-shot** registry lookup — no training split, no learned
> dictionary, no fitted parameter — beats the best dictionary learned from 3,500
> works on **every** split (+0.039, +0.103, +0.059) at **41,668 ns against
> 96,915**. It is the only rung with nothing to tune.
>
> **Negative:** six rungs and an authoritative registry still leave **38% of an
> achievable ceiling** unreached.

**The diagnosis was sharper than the ladder and it was wrong.** *One* string in
6,489 produced no candidate, so the extractor fails at **choosing**, not finding
— "University of Wisconsin" names thirteen ROR campuses. I concluded the
discriminating evidence was geography sitting unread in the string, promoted it
to §7 item 1, and built it. **It does not work** — see §3f, and read that section
before repeating any part of it.

## 3f. The composition failed, and the control caught it

`notes/findings/2026-08-18-a-second-view-that-undoes-a-mistake-without-being-worth-making-one.md`

Names propose, geography disposes: the first deliberate two-view composition in
this repo, on a problem that needed one. Means over three splits:

| variant | mean F1 | vs v6 |
|---|---:|---:|
| **v6** names only, abstains on ambiguity | **0.618** | — |
| B — abstention relaxed, **no** geography | 0.582 | **−0.036** |
| v7 — relaxed **+** geography | 0.611 | −0.007 |
| v8 — v6's abstention kept, geography may only **admit**, on city/subdivision only | 0.617 | −0.001 |

**The ablation is the finding.** Relaxing abstention costs −0.036; geography
recovers +0.029 of it, **81%**, and never gets ahead.

> **A second view informative enough to undo a mistake and not informative
> enough to be worth making one.** It has to beat *abstention*, not merely beat
> guessing — a higher bar than the architecture makes it look.

**The control, written before the run**, is why this is a finding rather than a
regression explained away: geography changed **9.8%** of answers and was better
on **23.0%**, worse on **46.4%**.

**Why:** 65% of ambiguous components carry no geographic evidence at all.

**And the expensive part.** I designed this arm from **five printed examples** out
of 1,251 disjoint cases; all five named a city, and the population does not. The
65% was computable from the same error breakdown before any variant existed.
That is a **slice inversion**, this repo's oldest documented mechanism, walked
into while writing a finding that cites the abstention lesson twice. Guard in
`notes/lessons/2026-08-18-i-designed-an-experiment-from-five-printed-examples.md`:
*a diagnosis derived from a slice must be sized on the population before it is
built on.*

What survives: the ~62% plateau is now a **harder** number, because it withstood
a serious attempt at its diagnosed cause. And **abstention won three times in one
session** — v2's word-overlap fallback, B's relaxed admission, and this.

## 3g. The two arrows priced together, and a metric inversion

`notes/findings/2026-08-18-the-extractor-that-wins-on-facts-loses-on-every-answer.md`

The first experiment in this repo that charges cost to the **system**, as
`CLAUDE.md` requires. Two worlds over 5,000 OpenAlex works — the reference from
OpenAlex's labels, the extracted from the zero-shot registry extractor.

**Error amplifies 1.85x, and recall is what dies.**

| query | Jaccard | precision | recall | amplification |
|---|---:|---:|---:|---:|
| `institutions_of(work)` | 0.544 | 83.9% | 43.8% | 1.00x |
| `works_at(institution)` | 0.331 | 94.1% | 42.1% | 1.47x |
| `collaborators(institution)` | **0.157** | 84.0% | **20.4%** | **1.85x** |
| `works_at_count` | — | — | — | **100% median rel. error** |

Precision holds; recall collapses, because the extracted world has **half the
entities** (2,270 vs 4,539) — the extractor abstains on every ambiguity, and a
collaborator never extracted anywhere is unreachable by any union.

**So the operating point was chosen on the wrong metric.**

| | v4 abstains | v4r high recall |
|---|---:|---:|
| fact-level F1 | **0.576** | 0.455 (**−0.121**) |
| `collaborators` F1 | 0.328 | **0.413** (+0.085) |
| `works_at` F1 | 0.582 | **0.640** (+0.058) |
| count median rel. error | 100.0% | **50.0%** |

> **The extractor that wins on facts by 0.121 F1 loses on every aggregate
> query.** Aggregate queries pay for **completeness**, not precision.

This inverts a conclusion stated three times in one session, each time on
fact-level evidence alone. It is the repo's oldest trap in a new costume — *a
ranking is a property of a metric* — and the metric this programme has been
optimising corresponds to nothing a user asks for. **"No fallbacks — fail
loudly" still stands** (it is about *silent* fallbacks), but **world
construction and answer construction want opposite defaults**, and nothing in
the architecture says so.

**The ledger:** 0.9 s and **$5.08e-06** to build the world symbolically against
**$19.03** for a model reading the same text — **3,746,454x** — and the world is
57.6% right. Every advantage in §3, §3b and §3c is quoted over a world someone
else built.

## 3h. Where completeness stops winning, and where the filter breaks

`notes/findings/2026-08-18-monotone-queries-repair-a-noisy-world-and-non-monotone-ones-cannot.md`

§3g's queries were all set **unions**, which reward over-generation by
construction. Four classes chosen to punish it instead:

| query class | winner | Δ F1 |
|---|---|---:|
| `works_at_both(A,B)` — intersection | completeness | **+0.177** |
| `common_institutions(w1,w2)` — intersection *(n=26, no weight)* | completeness | +0.055 |
| `institutions_unique_to(w1,w2)` — **difference** | **precision** | **−0.117** |
| `is_single_institution(work)` — boolean *(inconclusive vs 65.8% floor)* | completeness | +0.033 |

The one class precision wins is the only **non-monotone** one: `A − B` is
antitone in `B`, so a spurious member of `B` **deletes** a true member of `A` and
nothing recovers it. **Same axis as the witness result** (§3b) — monotone claims
have small stable certificates and tolerate noise; their complements do neither.
Two unrelated arms, one axis.

**Then the falsifier, run the same hour.** The claim rests on error
*independence*, so partition `works_at_both` by whether the two institutions are
**registry-confusable** (a single ROR name maps to both; 4,604 institutions have
such a sibling):

| pair type | precision |
|---|---:|
| co-occurring (as first published) | **95.1%** |
| **confusable — correlated errors** | **8.1%** |

**95.1% → 8.1%**, below even the 36.5% fact-level rate.

> **Intersection repairs uncorrelated over-generation and amplifies correlated
> over-generation — and the extractor's noise is correlated with exactly the
> entities anyone would want disambiguated. Over-generation is close to free
> where you do not need disambiguation and ruinous where you do.**

The finding carries a banner at the overstated section; do not quote it without
the correction.

## 4. Believed, not measured. Do not inherit as fact.

Recorded deliberately, with mechanisms, so a later contradiction is a finding
rather than a surprise.

Both of the previous revision's parked predictions have now been **run, and
both fell** — see §5. What is parked now:

- **A corpus that mostly *shrinks* inverts the witness asymmetry.** The witness
  is monotone under additions and dies on deletion; 13F opened 411,122 against
  333,014 closed. On a shrinking corpus the witness should be the fragile half
  and the optimality claim the stable one. Cheap and unrun.
- **Most kernels here have a witness available and discard it.** The ASP kernel
  holds the model and returns only claims; the cover experiment had to
  re-extract the picked filers by hand. Confidence ~0.7, from reading the code.
- **The minimal path certificate is derived only for hops ≤ 2**, which is every
  case in that sample because the co-holding graph is nearly complete. On a
  graph with real diameter the minimal optimality set is the ball of radius
  `d−1`, which grows, and the 1.4x could open back up. **That is the experiment
  that would break the newest finding**, and it is the one to run first if you
  want to attack it.
- **The ~5e7 constant is a measurement, not a law.** It is the ratio of a fact
  in a kernel to a fact in a prompt, on one corpus whose facts are 20-character
  identifiers. A corpus of prose facts should move it. Still unrun.

## 5. Corrected this session. Do not quote the dead versions.

| was published as | what it actually is |
|---|---|
| "the advantage curve spans seven orders of magnitude, 1.85e11 on ultimate parent" | arithmetic right, framing load-bearing: **99,738x** of it was handing the model the whole graph. Against an opponent given only the dependency, four query classes are within **1.2x** at ~5e7 |
| "a retriever can only guess what the answer depends on" (mine, same day) | **wrong.** An ideal retriever certifies determinacy in **≤4 rounds**, zero misses. What survives: it has no **stopping rule** — at its natural stop it is silently wrong on **1.128%** of the world — and it over-fetches **46x** |
| "ambiguity does not propagate in this graph, 1.0x" | true of the 251 conflicts that occurred, false of the graph: the same conflicts on the highest-exposure nodes would contaminate **102x** more |
| "alternatives retained not collapsed" | held only inside the process until `to_dict` was fixed; retention died at the artifact boundary |
| "scoping buys little on a dense graph" (parked prediction) | **false on the filed-real mixture**: read p50 1, max 8, **0 refusals** in 250 queries, anchor 179/179. What breaks is **wall time** — 48.3 ms/query against GLEIF's 2.8 µs, 17,000x — and the governing variable is `conflict rate x read footprint`, not topology. GLEIF's 2.8 µs was a property of a two-fact query, never of a forest |
| "the corpus has no genuine two-source property conflict" (three findings) | **false**: four airports where openflights and geonames disagree on country and the disagreement survives ICAO agreement, name agreement and a self-incoherence filter — EUN, SMW, VIL (Western Sahara) and PRN (Kosovo). Broadest defensible count 8 |
| "make dependency-certification a substrate-wide contract" (this handover's own §7 item 1, previous revision) | the **lower-value half** of the right idea. Every kernel reporting its read set is worth **0.3x–1.0x** per quarter, and the read set over-reads the actual dependency by up to **6,591x**. What pays is a **witness** plus a **minimal** dependency, and neither is producible by the generic mechanism |
| "the lever is the logical form of the claim" (mine, two hours later) | **wrong.** The lever is the *true dependency* of the claim. The 95x NP/coNP gap on set cover is real; the 8,932x version of it on shortest path collapses to **1.4x** once the optimality certificate is hand-derived, and the rest was the BFS over-reading |

## 6. Blocked, and it needs a human

**Every accuracy comparison against a language model is unrun and stamped NOT
QUOTABLE** (`ROADMAP.md` item 0b). It needs paid API access. The cost rows in §3
dodge this by being *lower bounds* — input tokens only, zero output, perfect
accuracy — which is why they carry no equal-accuracy assumption. But "is the
symbolic answer *righter*" cannot be dodged forever.

**Second blocker — partly cleared, and what remains is a free signup.** §3d has
raw prose on disk now via OpenAlex, so the first arrow is measured. What is still
blocked is the *better* corpus: **CourtListener's v4 API returns 401** and both
bulk listings are closed (404 / 403). It is the best available test of this arrow
because its **77M-edge citation map is already in this repo as ground truth** and
citations appear in opinions as prose — a sentence-level extraction task, where
OpenAlex only offered a short-string one. A CourtListener API token is **free**
but requires registering an account, which is an outward-facing action under the
user's identity and not an agent's to take. **One signup unlocks the strongest
version of the programme's weakest measurement.**

The fork, which is the user's and not an agent's: **get credentials, or accept
that this programme publishes cost bounds and capability certificates and never
claims an accuracy win.** Do not quietly assume equal accuracy in a new row; that
assumption is what put four earlier rows out of quotation.

## 7. What to do next

Ordered, with the reason. A recommendation from the evidence, not a queue —
`CLAUDE.md` is explicit that the better experiment beats the next item, and the
previous revision's §7 item 1 is in the corrections table above, so this section
has a demonstrated failure rate.

1. ~~Break the newest finding on a graph with real diameter.~~ **Done, and it
   broke** — `scripts/cert_diameter.py`, §3b above. Left here so the next reader
   sees that this section's first item has now been right once and wrong once.
2. **Put a `witness` on `KernelResult`.** The 95x and the 13,987x are both
   currently properties of one script. `symbolic_ai_kernels/abi.py` already has
   the right shape (`check_entitlement` is the nearest analogue) and the ASP
   kernel already holds the model it throws away. The contract to ship is
   narrower than "report your read set": *return a witness where your answer has
   one, a minimal dependency where you can derive one, and say plainly where you
   cannot* — because a read set that reads like a dependency is worse than no
   certificate, being 6,591x wrong and looking right.
3. ~~Try hub labelling as a cheaper optimality certificate.~~ **Not run, and the
   reasoning is in
   `notes/decisions/2026-08-18-not-running-the-hub-labelling-refuter-because-the-ball-dominates-it.md`.**
   Maintenance cost is `|dependency|/|corpus|`, so any certificate whose
   dependency is the whole edge set is dominated by the ball — and both
   candidates are. The LP dual is constant in `d` but its validity is a
   conjunction over every edge; hub labelling is small per query but sound only
   via a **global** 2-hop-cover invariant whose verification is APSP-equivalent,
   making it a trusted index rather than a self-contained certificate.
   **Separator certificates are not disposed of by that argument and stay open**
   — on a graph with good separators, which an airline network is not.
4. ~~Get raw observations on disk.~~ **Done — §3d.** What is left is the
   CourtListener token (§6), which is a free signup and is the user's to make.
5. ~~Re-price the ~5e7 constant on a prose corpus.~~ **Done — §3d.** The
   dependency is 7.4x larger on prose; the crossover does not transfer at all. It is the last load-bearing
   number in the cost argument that has never been attacked, gutenberg and
   stackexchange are both on disk, and the mechanism (facts here are
   20-character identifiers) predicts it should move.
6. ~~Join geography to entity linking.~~ **Run, and it failed — §3f.** Do not
   repeat it without first sizing the signal on the population (65% of the
   cases it targets carry no geography at all).
7. ~~Price the two arrows end to end.~~ **Done — §3g**, and it inverted a
   conclusion stated three times the same day.
8. ~~Find where completeness stops winning.~~ **Done — §3h**, including its own
   falsifier, which cut the headline from 95.1% to 8.1%.
9. **The shrinking-corpus inversion.** One arm, and it is the falsifier for the
   witness asymmetry rather than another confirmation of it.

**What not to do:** more kernels (the data says stop at eight); more query
classes on GLEIF ownership; any further cost row against a hypothetical
opponent; any experiment whose write-up you could draft first; and — new this
revision — **any certificate work that reports a read set without asking whether
it is the dependency.** That question is now the whole of it.

## 8. Traps that cost time this session

- **`pkill -f <pattern>` matches the shell running it.** It killed my own
  command mid-edit. Kill by PID. There is already a lesson note about a pgrep
  watcher matching itself; this is the same trap wearing a different hat.
- **A `@property` that computes is not an attribute.** `UltimateParentTask.ids`
  sorts 117k ids; reading it inside a comprehension's *condition* made one loop
  100,000x slower. Now `functools.cached_property`. Look for the same shape
  elsewhere before trusting a timing.
- **A control that confirms your prediction to three significant figures is
  probably broken.** Mine reported 4,992/4,992 exactly as predicted; it was
  seeding the retriever's held set wrongly. Corrected to 1,321. Re-read any
  control that lands on your hypothesis too neatly.
- **The solver's cost is its encoding.** 13 minutes → 1.6 s from restating
  `#minimize`/`#max` as a decision problem plus binary search.
- **Python buffers stdout when piped.** Use `python -u` or you will watch an
  empty file for ten minutes and conclude the job is hung.

- **Backticks inside `git commit -m "..."` are command substitution.** A merge
  message this session lost the word `exposure` to it: bash printed "command not
  found", substituted empty, and committed successfully. Use a *quoted* heredoc,
  `<<'EOF'`. Lesson note:
  `notes/lessons/2026-08-18-backticks-in-a-git-commit-m-string-silently-delete-the-word.md`.
- **An anchor that fails 300/300 is probably the anchor.** Mine compared twelve
  witness edges against `k`, which is four to nine distinct *filers*. The
  mechanism under test was correct throughout, and the reflex on a total failure
  is to distrust the older, better-tested half.
- **A row that reports its neighbour's number to the digit is a bug, not a
  coincidence.** The full-answer certificate matched the minimal one at exactly
  116 because the witness is keyed on edges, the optimality set on adjacencies,
  and I replayed their union against the adjacency stream alone. Same shape as
  the trap two entries above it in this list.
- **The certificate results are stated against an LM-shaped opponent that
  re-derives everything.** They are not claims against a database. If you quote
  13,987x without that sentence you have published something this repo does not
  believe.

## 9. Verify the checkout in two minutes

```bash
uv run pytest tests/test_ambiguity.py tests/test_fusion.py \
              tests/test_certificate.py                         # 91 pass, <1s
uv run python -u scripts/gleif_scoped_ambiguity.py              # ~1 min, both mixtures
uv run python -u scripts/ambiguity_advantage.py                 # ~1 min, the cost table
uv run python -u scripts/cert_witness_path.py                   # ~3 min, the newest headline
uv run pytest tests/                                            # 3,371 pass, ~10 min
```

If `data/sources/gleif/...` is absent, every script above dies at load and
nothing else in the repo depends on those bytes.
