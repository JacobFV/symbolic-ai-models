# Handover — 2026-08-19 (fifth revision, after the reading arm)

For the next agent picking this repo up cold. `ROADMAP.md` says what the work
*is*; `CLAUDE.md` says how to work here; this says **where the live edge is, what
is already known so you do not re-derive it, and what is believed but unproven so
you do not inherit it as fact.**

Read in this order: `CLAUDE.md` (working agreements — they are binding and they
were each paid for), `APPROACH.md` (the argument), then this, then `ROADMAP.md`.
`notes/lessons/` is the shortest path to not repeating six specific mistakes.

---

## 0. The state after the reading arm. Read this first of all.

*Programme-level:
`notes/status/2026-08-19-the-in-scope-path-was-larger-than-the-blocked-one.md`.
§0-below is the previous revision — still true about the learned reader, and it
concludes the ceiling would not move without the excluded component, which turned
out **wrong**.*

### The one paragraph that matters

Every decomposition of the reader used **ceiling × classifier × ranker**. Adding
the **proposer** — how often the candidate the answer needs is generated at all —
gave a four-factor model whose product reproduces the measured rate within
**0.019 across ten rows**, and showed `industry`'s proposal was **0.006**: the
reader could not represent the answer, and every number for that relation
described a component nobody had looked at. **The components that were not in the
decomposition were the ones with headroom.**

### What exists now that did not

- **`PhraseMentions`** — proposes from a learned phrase inventory plus productive
  suffixes, and **normalises**: seeing *automotive company* it reports the
  canonical `automotive industry`. `CapitalisedMentions` can only propose proper
  nouns and silently makes lowercase-valued relations unanswerable.
- **`supervise_via`** (`scripts/supervise_through_proposer.py`) — labels a
  sentence when **the proposer can produce a gold value from it**. Alone the
  alias proposer made `industry` *worse*; with aligned supervision, **3.9x**.
  The two halves are useless apart.
- **`induce_aliases`** (`scripts/induced_aliases.py`) — aliases by label
  association, which recovers what morphology cannot: `country` 0.182 → **0.390**.
- **`Ledger.correct_tokens_per_usd`** — throughput charged for clearing the floor.
  A system at its floor earns **zero**, which is a unit test.
- **`scripts/corrected_triage.py`** — the model-free screen.

### Numbers not to re-derive

| | |
|---|---|
| `industry`, end to end | **0.000 → 0.025 → 0.097 → 0.238** (+0.177 above floor) |
| `country` | 0.182 → **0.390** (floor **0.298** — only +0.092 above it) |
| `headquarters` | **+0.235 above floor**, the strongest relation |
| oracle classifier is worth | **1.9x–6.6x** on every relation |
| composed query, union | **micro-F1 0.225** (macro 0.118) |
| 1 Bt/$, charged for correctness | bounded **5.7–17.7x over**; prose **0.35–0.90 Bt/$**, under |

### The triage rule, and its exact limit

`containment < floor` **proves a relation cannot clear its floor**, model-free. It
rejected 1 of 7 with no false alarms. But a prospective test on two unseen
relations scored **four of seven**: every *negative* prediction was right and two
of three *positive* ones were wrong about size. And `owned_by` passes every screen
and still fails, because its gold values appear for reasons other than the
relation — **false containment**, with no cheap detector. Frame concentration was
tried twice and failed twice.

> **A model-free screen can prove a relation impossible, never feasible.**

### Claims withdrawn this arm — do not re-inherit them

- *"The composition law holds to within 0.001"* — six events in 191 chains.
- *"The union's gain grew sevenfold with scale"* — an ordering artefact; shuffled
  it plateaus at 17–20%.
- *"The Heaps exponent replicates to three decimals"* — prefix sampling; the
  spread is ±0.03.
- *"Error topology has opposite signs for the two composed shapes"* — measured
  and **backwards in every clause**.
- **Every composed-query figure was macro-averaged and none said so** — micro is
  1.4x–2.3x higher and inverts the learned-vs-hand ranking.

### Traps this arm added to the six below

7. **A prefix is not a sample.** Corpus files carry their construction order.
   Shuffle with a fixed seed before any prefix.
8. **Hash randomisation varies a deterministic-looking pipeline.** A dict built
   from `set(a) | set(b)` iterates differently per process; sort with a total
   order and sweep two `PYTHONHASHSEED` values before quoting a delta.
9. **A rate without its numerator is not a result.** Below ~20 events report the
   interval, not the point.
10. **Quote the floor.** `country` looked second-best on raw accuracy and is
    weakest of five above floor, because *United States* is right 29.8% of the
    time.
11. **Say which averaging.** Macro and micro differed by 2x and disagreed on a
    ranking here.

---

## 0. The state after the learned-reader session. Read this first of all.

*Programme-level version:
`notes/status/2026-08-19-the-boundary-is-built-priced-and-bounded.md`. This is the
operational one. §0a below is the previous revision and is still true; it is no
longer the edge.*

**The language boundary is built, priced, and bounded.** The edge is no longer
"can this be read" — it is a fork about what to build next, stated at the end of
this section.

### What exists now that did not

`symbolic_ai_core/reader/learned.py` — **one reader, no domain lexicon in its
source**, fitted from aligned `(sentence, claim)` pairs. It induces the predicate
inventory, what counts as a name, every role signature, filler types, quantity
units, the temporal envelope, and which roles are filled from earlier text. Two
models: an averaged perceptron (default, reproduces every published number) and
`model="logistic"` (a probability rather than a margin). `CapitalisedMentions`
swaps identifier corpora for English prose. `calibrate()` fits a held-out
score→accuracy map. `Reader.run(query=...)` carries the document subject.

**Use the union fit.** Fitted on documents alone it reads all three generated
domains at 1.000 and collapses to **0.000** when entities are renamed — it
memorised ten names. Refit with a per-document renaming *added* to the original
documents and it holds both ends (0.955 / 1.000 / 0.992). Anything quoting the
1.000 without the augmentation is quoting a vocabulary measurement.

### Numbers already measured. Do not re-derive these.

| | |
|---|---|
| **north star, learned pipeline** | $1.59e-08 / $2.37e-08 / $9.65e-08 per solved episode above floor (solvency / scheduling / flood) |
| **against a $3/Mtok API at accuracy 1.000** | 112,395x / 101,809x / 25,597x more expensive per solved episode |
| **generated surfaces are saturated** | six training documents reach 1.000 F1 in all three domains |
| **incremental ingestion** | claim-identical world at 8.3x less reading; the whole cross-document state is the **mention history** |
| **real text, learned** | `parent` 0.182 correct against four hand patterns at 0.393 |
| **real text, union** | learned fills gaps: 20–41% of its correct answers are ones the patterns miss; `headquarters` 0.241 → 0.327 |
| **multi-hop (191 chains)** | learned 0.031 against `p₁²` = 0.032 — independent to 0.001; hand 0.058 against 0.030 — its errors clump |
| **persistence economics** | ingest 1,661 articles $1.16e-04 **once** vs iterative RAG $6.32e-03 **per query**; cheaper from query 1 |
| **retrieval** | hop-2 article found 0.073 at k=1, 0.492 at k=5; the second retrieval is keyed on hop 1's answer, so RAG inherits `p₁` |
| **Heaps exponents** | full token path 0.915, last content word **0.648** (0.641 at a tenth the data — replicates) |
| **crossover** | four hand patterns ≈ 10⁵–10⁶ articles of distant supervision |

### Lines that are CLOSED. Do not reopen them in this form.

- **`L_reader = Σ sᵢ Lᵢ`.** Failed as a training weight (nine cells, one
  improvement) and as a decision rule (nine cells, zero), with its key input
  verified three ways. A margin-scaled update **over-predicts the upweighted
  class**, so the objective protects a critical claim by inventing one.
  Reopening needs the cost of an error *set*, not of single claims.
- **Six real-text levers**: multi-instance pruning (worse), WordNet supersenses
  (nothing, and *the second time* supersenses came out at the wrong
  granularity — they give a category and these tasks need a frame), frames on the
  classifier (nothing), class balancing (inner CV chose no weighting at both
  corpus scales), answer aggregation (oracle only 0.012 above argmax), frames on
  the ranker (+33% ranker, +4% end to end).

What *did* move real text: ten times the corpus (+55%) and the query (+4%).

### The fork, and it is the user's call

Both arms point at the same missing component from opposite directions — the
threshold arm because a kernel-derived rule needs a graded posterior, the
real-text arm because six feature-level levers are closed. That component is a
**learned sentence encoder**, and `CLAUDE.md` scopes the neural half as *a
control, off by default, not to be invested in*. **The evidence and the scope
disagree.** Options: extend the scope to a small CPU encoder; accept 0.182 on
real text and spend effort where the numbers are strong (kernels, persistence
economics); or change the task so features suffice. Do not resolve this by
drifting into it.

### Blocked

- **No LLM accuracy has been measured anywhere.** Every comparison is a price
  sheet plus the symbolic side's own accuracy. No API key and spending money is
  out of scope. State it as a limit in anything published.
- **Wikidata/Wikipedia rate-limit hard.** The fix is batching, not backoff:
  `wbgetentities` takes 50 ids and `prop=extracts&exlimit=20` takes 20 titles.
  `scripts/fetch_wikipedia_parents_batched.py` does ~170 requests where the
  one-at-a-time version did ~4,900 and spent hours on 49 articles.

