# Handover — 2026-08-18

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

> **GLEIF + SEC fusion: computing with disagreements that no source is entitled
> to settle, and pricing that capability against a language model.**

Two sources, 19 catalogued, 14 GB under `$SYMBOLIC_AI_DATA`, and one property —
"who ultimately owns this company" — where the data contradicts itself in a way
that is real, filed, and not synthetic. Everything below was measured on those
bytes.

## 2. What is built

| thing | where | what it does |
|---|---|---|
| `fuse`, `prefer_measured`, `ClaimGroup` | `symbolic_ai_core/runtime/fusion.py` | groups competing claims, ranks by derivation, **refuses a tie**, retains the mixture |
| `possible_answers` | `symbolic_ai_core/runtime/ambiguity.py` | answers under every consistent world; refuses an explosion rather than truncating |
| `possible_answers_scoped` | same | **answers under only the conflicts the query reads.** The read set is discovered by handing the computation a recording assignment — no annotation, no static analysis |
| `additive_bounds`, `Bounds` | same | exact, attained extremes for a sum of independent per-subject terms, in linear time |
| `exposure`, `rank_by_exposure` | same | what a conflict costs *before* enumerating it |
| `AmbiguityExplosion.read` | same | a refusal that **names the conflicts the query depends on** |
| the tasks | `symbolic_ai_tasks/` | `ultimate_parent`, `company_key`, `cross_source_alignment`, `airport_country`, `range_limited_routing` |
| the experiments | `scripts/gleif_scoped_ambiguity.py`, `gleif_ambiguity_ladder.py`, `alignment_bounds.py`, `ambiguity_advantage.py`, `retrieval_rounds.py`, `gleif_fund_exposure.py` | every number in §3 |

Tests: `tests/test_ambiguity.py` (38), `tests/test_fusion.py`. Full suite
**3,354 passed, 10 skipped** as of this handover.

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

## 4. Believed, not measured. Do not inherit as fact.

Recorded deliberately, with mechanisms, so a later contradiction is a finding
rather than a surprise.

- **Scoping buys little on a dense graph.** Predicted, not run, and the decision
  not to run it is in
  `notes/decisions/2026-08-18-drop-the-dense-graph-arm-and-measure-the-dependency-instead.md`.
  Expected: large read sets, frequent refusal, `additive_bounds` inapplicable to
  shortest path, set propagation asked constantly. **If you find otherwise,
  that is publishable.**
- **openflights and geonames may both carry a country for the same place**,
  which would be the first genuine *two-source property* conflict in the corpus
  — three findings in a row have said the corpus has none.
  `notes/questions/2026-08-18-the-same-three-mechanisms-on-a-dense-graph-and-a-real-cross-source-property-conflict.md`
- **The ~5e7 constant is a measurement, not a law.** It is the ratio of a fact
  in a kernel to a fact in a prompt, on one corpus whose facts are 20-character
  identifiers. A corpus of prose facts should move it.

## 5. Corrected this session. Do not quote the dead versions.

| was published as | what it actually is |
|---|---|
| "the advantage curve spans seven orders of magnitude, 1.85e11 on ultimate parent" | arithmetic right, framing load-bearing: **99,738x** of it was handing the model the whole graph. Against an opponent given only the dependency, four query classes are within **1.2x** at ~5e7 |
| "a retriever can only guess what the answer depends on" (mine, same day) | **wrong.** An ideal retriever certifies determinacy in **≤4 rounds**, zero misses. What survives: it has no **stopping rule** — at its natural stop it is silently wrong on **1.128%** of the world — and it over-fetches **46x** |
| "ambiguity does not propagate in this graph, 1.0x" | true of the 251 conflicts that occurred, false of the graph: the same conflicts on the highest-exposure nodes would contaminate **102x** more |
| "alternatives retained not collapsed" | held only inside the process until `to_dict` was fixed; retention died at the artifact boundary |

## 6. Blocked, and it needs a human

**Every accuracy comparison against a language model is unrun and stamped NOT
QUOTABLE** (`ROADMAP.md` item 0b). It needs paid API access. The cost rows in §3
dodge this by being *lower bounds* — input tokens only, zero output, perfect
accuracy — which is why they carry no equal-accuracy assumption. But "is the
symbolic answer *righter*" cannot be dodged forever.

The fork, which is the user's and not an agent's: **get credentials, or accept
that this programme publishes cost bounds and capability certificates and never
claims an accuracy win.** Do not quietly assume equal accuracy in a new row; that
assumption is what put four earlier rows out of quotation.

## 7. What to do next

Ordered, with the reason. This is a recommendation from the evidence, not a
queue of tickets — `CLAUDE.md` is explicit that the better experiment beats the
next item, and says so about itself.

1. **Make dependency-certification a substrate-wide contract.** Only
   `possible_answers_scoped` reports what it read. Generalise it so every kernel
   and flow node returns the facts it consumed, and "here is the answer, here is
   everything it rests on, and nothing else mattered" becomes a first-class
   artifact. *Why this first:* it is the only claim of ours that survived contact
   with a realistic opponent — the 46x over-fetch and the missing stopping rule
   are both this. `check_entitlement` in `symbolic_ai_kernels/abi.py` is the
   nearest existing shape to copy.
2. **Then find where the certificate is worth money.** A corpus with deep,
   private dependencies: the **3.8M-row 13F holdings graph**
   (`data/sources/sec-edgar/.../finance/13f/`) is the candidate. Portfolio
   questions depend on hundreds of facts, so a 46x over-fetch is not a rounding
   error and a wrong stopping point is a wrong answer. GLEIF ownership is close
   to exhausted for this line — chain p50 is 2.
3. **Keep attacking our own published numbers.** Two of the last three findings
   corrected an earlier headline of ours, at a cost of hours each. That is
   currently the highest-yield activity in the repo.

**What not to do:** more kernels (the data says stop at eight, `ROADMAP.md`);
more query classes on GLEIF ownership; any further cost row against a
hypothetical opponent; and any experiment whose write-up you could draft first
(`CLAUDE.md`, "Do not re-run to confirm").

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

## 9. Verify the checkout in two minutes

```bash
uv run pytest tests/test_ambiguity.py tests/test_fusion.py      # 74 pass, <1s
uv run python scripts/gleif_scoped_ambiguity.py                 # ~1 min, both mixtures
uv run python scripts/ambiguity_advantage.py                    # ~1 min, the cost table
uv run pytest tests/                                            # 3,354 pass, ~11 min
```

If `data/sources/gleif/...` is absent, every script above dies at load and
nothing else in the repo depends on those bytes.