### Traps that cost this session hours

1. **`pkill -f <pattern>` matches your own shell**, whose command line contains
   the pattern. It killed two sessions. Bracket a character: `fetch_[w]ikipedia`.
2. **Calibrating on the training distribution returns a constant.** Holding out
   *documents* is not holding out the *shift*; the model is near-perfect on the
   phrasings it was fitted on, so isotonic regression correctly says score does
   not predict accuracy — and every downstream threshold goes inert for a reason
   that has nothing to do with thresholds. Calibrate on the deployment
   distribution (dev seeds 500,000+).
3. **Renaming a corpus by string substitution shifts every span offset after it**
   and reads as catastrophic reader failure. Rename the *case* and re-render.
4. **`functools.lru_cache(maxsize=1)` becomes a bug the moment the function takes
   a parameter.** Alternating verb/noun lookups re-parsed the WordNet archive per
   token: 72 s for 4,400 lookups against 0.19 s.
5. **Token-level membership tests break multi-word names.** `Ministry of
   Communications` is never one token, so role induction called every such filler
   *latent* and answered with a minted skolem: 0.000 exact against 0.149 lenient.
6. **An averaged perceptron's clock must count examples, not mistakes.** Counting
   mistakes stops the clock at convergence and the average is dominated by the
   first chaotic updates — 0.796 F1 against 1.000, fixed in one line.

---

## 0a. The state after 2026-08-19. Read this before anything else.

*For the programme-level version of this — what the whole bet has established,
what it costs, and how it sits against the GOFAI post-mortem, the neuro-symbolic
pitch and the scaling position — see
`notes/status/2026-08-19-where-the-programme-stands.md`. This section is the
operational one: what changed and what to do about it.*

A long session on **what a reader gets wrong, what can catch it, and what any of
it costs**. It supersedes §0 in several places and it changes what to do first.

### The benchmark was easier than it looked, in all three domains

**Every distractor was inert by construction.** Flood's disused track drew its
endpoints from regions appearing nowhere else; scheduling's withdrawn machine
carried no capability and its "anodising" sentence names a capability outside the
vocabulary; solvency's divested `sub_99` appears nowhere else at all. Measured:
flood's reader **admits** its distractor on 60/60 cases and the other two never
even type theirs (0/60 each).

Point them at entities that matter — `hard_distractors=True`, now in all three
generators, default `False` so published numbers keep their meaning:

| domain | published | **honest** | with today's components |
|---|---:|---:|---:|
| flood | 0.988 | **0.679** | 0.933 |
| scheduling | 1.000 | **0.790** | 1.000 |
| solvency | 1.000 | **0.450** *(floor 0.550)* | 1.000 |

Solvency on the honest surface is **worse than answering "no" every time**. Use
the honest setting for anything new.

### Two responses to a corrupt channel, and which one a domain permits

**Detection** reads the fact a second time — sound *and* complete, gated by the
role's **arity**. **Insensitivity** proves the answer does not depend on it —
sound but lossy, gated by the shape of the **decision**.

| channel | arity | detection | insensitivity | break-even `W` |
|---|---|---:|---:|---:|
| flood `link` | multi | 0.000 | 0 wrong @ 48.8% | 0.595 |
| flood roles | single | 0.774–0.976 | — | — |
| scheduling `has_capability` | multi | 0.000 | 0 wrong @ 52.5% | 2.948 |
| scheduling `needs_capability` | **single** | 1.000 | — | — |
| solvency `owns` | multi | 0.000 | 0 wrong @ 48.5% | free |
| solvency `revenue` | multi | 0.000 | **none possible** | — |

Three things to carry: **the detectable errors are the harmless ones**;
**undetectable is not uncertifiable**; and **only an aggregating decision denies
both** — which is why solvency's repair had to be in the reader.

### The reader's own design rules, both measured

- **Accumulate, do not branch.** A packed sentence (two claims, one sentence)
  collapses a branching reader to its floor — solvency 1.000 → 0.567, scheduling
  1.000 → 0.658. `read_signature_accumulating` in both recovers **1.000** and is
  identical on every honest surface. Theorem: a signature is a function of the
  sentence, so **no signature reader can be packing-robust**; the claims are still
  there, and accumulation recovers the content the signature cannot classify.
- **Cut at the clause, and no finer.** A sentence-level staleness gate takes a
  reader from 0.925 to 0.625 on packed prose. `filter_stale(…, unit="clause")`
  restores 1.000. Sweeping five granularities gives a **peak**: the finest split
  reproduces the sentence split's numbers to three decimals, because cutting
  through `a subsidiary **of** X` leaves no fragment matching the pattern.
  **Over-splitting is over-deleting.**

### Explanations are wrong more often than answers

- Flood's complete renderer cites a false fact on **7.6%** of answers it got
  **right**, and 15.5× worse per citation than the two-fact template — because its
  extra facts are the load-bearing set computed from the **read** world.
- Solvency is far worse: the stated consolidated total is wrong on **1.000** of
  cases while the verdict is wrong on 0.485. Sweeping the perturbation, **at a
  0.1% reading error the answer is perfect and the explanation is wrong 985 times
  in 1,000** — the two are functions of different variables and the ratio diverges.
- `ungrounded` flags **none** of it, in every cell. It certifies consistency with
  the world *as read*.
- **`render.uncorroborated` flags 88 of 88 false citations in 7.5% of them**, and
  **a certified answer cites no link at all** — 0.022 falsehood against 0.378. One
  check buys soundness *and* an honest account.
- The general rule: **an explanation's error rate is not bounded by the answer's**;
  inspectability is free only when the kernel uses claims **directly**.

### Real text exists now, and it is where the ideas get tested

`data/artifacts/wikipedia_parents.jsonl` — 168 companies, Wikidata `P749` against
the Wikipedia intro, with **former** parents labelled by `P582`. Rebuild it with
`scripts/fetch_wikipedia_parents.py`.

- The gold parent is named in the intro on only **0.696** of articles; four
  regexes get **0.369** at 0.626 precision.
- **`agreement` transfers nothing** — 0.603–0.626 precision, flat, at 0.21 less
  coverage. It tests *mutually exclusive alternatives*, and real prose supplies
  none: *Sony Music Entertainment* and *Sony Music Group* are one answer at two
  granularities.
- **`corroboration` transfers** — 0.718 against 0.346, graded (0.375 / 0.500 /
  0.857 / 0.784 by mention count), priced at **W = 0.242**, the lowest of the day.
  The first component here to improve a real-text number.
- The staleness gate's cue list was **85% false positives** on real English and
  needed three corrections, each found by **adding a genre**, not by thinking
  harder: the passive of *use* (53.5% of scientific fires), four temporal cues,
  and `struck` (29.9% of narrative fires, two in 36k scientific sentences).
- **Ambiguity mass on real prose is ≥ 0.44**, against the 0.000 that scheduling
  and solvency post — a signature never looks at the **verb**.

### What to do first

1. **Use `hard_distractors=True` and the accumulating readers.** Anything measured
   on the default surface with a branching reader is measuring the easy case.
2. **Real text is the front.** One arm exists; the corroboration result says the
   repo's ideas can pay there, and the agreement result says which ones will not.
3. **A reader on real text needs entity resolution**, which nothing here has —
   that is the concrete missing capability the emission failure names.
4. Blocked: SEC EDGAR needs a contact **email** in the `User-Agent`, and financial
   filings are the genre solvency imitates. One line from the user unblocks it.

### Numbers below that are now wrong

- The all-adversarial floor **0.618** was n=34; at 400 seeds it is **0.710**.
- *"The anchors never misfire"* is retracted — the control asserted the same
  predicate the mechanism computes. A misfiring vocabulary costs **−0.290**.
- `break_even_wrong_cost` reported **0.103** for the corroboration filter; the
  honest figure is **0.242** (the function assumed a baseline that answers
  everything). The three certificates are unchanged.
- Solvency's ownership paragraph was **decorative**: `read_signature` enrols a
  member the moment it files, and deleting the paragraph changes **0 of 200**
  answers.

## 0. Read this first — 2026-08-19, and it supersedes some of §1

A long run of work on the **text → world** front. The headline results are below;
the corrections are mixed in rather than segregated, because several of them are
corrections *to* the headline results.

### The benchmark does not justify its own kernels, except in one place

- **Flood's decision is in P.** A max-min Dijkstra — maximise the minimum bridge
  limit from depot to site over non-flooded regions — reproduces the full
  datalog + ASP + SMT answer on **200 of 200** cases
  (`symbolic_ai_generators/flood/widest.py`). Flood's `$/correct`, kernel
  ablations and price-of-soundness figures measure **the pipeline, not the
  task**. Use flood to study **reading**; do not use it to argue heterogeneous
  kernels are necessary.
- **Solvency's decision** is a sum against a threshold. Also polynomial.
- **Scheduling is the only genuinely hard domain**, and it is hard
  *asymmetrically*: a greedy packer exhibits an assignment for nearly every
  feasible instance, so what no polynomial method supplies is a **certificate
  that none exists**. The kernels earn their keep proving **negatives**.
- **But the expensive negatives are the easy negatives.** Every cell where
  clingo is slowest (198 ms at 20 jobs/−0.02, 1502 ms at 40/−0.05) is settled
  **6/6** by the O(n) capacity gate. The only regime where the solver is both
  necessary and expensive is **slack ≈ 0**, exact fit — which is also where the
  ground-truth oracle degenerates. `HARD_REGIME` (20 jobs, 3 machines, slack 0)
  is that intersection.

### Routing (directive 13) is answered, negatively

The escalation rule `p·L > c₁ − c₀` prices the cheap kernel as a **substitute**
for the expensive one. Measured, it is a **complement** — `c₁` depends on whether
`c₀` ran. Removing flood's datalog reachability made the flow **1.78× more
expensive and less accurate**, so its escalation threshold is *negative*: no loss
value makes skipping it pay. Per-case cost spread is p50 1.08×, max 2.14×, so no
hidden regime.

**Run every sound cheap check, always; never route around one.** A learned router
has nothing to choose between. Reopening conditions: an *unsound* cheap arm whose
error is predictable from pre-run world features, or a cost spread beyond 2.14×.

### Reading is the hard part, and the front is closed in a specific way

- Measured the same way, **flood puts reader loss at 0.500 and scheduling at
  0.000**. One domain where reading is the whole cost, one where solving is.
- **`read_signature`'s 1.000 was hard-coded paragraph indices** (`pi == 0..3`).
  Section headings are worth **nothing**; paragraph *order* was worth
  everything; paragraph **co-occurrence** replaces it at no cost.
- **Structure is load-bearing exactly where a sentence's signature does not fix
  its predicate** — confirmed by manipulation, not just correlation: renaming
  flood's regions so the prefix carries the role moves interleaved accuracy
  0.000 → 1.000 with everything else identical.
- The residual (depot vs flooded) is **closed to content-free reading**:
  rank-normalised observation → role is not even a function (21/21 role-slots
  ambiguous). **Content is required**, and that is measured rather than assumed.
- **A thesaurus is worse than no words.** WordNet expansion (17 → 1,324 tokens)
  recovers −0.029 and costs −0.265. Precision dominates coverage for a component
  feeding a symbolic pipeline.

### The soundness apparatus, and what each piece actually certifies

- **`ungrounded` certifies internal consistency with the world *as read*, not
  truth.** Demonstrated: a case whose true answer is empty renders as *"truck_0
  runs region_0 to region_3"* — a road in no claim — and returns `[]`. It cannot,
  by construction, catch reader errors.
- **`symbolic_ai_generators/flood/certificate.py`** proves the answer insensitive
  to a spurious link in one DFS rather than sixteen solves, and is **tight**
  (0 conservative, 0 incomplete over 196 cases). Prefer
  `certifies_role_independent`: the collapsed form **reads the roles**, so it
  inherits their errors and needs the role flag as a precondition.
- On the honest surface (interleaved, `hard_distractors=True`): answering
  everything gives **0.679**; the role-independent certificate gives **0 wrong at
  48.8% coverage**. That 48.8% is what the task allows, not what the check
  misses.

### Method lessons that cost real time

- **State the bound, not the number.** Zero failures in 34 cases excludes only
  8.8%; in 400, 0.75%. Both print as `1.000`. Re-running the claimed-exact
  findings at 400 seeds broke one of three.
- **A check that reads part of the world inherits that part's errors.** Produced
  three times independently — `ungrounded`, the certificate, and the role flag.
- **The margin that makes a component look sound is the same margin that hides
  its unsoundness.** `capacity_gate` compared summed floats and refused
  schedules that provably exist, on 4 of 30 instances at exact fit.
- **The risk is summation, not floating point.** Sum-vs-threshold needs exact
  arithmetic (solvency flipped 39/200 at constructed exact fit); one quantity vs
  one posted limit does not (flood, 0/3000).

### Numbers in older notes that are now wrong

- `capacity_gate` removing **87.7% of solver time "at zero accuracy cost"** — the
  saving is real and was measured where margins are comfortable; the gate was
  **unsound at exact fit** until fixed. Re-read, do not re-quote.
- The **solvency reader** used *largest filing* where the rule is *latest*: wrong
  on **9/400** cases, reported as 1.000 on 60 seeds. Fixed; now 0/400.
- **flood `signature+content` is 0.988, not 1.000**, interleaved at V=4.
- **The insensitivity certificate alone is 0.9786, not 1.000**, on the
  hard-distractor surface.

## 1. Where the live edge is

The programme pivoted on 2026-08-18 from *model zoo + language curriculum* to a
**typed world-program runtime over real federated data**. The curriculum is a
development harness, not the benchmark.

**The cost question is answered and the arc is closed.** The advantage over a
language model is **`1/f`**, where `f` is the fraction of queries the symbolic
system cannot settle — and **neither side has a lever** (§3i). `f` is a property
of **where the structure came from and how many identity boundaries the query
crosses** (§3j):

| regime | `f` | advantage |
|---|---:|---:|
| filed, single-source | 0.216% | **463×** |
| filed, **cross-source** | 14.7% | **7×** |
| derived from text | 56.0% | **1.8×** |

**68× of that is the first identity boundary** — inside the filed regime, which
is exactly where a federated substrate has to operate. Quoting any of these
without naming the regime is the error, and this file did it for months.

**And "cross-source" is not one number either.** The same regime spans **1.3× to
6.8×** on the choice of join and denominator alone — the ISIN bridge gives `f` =
77.7% per distinct security, 41.2% per position, 20.9% per aggregate dollar and
**42.0% for the median filer**. *A regime label is not an advantage; a question
is* (§3j).

**The capability question is where the live work is.** The first federated query
runs — three filed sources, two identifier joins, ~260 µs per portfolio — and its
answer is necessarily an **interval** (§3k). The arc there ends somewhere useful:

> **An uncertain input must not collapse a certain output.** Resolving positions
> by escalation makes a narrow band whose truth decays as `a^k`; widening for the
> errors instead keeps **96.9%** coverage at half the width, for $0.045.

**The one thing a human must do** is in §6: every accuracy comparison against a
language model is still unrun for want of credentials, and that blocker has now
bitten a **product** claim rather than only a cost row — `a`, the lookup accuracy
the band's reliability depends on, is unmeasured.

**And the programme-level result, which is what a reviewer should take away.**
Three arms this session ended the same way — **the symbolic machinery was correct
and the data did not reach**:

| arm | the machinery | the reach |
|---|---|---|
| extraction | works | **62%** of a 0.99 ceiling |
| the identifier bridge | exact, **0** ambiguity | **22.3%** per security |
| the ownership closure | **95.7%** agreement with filed truth | **5.3%** of held issuers |

**The bottleneck is not reasoning and has not been at any point this session.**
And reach splits in two: **purchasable** (a crosswalk, a corpus, a token — the
extraction and bridge gaps are partly this) and **structural** (what the world
files at all — the repo holds **98.3%** of GLEIF and only **4.1%** of its
entities report a parent). Half the reach on offer cannot be bought.

**But two of the three were the question, not the reach.** The same ownership
closure that changes 0.8% of *portfolio* answers changes **35.9%** on the
population that actually has parents — rising to **86.4%** at chain depth 6,
because a chain crosses a border through an intermediate holding company.
Portfolios hold the *top* of chains, so there is nothing to traverse. So the
instruction is one turn sharper than "invest in reach":

> **Match the question to the data's shape.** The machinery was right in all
> three arms. Twice the question did not exercise it; once the data did not
> reach. Different failures, different fixes.

**Read next:** §3i–§3k for the above, §5 for what this session retracted
(fourteen rows, most of them mine), §7 for what to do.

## 2. What is built

| thing | where | what it does |
|---|---|---|
| `fuse`, `prefer_measured`, `ClaimGroup` | `symbolic_ai_core/runtime/fusion.py` | groups competing claims, ranks by derivation, **refuses a tie**, retains the mixture |
| `possible_answers` | `symbolic_ai_core/runtime/ambiguity.py` | answers under every consistent world; refuses an explosion rather than truncating |
| `possible_answers_scoped` | same | **answers under only the conflicts the query reads.** The read set is discovered by handing the computation a recording assignment — no annotation, no static analysis |
| `additive_bounds`, `Bounds` | same | exact, attained extremes for a sum of independent per-subject terms, in linear time |
| `exposure`, `rank_by_exposure` | same | what a conflict costs *before* enumerating it |
| `AmbiguityExplosion.read` | same | a refusal that **names the conflicts the query depends on** |
| `Witness`, `KernelResult.witness/.maintainable` | `symbolic_ai_kernels/abi.py` | the facts that make an **existential** answer true, and `maintainable` is true exactly when one is present — deliberately **not** for a proof of impossibility. Carried by `asp@1` (answer set), `smt@1` (model), `lean@1` (refutations), `datalog@1` (derivation, **opt-in** via `witness_for` because recording provenance changes `evaluate`'s cost profile). `egraph@1` could and does not; `rigid@1`/`geo@1`/`economy@1` have none to have, because their answers are computed values rather than searches. `tests/test_witness.py::TestWitnessCoverage` holds that classification and fails if a new kernel skips it |
| `certify`, `revalidate`, `RecordingStore` | `symbolic_ai_core/runtime/certificate.py` | the same recording trick over **facts** rather than conflicts: run a computation once against a mapping that remembers, and its dependency set is the answer. Works on an arbitrary computation, including one that shells out to clingo |
| the tasks | `symbolic_ai_tasks/` | `ultimate_parent`, `company_key`, `cross_source_alignment`, `airport_country`, `range_limited_routing` |
| the experiments | `scripts/gleif_scoped_ambiguity.py`, `gleif_ambiguity_ladder.py`, `alignment_bounds.py`, `ambiguity_advantage.py`, `retrieval_rounds.py`, `gleif_fund_exposure.py` | every number in §3 |

Tests: `tests/test_ambiguity.py` (38), `tests/test_fusion.py`,
`tests/test_certificate.py` (17), `tests/test_witness.py` (21). Full suite
**3,403 passed, 10 skipped**. One test in that run was a ~25% flake that raced
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

**Inspectability is asymmetric — and this was measured BEFORE the certificate
arm, and was missing from this section until 2026-08-18.** Its omission caused
three findings in one session to claim an axis as new that the repo had already
established twice, and caused a decision note to re-derive analytically a number
that was on disk. See
`notes/lessons/2026-08-18-i-claimed-an-axis-was-new-and-the-repo-had-measured-it-twice.md`.

`notes/findings/2026-08-18-inspectability-is-asymmetric-the-witness-is-247x-cheaper-and-optimality-costs-double.md`,
on the route network, 400 solvable pairs, mean 5.19 hops:

| | per query | vs solving |
|---|---:|---:|
| solve (BFS with parents) | 274.8 µs | — |
| **verify witness** | **1.1 µs** | **247x cheaper** |
| **verify optimality certificate** | **542.4 µs** | **2.0x MORE expensive** |

An existential answer is its own witness; the universal half has none, and its
standard certificate — a distance labelling — quantifies over every edge and
cannot stop early where the solver can. Companion result in
`notes/findings/2026-08-18-a-datalog-witness-verifies-flat-while-solving-grows-and-most-of-the-ratio-was-my-engine.md`,
and `symbolic_ai_kernels/datalog/proof.py` carries the **stated open question**
that §3b's witness finding later answered: *whether that shape is a property of
shortest path or of the existential/universal distinction itself.* It is the
latter — §3b, §3h.

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

## 3i. The advantage at fixed quality: 8.1×, not 10⁶

`notes/findings/2026-08-18-the-million-fold-advantage-is-8x-the-moment-you-escalate-anything.md`

**Read this before quoting any number in §3, §3b, §3c or §3g.** They all compare
a cheap-and-wrong system against an expensive-and-assumed-perfect one. The
comparison anyone would actually make is a hybrid, and its price is set by the
escalated fraction `f`:

| policy | **f** | quality | **advantage** |
|---|---:|---:|---:|
| symbolic only | 0.0% | 0.526 | 2,061,364× |
| **escalate SILENT only** | **12.3%** | **0.650** | **8.1×** |
| escalate AMBIGUOUS only | 38.3% | 0.712 | 2.6× |
| escalate silent + ambiguous | 50.6% | 0.835 | **2.0×** |
| model only | 100% | 1.000 | 1.0× |

**And the extractor cannot tell what it knows.** Its `certain` tier — every
matched component naming exactly one institution — scores **F1 0.666**, against a
pre-registered *"below 0.7 changes my mind"*. Confident and wrong a third of the
time; `certain` beats `ambiguous` by only +0.150.

**The one thing that works inverts the intuition:** silence is a better
escalation signal than ambiguity. Escalating the silent tier buys **1.00 quality
per unit escalated** (those cases score 0.000, so nothing is re-bought);
escalating the ambiguous tier buys **0.48**, wasting half the spend on cases
already 0.516 right. **Escalate where the system produces nothing, not where it
is unsure.**

## 3j. The advantage is a property of provenance

`notes/findings/2026-08-18-the-advantage-is-a-property-of-provenance-463x-filed-against-18x-derived.md`

§3i's negative named its own escape hatch in one clause — *a task where `f` is
naturally small, regulatory data, where structure is already filed* — and this
tests it from numbers that were on disk before the session began. `f` is the
fraction of queries the system cannot settle: in a derived domain that is
everything the extractor got wrong (**56%** at 0.85 quality); in a filed domain
there is no extraction step to fail, so it is only what the data itself leaves
undetermined (**0.216%** / **4.274%**, `HANDOVER` §3).

**259×** between regimes on the strict comparison, **13×** on the conservative
one, from the same formula and the same code.

**The ladder, and the cliff is not where the section title suggests:**

| regime | **f** | quality | **advantage** |
|---|---:|---:|---:|
| **FILED** — GLEIF `ultimate_parent`, **single-source** | **0.216%** | 1.00 | **463×** |
| FILED — incl. closure-vs-filed conflicts | 4.274% | 1.00 | 23× |
| **FILED** — SEC → GLEIF, **CROSS-SOURCE** | **14.7%** | 1.00 | **7×** |
| **DERIVED** — OpenAlex affiliation → ROR | **56.0%** | 0.85 | **1.8×** |

**68× from single-source to cross-source; only 4× from cross-source to derived.**
So the cliff is **not** at the filed/derived edge — it is at the **first identity
boundary, inside the filed regime**. And crossing boundaries is what a federated
substrate is *for*: a system that answers only within one source does not need
federation, and the moment it does, the advantage falls 463× → 7×.

**And the cliff is irreducible by modelling.** 51.3% of ambiguous matches span
more than one country, so country should halve `f` — but **SEC carries no
country**, `same_as` is a name-derived key rather than a bridge, no file on disk
links a CIK to an LEI, and GLEIF's own external identifier is the *Delaware
register number* (NVIDIA: 2862596) rather than the CIK (1045810). Two filed
sources fail to join **not for lack of identifiers but for a surplus of
incompatible ones**, and the only attribute both hold is the name. Closing the
68× cliff looked like a **data-acquisition** problem — one crosswalk file — and
**that has now been tried and is mostly wrong.** GLEIF's free ISIN→LEI mapping is
on disk (`data/sources/gleif-isin/`), gives an exact-identifier join to 13F's
CUSIP-keyed holdings with **0.0000% ambiguity**, and covers only **22.3%** of
held securities. A coverage gap escalates exactly as an ambiguity does, so the
identifier join *alone* is **worse** than the names it replaced (f 77.7%, 1.3×);
the cliff is not the absence of an identifier but the absence of one that
**covers the workload** — and coverage has **two denominators**: 22.3% per
distinct security, **58.8% per position held**, because portfolios concentrate on
the large caps that carry LEIs. *(A "bridge-then-name" row first published here
was invalid: it multiplied one join's coverage by a different join's ambiguity.
See §3k.)*

> **RETRACTION, measured 2026-08-18.** *"No file on disk links a CIK to an
> LEI"* is **false**, and I asserted it after searching for the *mechanism* (a
> `same_as` column) rather than for the *name*. A file called
> `data/sources/wikidata/.../idbridges_full_p0.parquet` was invisible to that
> search: 69,679 `same-as` edges out of the wikidata namespace, targeting
> **lei 53,198 / isin 9,936 / sec 3,660 / asx 2,846 / ticker 39**. Any wikidata
> entity carrying both a `sec` and a `lei` edge is a CIK→LEI bridge joined on
> identifiers at both ends, and there are **2,113** of them.
> `scripts/wikidata_bridge_cik_lei.py`:
>
> | | | |
> |---|---:|---|
> | coverage, all SEC filers | 15.3% | 1,226/8,021 |
> | coverage, **matched** filers | **24.9%** | 1,015/4,078 — the denominator that composes |
> | ambiguity among **bridged** | **19.5%** | vs 13.1% unbridged, 14.7% base |
> | enrichment | **1.33×** | z = 5.03, p = 4.8e-07 |
> | composite `f`, independence | 11.01% | 9.1× — what the arithmetic above would predict |
> | composite `f`, **measured joint** | **9.81%** | **10.2×**, a **1.49× gain** over names alone |
>
> **Crosswalk coverage is not independent of join difficulty — it is enriched
> toward exactly the entities names cannot settle**, so `(1 − coverage) × f_name`
> *underprices* a crosswalk, here by 10.9% of itself. And the bridge and the name
> join agree **93.0%** of the time on which LEI a filer is (**90.4%** on the
> ambiguous subset, where the bridge actively picks) — the first time two
> independent joins in this repo have been checked against each other.
>
> **What survives unchanged:** 1.49× of a 68× cliff is not closing it. The
> paragraph's conclusion — that the cliff is about coverage of the workload, not
> the absence of an identifier — stands. Only the flat negative was wrong.


Two caveats belong next to it. Quality 1.0 in the filed regime is relative to
**the filing** — a better anchor than an automated extractor, still not truth.
And `f` counts undetermined answers as escalations when this repo's ambiguity
machinery returns the *alternatives enumerated*; a caller that can act on a
retained mixture escalates none of them and `f` is lower still.

## 3k. The first federated query, and it answers in an interval

`notes/findings/2026-08-18-three-sources-two-joins-and-an-answer-that-has-to-be-an-interval.md`

Three filed sources, two **identifier** joins, no names: 13F holdings (CUSIP) →
GLEIF ISIN-LEI → GLEIF entities (country). **World built in 5.8 s; 347 µs per
portfolio answered.** The answer is necessarily an interval — `additive_bounds`
gives exact attained extremes and the lower bound carries a **witness** a reader
checks by following two joins per position.

| US exposure, interval width | p10 **18.0%** | p50 **38.9%** | p90 71.0% |
|---|---|---|---|

**Value-weighted** (13F reports USD — established by summing AAPL to $3.06e12):
width p10 **8.7%**, p50 42.1%, p90 **88.2%**, and **25.2%** of filers get a band
≤ 20 points, up from 13.4% unweighted. It helps the filers already close and
**hurts the ones that were not**.

**Coverage has four readings spanning 3.5×** — 22.3% per distinct security, 58.6%
per position, **79.1% per dollar aggregate, 58.0% per dollar for the median
filer**. The aggregate describes Vanguard, not a typical filer; quoting it would
be the slice-versus-population error in its third form.

Honest uncertainty rather than a point estimate that would have been a lie — and
**it becomes a product when the width is attributed.** `Bounds.width_by_subject`
was already there and the slice ignored it; settling unbridged positions
widest-first, the 5 widest carry **57.5%** of the width and:

| lookups | median band | filers inside 20 points | $/portfolio |
|---:|---:|---:|---:|
| 0 | 43.5% | 23.7% | 0.000 |
| **10** | **6.9%** | **77.5%** | **$0.045** |
| 20 | 2.0% | 92.8% | $0.091 |

**Ten escalations move one-in-four to three-in-four for four and a half cents** —
on **usability**. **They do not preserve truth.** Tested on the bridged subset,
the narrowed band still contains the truth only:

| lookup accuracy | k=0 | **k=10** | k=20 |
|---:|---:|---:|---:|
| 1.00 | 100% | 100% | 100% |
| **0.95** | 100% | **63.3%** | 42.3% |
| 0.90 | 100% | 40.7% | 17.1% |

**Coverage ≈ `a^k`**: any single wrong lookup breaks the band, because the policy
resolves *widest-first* and one error displaces it by that position's full
weight. The concentration that makes the product cheap makes it fragile.

> **You can have a bound that is always true and rarely usable, or one that is
> usually usable and often false.** A narrowed band must be quoted with `a^k`,
> and `a` for a real model on this task is unmeasured — §6.

**And the fix is the repo's own ethos: widen for the error rather than collapse.**
If at most `m` of `k` lookups are wrong, widen both ends by the `m` largest
resolved weights. At `a = 0.95`, `k = 10`:

| m | coverage | median band |
|---:|---:|---:|
| 0 *(naive)* | 63.3% | 10.4% |
| **1** | **96.9%** | **23.7%** |
| 2 | 100.0% | 28.7% |

So at the same **$0.045**: doing nothing is a 43.5% band always true; naive
resolution is 10.4% and true 63% of the time; **widening for one error halves the
band to 23.7% and stays true 96.9% of the time.** `additive_bounds` needed no
change — only the right input. **Do not let an uncertain input collapse a certain
output.**

The advantage is a property of the domain's **structure-provenance**, not of the
technology — and this reconciles the two
halves of the session that looked contradictory. The repo's earlier advantages
were measured on GLEIF and SEC, both **filed**, and they were real. The
extraction arm's 1.8× is also real. One formula, two regimes; **quoting either
without naming the regime is the error.** `symbolic_ai_core/cost.py` said this in
its own docstring before the session started — *"cheap-and-incapable is not a
point on the cost curve; it is a point off the capability axis entirely"* — and
every cost row here ignored it until now.

The previous frontier, which is measured and closed rather than abandoned:

> *Maintaining an answer instead of re-deriving it: what an answer actually
> depends on, how much smaller that is than what the computation read, and what
> the difference is worth per corpus update.*

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

## 3l. Reach has three tiers, and the residual lives in the one nobody recorded

Two findings, `notes/findings/2026-08-18-purchasable-reach-saturates-...md` and
`notes/findings/2026-08-18-reach-has-three-tiers-...md`. The *purchasable /
structural* split this repo has carried is wrong; it is three.

**1. Purchasable — and it SATURATES.** Over 26,850 securities and **$51.4T** of
13F positions:

| crosswalk | rows | by count | **by dollar** | attained vs oracle at its own k |
|---|---:|---:|---:|---:|
| filed, GLEIF ISIN→LEI | 2,281,221 | 27.9% | **75.0%** | 66.0% |
| curated, wikidata→ISIN | 2,383 | 7.5% | **68.8%** | 69.8% |

A crosswalk **957× smaller** answers 92% as much of what the workload weighs —
**878× more answered value per row**. Normalised against an oracle picking the
best k securities at each crosswalk's *own* k (random-at-k as the floor), the two
are **1.06×** apart, so neither is better targeted and the effect is pure value
concentration. **The raw dollar/count ratio (9.21× vs 2.68×) is an artefact** —
its ceiling is `1/coverage`, so a smaller crosswalk scores higher mechanically.
Do not quote it.

**2. Derivable from recorded structure — works, and is narrow.** Transitive
closure over GLEIF's relationship graph, on the 598 ambiguous filers:

| | | |
|---|---:|---|
| determined at group level, unconditional | **18.2%** | 109/598 |
| candidates all present in the graph | 22.4% | 134/598 |
| determined, **conditional on that** | **81.3%** | 109/134 |
| permutation control, both populations | **0.0%** | 0/598 and 0/134 |

**3. Absent.** GLEIF mentions **348,836 of 3,348,427** entities (**10.4%**) in
any relationship, because Level 2 is only reportable when a consolidating parent
exists *and* is itself LEI-registered. For the other 90% the relationship was
never recorded by anyone — not a procurement problem, and closure cannot reach it.

**And the two levers are near-orthogonal.** `f` for a group-level question:

| policy | `f` | advantage | |
|---|---:|---:|---|
| names alone | 14.66% | 6.8× | |
| + wikidata bridge | 9.81% | 10.2× | 1.49× — acquired |
| + closure, zero acquisition | 11.99% | 8.3× | 1.22× — derived |
| **+ both** | **8.17%** | **12.2×** | **1.80×** (1.49 × 1.22 = 1.82) |

> **The residual `f` of 8.17% lives almost entirely in tier 3.** The frontier of
> the federated advantage is not a reasoning limit and not a budget limit — it is
> the limit of what the world has written down.

**Scope, and it is half the result.** Closure settles **group-level** questions
only; *"which country is this filer's legal entity in"* stays ambiguous when the
group spans countries. Matching the question to the data's shape is worth
**1.22×**, free — the first time this repo has priced that thesis rather than
asserting it.

## 3m. Structural federation is gated by identity federation, and that saturates

`notes/findings/2026-08-18-structural-federation-is-gated-by-identity-federation-and-that-saturates.md`.
§3l placed the residual `f` in tier 3 and called it "not a procurement problem".
The obvious consequence — a second source's structure reaches what GLEIF never
recorded — was tested and is a **null**.

| arm | ownership edges | ambiguous filers determined | control |
|---|---:|---:|---:|
| GLEIF only | 296,491 | 109/598 = 18.2% | 0.0% |
| wikidata only | **1,279,720** | 6/598 = 1.0% | 0.0% |
| UNION | 1,573,678 | 112/598 = 18.7% | 0.2% |

**3 filers settled that GLEIF could not**, against a control settling ~1 —
noise-adjacent, and a slice. The second source buys **1.01×**. Why:

| | |
|---|---:|
| wikidata edges with **both** ends expressible about an LEI | **3,996** of 1,279,720 |
| GLEIF entities carrying a wikidata twin | **52,860 / 3,348,427 = 1.58%** |
| ambiguous filers whose candidates all carry a QID | 11/598 = 1.8% |

> **A second source holds 4.3× more ownership structure than the first and 0.3%
> of it can be said about the entities in question.** The structure is abundant
> and *unaddressable*. **Relief in tiers 2 and 3 is gated by tier-1 identity
> coverage, and tier 1 saturates** — so the residual 8.17% does not yield to more
> sources, only to more identity.

**Screening number before federating another source's structure:** what fraction
of the target population carries that source's identity. Here 1.58%, and it
predicts the 1.01× without building anything.

**Do not quote** the 54.5% conditional determinacy from that run: n = 11.

## 3n. Coverage is asymmetric in the DIRECTION of the query

`notes/findings/2026-08-18-identity-coverage-is-asymmetric-in-the-direction-of-the-query.md`.
§3m's null rests on **1.58%** of GLEIF entities carrying a wikidata twin — an
unweighted per-entity count, and this repo has been caught by that denominator
three times. Checked, over $51.4T of 13F positions:

| population | by count | **by value** | ratio | vs flat 1.58% |
|---|---:|---:|---:|---:|
| **held securities** (issuers), by $ held | 12.0% | **66.3%** | 5.5× | **42×** |
| **13F filers**, by AUM | 1.6% | **23.2%** | 14.3× | 15× |
| all GLEIF entities, unweighted | 1.6% | 1.6% | 1.0× | — |

> **Coverage is asymmetric in the *direction* of the query over the same edge.**
> The 13F holdings relation traversed toward the security is 66.3% addressable
> by value; traversed toward the holder, 23.2%. **2.9× apart**, same bridge,
> same technology.

Two consequences, and they point opposite ways:

- **The residual `f` of 8.17% is NOT a tail phenomenon.** The alignment workload
  where `f` lives is over *filers*. Correcting the denominator was necessary and
  §3m's null survives it — that arm ran on the population wikidata covers worst.
- **The vertical slice (§3k) rests on much firmer ground than the alignment
  does**, because it operates on the *issuer* side at 66.3% of held value.
  Nothing had established that.

**Prominence tracks entity TYPE, not size.** I predicted 12–25% of filers by
count and 55–80% by AUM; it is 1.6% and 23.2%. wikidata is an encyclopaedia of
operating companies, and most of the 8,755 13F filers are small registered
advisers with no encyclopaedic existence at any AUM.

**Strongest available refuter, and it is cheap:** Form ADV covers exactly the
registered advisers wikidata misses, is public, and is not on disk.

## 3o. Saturation is a property of the workload, not a law — and one statistic decides it

`notes/findings/2026-08-18-saturation-is-not-a-law-...md`. §3l's headline
("purchasable reach saturates") named its own refuter; it was run and it fires.
Share of mass in the **top 7.5% of entities** — the count-coverage of the curated
crosswalk, so it answers "could a small acquisition have covered this?":

| workload | entities | **top 7.5%** | gini |
|---|---:|---:|---:|
| 13F holdings, by **$ held** | 33,656 | **96.9%** | 0.976 |
| patent assignees | 572,495 | 85.6% | 0.892 |
| 13F holdings, by **position count** | 33,656 | 77.7% | 0.894 |
| caselaw citations | 4,513,529 | 56.1% | 0.716 |
| patent citations | 8,407,184 | 55.6% | 0.723 |
| **github events, per repo** | 3,902,511 | **27.3%** | **0.373** |

**3.5× span.** The GitHub outlier was verified directly because it carries the
conclusion: 7,730,712 events over 3,902,511 repos, mean 1.98, median 1, 57.3%
with exactly one event, max 1,043. There is no head to concentrate in.

> **THE DECISION RULE:** before acquiring a crosswalk, measure the workload's
> top-7.5% mass share. At **96.9%** buy the small file and stop — 957× more rows
> bought 6.2 more points. At **27.3%** a small acquisition buys almost nothing
> and breadth is the only lever.

**What survives:** the *mechanism* — both crosswalks attain ~2/3 of the value
achievable at their own k, so the raw dollar/count ratio is still an artefact.
**What does not:** the generality of the economic advice.

**And the denominator trap fires inside one edge set**: the same 13F holdings are
96.9% concentrated by dollar and 77.7% by position count. Fourth time in this
repo. *"The workload" is not defined until the mass is.*

## 3p. Determinacy is not accuracy — and §3j–§3o priced determinacy

`notes/findings/2026-08-18-determinacy-is-not-accuracy-...md`. **Read this before
quoting anything from §3j–§3o.**

Every advantage in those sections came from a hand-rolled
`advantage(f) = M/(f·M + (1−f)·O)` where `f` is *the fraction the system cannot
settle*. That formula has **no slot for accuracy**, so accuracy was never
measured and "settled" was read as "correct". §7 item 10 had recommended running
this session's work through `symbolic_ai_core/cost.py` the whole time.

Ground truth: the wikidata bridge, **1,015** filers, **excluded** from the system
being scored. Floor: **pick at random among the name candidates** — strong by
construction, because an unambiguous filer has one candidate and the floor takes
it free.

| | settles | correct (fallback) | floor | **above floor** |
|---|---:|---:|---:|---:|
| entity level | 80.5% | 83.7% | 82.9% | **+0.9%** |
| group level | 84.6% | 87.3% | 87.4% | **−0.1%** |

**CEILING, which no arm had computed: the true LEI is among the name candidates
for only 93.0% of filers.** No policy over them scores above that.

| system | rate | floor | $/solved | **$/solved above floor** |
|---|---:|---:|---:|---:|
| hybrid, escalating 15.4% | 0.965 | 0.874 | $9.80e-05 | **$1.04e-03** |
| frontier model only | 1.000 | 0.874 | $6.15e-04 | $4.88e-03 |
| **federated symbolic resolver** | 0.873 | 0.874 | $1.78e-11 | **inf** |

**Why, and it is not a bug:** at group level closure determines the answer
*because all candidates share a root* — and if they share a root, a random pick
lands on it too. The floor gets exactly the cases closure settles, for free.

> **The 1.22× (closure), 1.49× (crosswalk) and 1.80× (combined) are cost ratios
> over an escalation policy, not capability gains.** What the symbolic layer buys
> is **knowing when it is right** — certification, not capability. Priced
> properly that is **4.7×** on $/capability-above-floor (hybrid $1.04e-03 against
> the model's $4.88e-03), not 6.8×–12.2×.

**Harness trap, walked into with the sign posted:** the first version scored
abstention as zero and reported the layer at **−7.5% below floor** — comparing a
system that refuses to guess against a floor that always guesses. Score both; the
gap between them *is* the effect.

**But that is not the whole question, and the rest is good news.** Determinacy is
**highly informative** about correctness — entity level settled **93.6%** (at the
93.0% ceiling) against unsettled 32.3%; group level **95.8%** against 40.4%.
Priced at a fixed 15.4% escalation budget:

| policy | accuracy | gain |
|---|---:|---:|
| escalate the **unsettled** cases | **96.5%** | **+9.2%** |
| escalate a random 15.4% | 89.2% | +2.0% |

> **Knowing which answers are unsafe is worth 4.69× more quality per escalation
> dollar than spending it blindly.** That is the layer's real contribution, and
> it is the first capability number this session produced with a floor behind it.

**This contradicts §3i**, where the confident tier beat the ambiguous one by only
+0.150 F1 on OpenAlex. Both tierings are structural, so the difference is
**candidate recall** — 93.0% here against a lossy gazetteer there.
**Determinacy is informative exactly when the candidate generator has high
recall**; a certificate can only certify what the generator retrieved. Report
candidate recall beside any determinacy claim.

**It exposed a gap in the north star, and the gap is now CLOSED.**
`$/solved-above-floor` priced getting the answer right and priced
knowing-you-are-right at **zero**. `symbolic_ai_core/cost.py` now carries a
`Targeting` denominator, floored by **blind escalation of the same share** —
mirroring `Capability`'s refusal to carry a rate without a floor, because *"we
escalated and quality rose" is not a result; buying answers raises quality
whoever picks them.* Two columns, rendered only when a row makes the claim:

```
system                       $/solved>floor   rate   floor    aim x      $/pt
federated symbolic resolver             inf  0.873   0.874     4.69  $1.31e-03
```

**Worthless at producing answers above its floor; worth 4.69× at certifying
them.** Applied to the two domains already measured — OpenAlex values
hand-computed and recorded *before* the implementation existed:

| signal | escalated | **aim ×** | verdict |
|---|---:|---:|---|
| GLEIF resolver determinacy | 15.4% | **4.69×** | worth routing on |
| OpenAlex **silence** | 12.3% | **2.13×** | worth routing on |
| OpenAlex **ambiguity** | 38.3% | **1.02×** | worth **nothing** |

> §3i called the ambiguity signal *weak* (+0.150 F1). Priced, **it is worth
> nothing over spending the same budget at random** — a sharper claim than that
> finding made, obtained by pricing a description already on disk.

See `notes/findings/2026-08-18-pricing-certification-...md`.
`tests/test_cost_targeting.py`, 12 tests; the 41 existing cost tests are
unchanged.

## 3q. What a certificate wastes is a property of the ANSWER, and reads cannot see it

`notes/findings/2026-08-18-over-approximation-is-a-property-of-the-answer-...md`.
§3b measured soundness on every row and never measured **precision** — how many
invalidations were unnecessary. Under the new `Targeting` denominator that is the
whole value: for a sound certificate `aim× = 1/f_flagged`, against a minimal
certificate's `1/f_stale`.

| query class | compute | f_flagged | f_stale | **over-approx** | aim× |
|---|---:|---:|---:|---:|---:|
| `is_widely_held(k=100)` | 739 ns | 62.1% | **0.78%** | **79.8×** | 1.61× |
| `holder_count` | 748 ns | 62.1% | 54.3% | **1.1×** | 1.61× |
| `portfolio_overlap` | 6,048 ns | 99.0% | 62.1% | 1.6× | 1.01× |
| `min_filers_covering(12)` | 6,745,104 ns | 100.0% | 40.7% | 2.5× | 1.00× |

**The first two rows read the identical keys over the identical securities and
cost 9 ns apart. They differ 73×.** The only variable is the answer function:
`len(holders)` against `len(holders) >= 100`.

> **Over-approximation is a property of the answer's SENSITIVITY — not of the
> computation's cost, not of the read set's size — and it is invisible to any
> mechanism that records reads**, because the two cases that differ 73× record
> byte-identical read sets.

That answers §3b's stated open question (*"nothing in the mechanism tells you
which case you are in"*) with a mechanism, and it explains the 6,591× over-read:
that is what happens when a coarse answer is certified by the fine inputs a
search touched.

**My pre-registered claim was that over-approximation would be worst where
compute is dearest. Refuted** — worst at the cheapest class, **2.5×** at 9,000×
the compute. An NP-hard set cover's answer moved **40.7%** of the time.

**And the stability margin is loose too.** §3b called it *"the rung the recording
mechanism cannot produce"* at 93.62% survival; since it is sound, its 6.38%
flagged rate is an **upper bound** on `f_stale`, measured at **0.78%**. The best
rung in the arm **over-approximates by 8.2×**.

**In the ledger** (`rate` 1.0 because a sound certificate leaves every answer
correct; floor is recomputing nothing, so `above_floor` is exactly `f_stale`):
`is_widely_held` costs **$7.12e-11** per answer kept correct against
`portfolio_overlap`'s **$8.95e-13** — 80× more, because almost none of its
answers needed saving. `min_filers_covering` flags 100% of queries, so aiming and
spreading are the same policy and its `$/pt` is `inf`.

## 3r. The rung §3b said could not be produced is derivable, and it is built

`notes/findings/2026-08-18-the-rung-the-recording-mechanism-cannot-produce-is-derivable.md`.
§3b called the stability margin *"the rung the recording mechanism cannot
produce"* and treated it as **query-supplied**. It is **derivable**, and the
derived version is slightly tighter than the hand-written one.

`q_widely_held` computes `len(holders) >= 100`, so **the count is an intermediate
it already produced** and `|count − 100|` is the distance to the flip. Only the
*discarding* of that number was ever the problem.
`symbolic_ai_core/runtime/certificate.py` now carries `Sensitivity`, `Counted`
and `revalidate_sensitive`; revalidation is
`Σ lipschitz_k × |old_k XOR new_k| < slack`, with **no per-query delta rule**.

| query class | read-set flagged | **derived** | over-approx | **recovers** |
|---|---:|---:|---:|---:|
| `is_widely_held(k=100)` | 62.22% | **6.16%** | 79.8× → **7.9×** | **10.1×** |
| `holder_count` | 62.22% | 62.22% | 1.1× | 1.0× |

| arm | aim× | **$/quality point** |
|---|---:|---:|
| `is_widely_held`, read set | 1.61× | $8.67e-10 |
| **`+margin is_widely_held`** | **16.23×** | **$3.46e-11** |

> **25× cheaper per quality point, from recording one extra number per answer.**
> The derived margin flags **6.16%** against the hand-written rule's **6.38%** —
> tighter, and it needed no rule.

**Zero false survivals on every arm**, checked by an assertion that stops the run;
78 parametrised soundness cases sweep counts and deltas across the boundary.

**The residual 7.9×** is the symmetric-difference bound: an add and a remove
cancel in a count and do not cancel in a XOR. That is the price of a mechanism
that does not know what the query does with its inputs.

**What it does not do:** nothing for `holder_count` or `portfolio_overlap` (slack
0 — the answer really does move on any change), nothing for
`min_filers_covering` (no cheap sound Lipschitz bound for a set cover's optimum).
**It pays exactly where the answer is coarse, which is exactly where the waste
was.**

**Consequence for the contract in §7 item 2.** *"Return a witness where your
answer has one, a minimal dependency where you can derive one"* should now read
**"and the slack your answer has, which you already computed"**. That third
clause is worth 10.1× on the one class here that has any.

**CORRECTION, same day: "costs one integer" understated it, and the 25× answered
a narrower question than it looked like.**
`notes/findings/2026-08-18-the-derived-margin-is-the-first-arm-above-1x-...md`
priced *revalidation*, which the row above left out of both arms. The delta pass
costs **6,634 ns/key** against the digest pass's **853 ns** — **7.8× dearer** —
so the net maintenance advantage is a curve in **queries per key**:

| queries per key | 1 | 20 | 50 | 200 | **∞** |
|---|---:|---:|---:|---:|---:|
| read set | 0.25× | 0.91× | 0.99× | 1.04× | **1.05×** |
| **derived, delta supplied** | 0.04× | 0.65× | 1.22× | 2.16× | **2.91×** |
| derived, delta **recomputed** | 0.05× | 0.05× | 0.05× | 0.05× | **0.05×** |

- Overtakes the read set at **34.3 queries per key**; exceeds 1.0× at **36.4**.
- **Recomputing its own diffs is a 20× LOSS** — the XOR costs 5,911 ns against a
  277.5 ns recompute.
- Per *quality point bought by aiming*, 25× stands. Per *dollar of maintenance*
  it is 2.91× at best.

> **What survives is bigger than what was corrected: the derived margin is the
> first arm in this whole certificate programme to exceed 1.0× on a real corpus
> update.** §3b's read-set rows were 0.3×, 0.3×, 0.6×, 1.0×; the read-set ceiling
> measured here is 1.05×; the margin reaches **2.91×**.

The condition is a statement about the **workload**: the delta must come from the
update stream (§3b's own margin arm assumed this silently, via a precomputed
`delta_size`) and each key must be read ~36 times. A one-pass analysis does not
meet it; a service that re-serves answers meets it easily.

## 3s. Soundness costs 2.3×, not 8.2× — the rest was a loose bound

`notes/findings/2026-08-18-soundness-costs-2-3x-not-8-2x-...md`. Every
certificate here is sound and that had never been priced. Over 5,000 securities
where **0.76%** of answers actually moved, relaxing the derived margin by `alpha`
— flag iff `delta >= alpha × slack`:

| policy | flagged | wrong served | rate | **aim×** | sound |
|---|---:|---:|---:|---:|:--:|
| margin, α=1 (symmetric difference) | 6.22% | 0.000% | 1.0000 | 16.1× | ✅ |
| margin, α=8 | 0.64% | 0.440% | 0.9956 | 65.8× | |
| margin, α=16 | 0.24% | 0.620% | 0.9938 | **76.8×** | |
| **`\|Δcount\|` bound** | **1.74%** | **0.000%** | **1.0000** | **57.5×** | ✅ |
| **ORACLE** (a bound, not a system) | 0.76% | 0.000% | 1.0000 | **131.6×** | ✅ |

`moved_elements` bounds movement by the **symmetric difference**, where an add
and a remove cancel in a count and do not cancel in a XOR. Bounding by `|Δcount|`
is **equally sound** and much tighter:

> **Of the 8.2× looseness, 3.6× is the XOR over-counting a count and only 2.3× is
> what no sound bound removes without computing the answer.** And the trade
> reverses: **the tighter sound bound reaches 57.5×, beating every unsound arm up
> to α=8 — which serves 0.44% wrong — while serving nothing wrong.** You do not
> give up soundness to get the aim; you stop using a loose bound.

**The instrument had a hole.** `aim×` still ranks the unsound α=16 arm above the
sound α=1 arm by 4.77×. The accuracy column catches it ($7.31e-11 against
$3.97e-10) and **nothing said the two columns disagreed**.
`symbolic_ai_core/cost.py` now carries `targeting_regime()`, mirroring
`perverse_regime()`, and prints *"aiming better by answering worse … compare
aim× only across rows at the SAME rate."* **Third instance of one rule** — §3i's
*"advantage at fixed quality"*, `perverse_regime`, now this.

**A bound is not a system.** The oracle initially sat in the ledger and
*suppressed* the warning, having both the best `aim×` and a perfect rate. It is
printed as a bound now and excluded from the rows.

**The catch:** `|Δcount|` is not deployable from two snapshots — computing
`len(new[k])` *is* the recompute. It needs signed adds and removes from an update
stream, i.e. the `Delta` type parked in
`notes/decisions/2026-08-18-not-building-a-delta-type-...`. **That decision now
has a second independent motivation worth 3.6×**, and the blocker is unchanged:
nothing here emits an update stream.

## 3t. Certification is bounded by 1/(1−accuracy), and that unifies the session

`notes/findings/2026-08-18-a-model-can-only-certify-to-the-extent-it-is-usually-right.md`.
The certification value found on federated data was never checked against the
repo's own subject. `_forward_graph` already computes `s_conf` — 0 wherever a
model declined to vote — and discarded it; it is now
`ModelOutput.channels["determinacy"]`, consumed by nothing else, so no published
number moves.

Ten models, one shared config, re-fitted:

| model | votes on | acc\|voted | acc\|abst | gap | label_acc | **aim×** | ceiling |
|---|---:|---:|---:|---:|---:|---:|---:|
| routes-001 | 98.3% | 0.329 | 0.000 | +0.329 | 0.323 | **1.48×** | 1.48× |
| ruleinduce-001 | 82.9% | 0.391 | 0.030 | +0.360 | 0.329 | 1.45× | 1.49× |
| ilp-001 | 60.9% | 0.475 | 0.059 | +0.416 | 0.312 | 1.37× | 1.45× |
| syllogism-001 | 56.0% | 0.207 | 0.068 | +0.139 | 0.146 | 1.09× | 1.17× |
| **synth-001** | **2.1%** | **0.759** | 0.062 | **+0.697** | 0.077 | **1.02×** | 1.08× |

`corefer-001`, `ptrgen-001`, `vsa_perm-002` **never abstain**. `evidence-001` and
`grammar-001` abstain on **one position of 5,233** — slices, not results.

```
aim = (1−v)(1 − a_abstained) / [(1−v)(1 − base)] = (1 − a_abstained)/(1 − base)
```

> **The flagged share cancels.** Certification value is not governed by how much
> you flag nor by how *well* you flag. Since `a_abstained ≥ 0`:
> **aim ≤ 1/(1 − label_acc)**, and every model sits at or just under it.

**`synth-001` has the strongest determinacy signal in the repo** — 2.1% of
positions at 0.759 against 0.062, a **+0.697** gap — **and is worth 1.02×.**

**This unifies everything measured this session:**

| system | base | measured aim× | 1/(1−base) |
|---|---:|---:|---:|
| curriculum models | 0.077–0.329 | 1.02×–1.48× | ≤ 1.49× |
| federated resolver | 0.873 | 4.69× | 7.9× |
| maintenance, derived margin | 0.9924 | 16.1× | 131.6× |
| maintenance, `\|Δcount\|` | 0.9924 | 57.5× | 131.6× |
| maintenance **oracle** | 0.9924 | **131.6×** | **131.6×** |

The oracle's 131.6× is **exactly** `1/(1−0.9924)`. The session's whole 1.02×–131.6×
spread is one quantity: **how often the system is already right.** It also
explains §3p's candidate-recall result — recall sets the base, the base sets the
ceiling.

**A consequence, now priced.** The ceiling is attained only when abstained
positions score **0**, so strengthening the structural back-off lowers
certification value.
`notes/findings/2026-08-18-the-backoff-trade-is-real-and-one-sided.md` measured
it on four models at the repo's standard config:

| model | back-off | label_acc | acc\|abst | **aim** | $/solved>floor |
|---|---|---:|---:|---:|---:|
| **ilp-001** | **on** | **0.312** | 0.059 | 1.37× | **$3.28e-12** |
| ilp-001 | off | 0.291 | 0.001 | **1.41×** | $3.76e-12 |
| **syllogism-001** | **on** | **0.146** | 0.068 | 1.09× | **$1.98e-10** |
| syllogism-001 | off | 0.116 | 0.001 | **1.13×** | **inf** |
| ruleinduce-001 | on/off | 0.329 / 0.329 | 0.030 / 0.003 | 1.45× / 1.49× | — |
| routes-001 | on/off | identical | | 1.48× | — |

> **The trade is real and one-sided.** The back-off buys **+0.021** and
> **+0.030** accuracy and costs **0.04×** of a metric capped at **1.49×** — and
> for `syllogism-001` that accuracy is the difference between beating its 0.143
> floor and reading **inf**. §3t's consequence is true and economically
> irrelevant.

`ruleinduce-001` shows the mechanism exactly: `label_acc` is **identical** both
ways because the prior **helps where the model abstains** (0.003 → 0.030) and
**hurts where it votes** (0.397 → 0.391). It is attached at *every* hidden node,
not only abstained ones.

**Instrument finding: the guard did not fire.** `targeting_regime()` compared the
*global* aim winner against the *global* rate winner, and `ruleinduce-001` off
held both — while the real inversions are **pairwise within a model**. It now
finds any inverted pair and reports the sharpest. **Third strengthening of a
ratio guard this session**, and the second found by using the instrument on real
rows rather than a fixture.

**Also unreproduced:** `symbolic.py`'s docstring credits the back-off with taking
`ruleinduce` from 0.076 to its current score. Toggling the flag today moves its
accuracy by **0.000**. Whatever produced that gain, the flag alone does not
reproduce it; not chased.

## 3u. Escalation and maintenance are one expression (a DERIVATION)

`notes/findings/2026-08-18-escalation-and-maintenance-are-one-expression.md`.
Labelled as a derivation on purpose: the algebra is new here, the empirical
content is five rows that were already §3b's.

With `f_flagged` = P(flagged), `f_needed` = P(this case needs the expensive
path), `precision = P(needed | flagged)`, `recall = P(flagged | needed)`:

```
realised  =  recall / f_flagged  =  (1/f_needed) × precision
ceiling   =  1 / f_needed        attained iff precision = recall = 1
```

- A **sound** certificate has `recall = 1` and realises `1/f_flagged` — **§3b's
  `advantage = min(compute/check, 1/P_hit)` exactly**.
- A **model's abstention is not soundness**, so `recall < 1` (`ilp-001`: 0.535).
- An **oracle** attains `1/f_needed`.

> **§3b's `1/P_hit` is the sound case; the achievable ceiling is `1/f_needed`,
> and the gap is the certificate's over-approximation** — 8.2× for the
> symmetric-difference bound, 2.3× for `|Δcount|`.

**Independently confirmed rows** (measured from timings and USD, predicted from
invalidation counts) — the other seven rows in the script are **identities** and
confirm nothing:

| row | predicted | measured | error |
|---|---:|---:|---:|
| §3b witness (path edges) | 29,389.5× | 29,182.1× | 0.7% |
| §3b optimality, recorded | 3.27× | 3.27× | 0.0% |
| §3b optimality, minimal | 21,788.8× | 21,534.3× | 1.2% |
| §3b full answer | 14,120.1× | 13,987.1× | 1.0% |
| §3b maintenance, `min_filers_covering` | 1.000× | 0.998× | 0.3% |

**No arm exceeds `1/f_needed`.** That is the one thing the table could have
falsified.

**Near miss, recorded:** the first version presented all twelve rows as
confirmations. For maintenance `aim = 1/f_flagged` *by construction*; the
curriculum rows rearrange to the expression `aim` came from. A suspiciously
small error (1.2% over five orders of magnitude) was the tell. See
`notes/lessons/2026-08-18-a-validation-that-reproduces-its-own-definitions.md`.

**What it is good for:** two quantities decide any certification opportunity and
both are measurable before building — `f_needed` sets the ceiling, and
`f_flagged/f_needed` is what the mechanism wastes.

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
| "two unrelated arms, one axis — now worth treating as a property of the substrate rather than two observations" (mine) | **four**, and two of them **predate the session**. The existential/universal asymmetry was measured on this same route network before the certificate arm began (§3, 247x / 2.0x). What this session added is the *maintenance* economics and the appearance of the axis in plain set queries with no proof machinery at all — which is the better claim, and the one that answers `datalog/proof.py`'s stated open question |
| "no file on disk links a CIK to an LEI" (mine, §3j) | **false.** `wikidata/idbridges_full_p0.parquet` carries 3,660 `sec` and 53,198 `lei` edges; **2,113** entities carry both. I searched for the *mechanism* (a `same_as` column) and never for a file named after its purpose |
| "the composite is `(1 − coverage) × f_name`" (mine, `bridged_join.py`) | the **product of the marginals**, and they are not independent: crosswalk coverage is enriched **1.33×** (z = 5.03) toward the filers names cannot settle, so it underpriced the crosswalk by 10.9% of itself. Measured joint `f` **9.81%**, not 11.01% |
| "the curated crosswalk is 3.43× better targeted" (mine) | **artefact.** The dollar/count ratio's ceiling is `1/coverage`, so a smaller crosswalk scores higher mechanically. Against an oracle at each crosswalk's own k they attain **69.8%** and **66.0%** — 1.06× apart. Saturation, not targeting |
| "tier 3 is not a procurement problem — a relationship GLEIF did not record was not recorded anywhere" (mine, §3l) | **untested assumption, and the null is worse news.** wikidata holds **4.3×** more ownership structure and settles **3** more filers of 598. Only 3,996 of 1.28M edges are expressible about LEIs because **1.58%** of entities carry a twin. The tiers are **not independent**: 2 and 3 are gated by tier-1 identity, which saturates |
| "purchasable reach saturates" (mine, §3l headline) | **conditional, not a law.** Top-7.5% mass share spans **27.3%** (GitHub events) to **96.9%** (13F dollars), a 3.5× span. Replaced by a decision rule: measure that share before acquiring anything |
| **"the federated advantage is 6.8×→12.2×, and closure buys 1.22×" (mine, §3j–§3o, six arms)** | **determinacy priced as accuracy.** `advantage(f)` has no slot for accuracy, so equal accuracy was asserted silently once per arm. Against a floor sharing the same candidate sets the resolver is **+0.9%** at entity level, **−0.1%** at group level, and **does not beat its floor**. The honest number is **4.7×** on $/capability-above-floor — §3p |
| five end-to-end query classes quoted with **no floor** (mine, across three findings) | audited with `scripts/query_floors.py`: **nothing retracts**, no floor meets its system. But `collaborators` had **28.8%** of its score bought by a query-blind popularity guess — read its lift as **0.297**, not 0.417 — and the other four lose 4–6%. `symbolic_ai_core/cost.py` had been enforcing `accuracy - floor` in code the whole time |
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
9. ~~The shrinking-corpus inversion.~~ **Run — §3b. It narrows 93x → 72x and
   does not invert; the belief held at 0.8 was false.**
10. ~~Put this session's work through `symbolic_ai_core/cost.py`.~~ **Done —
    §3p, and it was the most consequential thing in this revision.** The
    resolver does not beat its floor; six arms had priced determinacy and read
    it as accuracy. Original text kept below because the reason it was written
    is exactly the failure it caught.
    **Put this session's work through `symbolic_ai_core/cost.py`.** Everything
    here was priced with hand-rolled arithmetic in scripts while the repo's own
    ledger sat unused, and the floors now exist to make it computable. *Why it
    matters:* a number on a different basis from the published ones is not
    comparable with them, which is most of what a ledger is for. One arm, and it is the falsifier for the
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
