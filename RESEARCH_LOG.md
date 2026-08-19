# Research log

Where this repo actually is, for someone arriving cold. `README.md` documents
the harness and the models; `ROADMAP.md` holds the task list and the working
rules; this file says what is *known*, what is *shaky*, and what is *wrong that
used to be believed*.

**Model names carry a version.** Every model is registered as `name-001`, and a
bare `name` resolves to the highest version, so `--models corefer` still works
and means "the current one" while `corefer-001` pins a specific thing. A number
in this file is attached to a versioned name because it has to be: `corefer`'s
type head went 0.174 -> 0.612 in one commit and `workspace` moved from eighth to
joint first when a cap was raised, and both silently redefined what an earlier
row meant. A variant is now `corefer-002` or `corefer-noprose`, a separate row in
the same sweep.

Numbers here are from `runs/full179`: all 179 generatable lessons, 20 training
episodes each, evaluation seeds a million away, CPU. The sweep is the authority;
nothing in this file was measured by a scratch script.

## The question

Two tasks on the same harness. Next-token prediction, and **masked-node
prediction** — hide nodes in the typed term graph an episode was rendered from,
predict each one's *label* (which symbol) and *type* (what kind of node). The
graph is not a parse of the text; it is the thing the text was generated from,
so the answers are exact and unannotated.

Nineteen models, two families. Rule-based ones are the subject; six neural ones
exist as a control and are off by default.

## Every reader number in this repo was measured against distractors that could not bite

**Status: measured, 2026-08-19 — three domains, each with a clean control, a
single-distractor arm, and a repair; the size-dependent numbers carry their
injection parameter. Not yet challenged by anyone who did not write it, though
the sharpening below came from trying to refute it.**

Each of the three world-IR domains ships distractor sentences whose stated
purpose is to test whether the reader rejects text that is not a claim. In all
three the distractor is inert **by construction**, and in two of the three the
reader never even types it. The measurement that says so is one line per domain:
does the read world contain the distractor?

| domain | distractor | admitted as a claim | why it cannot bite |
|---|---|---:|---|
| flood | *"A disused track once ran from X to Z"* | **60/60** | endpoints drawn from regions appearing nowhere else |
| scheduling | withdrawn machine, cancelled job, *"set up for anodising"* | **0/60** | no capability, no quantity, or a word outside the vocabulary |
| solvency | *"A former subsidiary, sub_99, was divested"* | **0/60** | one entity, so no branch matches — and no filings anyway |

So there are **two** kinds of defanging, not one. Flood's reader admits a false
claim every single case and the generator makes it harmless. Scheduling's and
solvency's readers never face the question, which matters because both were
credited with a vocabulary that "does double duty — settles signature collisions
**and** filters distractors". That credit was earned against sentences the
vocabulary never had to work for.

Pointing each distractor at entities that matter — a phantom road between two
**real** regions, a machine capability the floor does **not** have, a divested
subsidiary that **files** — gives the honest surface:

| domain | published | honest surface | with the checks below |
|---|---:|---:|---:|
| flood (interleaved) | 0.988 | **0.679** | **0.933** |
| scheduling | 1.000 | **0.790** | **1.000** |
| solvency | 1.000 | **0.450** *(floor 0.550)* | **1.000** cued / **0.450** uncued |

Solvency's is the worst and is worth stating plainly: on the honest surface the
published pipeline is **worse than answering "no" every time**. That figure
depends on the size of the injected filing — the dose-response is U-shaped,
0.630 / 0.665 / 0.515 / 0.450 at 5% / 10% / 25% / 50% of the threshold, because
a spurious figure dated at the determination date *replaces* the real one and so
lowers the sum when small and raises it when large. Quote the injection with the
number.

### What the search for a repair turned up

- **Solvency's ownership paragraph was decorative.** `read_signature` enrols a
  member the moment it files, so deleting the entire first paragraph — one of the
  domain's two claim kinds — changes the answer on **0 of 200** cases. The reader
  was reported at 1.000 accuracy and 1.000 filing recall in all six cells of
  V × arrangement without ever reading the group structure, because the generator
  never files for a non-member. `read_signature_consolidated` is registered
  beside it.
- **The repairs are conjunctions, not alternatives.** For the divested filer the
  staleness gate alone buys 0.035 and the consolidated reader alone buys nothing;
  together they buy 0.550, because the entity is enrolled by *either* its filing
  or its ownership sentence and each fix closes one route.
- **One component transfers across domains unchanged** — the first here.
  `symbolic_ai_generators/staleness.py` asks whether a sentence *withdraws* what
  it asserts. **Cancellation, not tense**: a tense gate destroys true claims
  phrased in the past (0.645 scheduling, 0.317 flood) and misses *"a disused
  track once ran"* outright.
- **And "closed-class" was an argument, not a measurement.** Run on English
  nobody here wrote, the shipped cue list was **~85% false positives**: 2.29% of
  36,223 scientific sentences, of which `used to` — the *passive of use*, *"is
  used to obtain"* — was 53.5%. On 75,555 sentences of narrative the dominant
  error was different again: `struck`, the verb *strike*, at 29.9% against **two**
  fires in the scientific corpus. Three corrections, each on meaning rather than
  on the count, took real-prose firing to **0.33%** and **1.35%** — and left every
  generated-surface number **byte-identical**, which is the evidence that what was
  removed was noise. Both corrections after the first came from **adding a genre**,
  not from thinking harder about the list.
- **It fails where the predicate is itself a negation.** The gate deletes flood's
  true *"…it is no longer passable"*, costing 0.055 on the clean surface, because
  it cannot distinguish a sentence that withdraws its own claim from one asserting
  that something *was* withdrawn — and `flooded` **is** a cancellation. A property
  of the predicate; no cue list fixes it.
- **The honest floor is the uncued arm.** *"sub_98 left the group in April"* is
  semantically stale and carries no declared cue, and nothing built here repairs
  it: 0.450, unchanged by every check. A test asserts this so the 1.000 above is
  not read as a solution.

### And on real prose the signature carries almost nothing

The instrument's floor, measured with the instrument. On the generated surfaces
the biggest signature bucket holds **one** claim kind for scheduling and solvency
— which is what an ambiguity mass of 0.000 looks like, and a bucket can be huge
and still hold one kind: solvency's holds half of all its claim spans.

On real prose the biggest bucket is the **empty** signature — no recognised
entity, no number, no date — and it holds **44.2%** of 36,223 scientific
sentences and **46.9%** of 75,555 narrative ones, expressing plainly different
predicates. So **ambiguity mass on real prose is at least 0.44**, against the
0.000 the repo cites when arguing a content-free reader can work.

The reason is structural rather than an artefact of entity detection: **a
signature over (entity counts, numbers, dates) never looks at the verb**, and the
verb is where a real predicate lives. Signature determinacy is a property of
surfaces whose claim kinds were *given* distinct arities.

Worth recording as method: the first version of that measurement used **entropy**,
which showed real abstracts carrying *more* signature entropy (3.65 bits) than any
generated surface (2.26–2.61) and answered nothing. Entropy says how much a
signature varies, not how much it determines. It was chosen because it needed no
labels — which is exactly why it could not answer the question labels are for.

### And the signature audit predicts none of it

`audit_surface` is credited with predicting four things — reader difficulty, where
error concentrates, payback, and maintenance. It predicts neither of the two
failures above, and both were found the same day:

- it scores the two flood surfaces **identically** (ambiguity mass 0.640, the same
  280 prose flags) while emission soundness on them is 1.000 against 0.649;
- it scores scheduling at **0.000 ambiguity mass**, and one admitted sentence takes
  that domain from 1.000 to 0.790, every failure unsound.

The reason is exact: **it measures ambiguity of the signature, not fragility of
the vocabulary.** *"machine_0 was set up to paint"* carries the
`(machine, capability)` signature unambiguously, and is false. Signature
determinacy says a reader *can* type a claim; it says nothing about whether it
*should*.

### And on real prose the sentence is the wrong unit

The first task here with real prose **and** a real answer: Wikidata's `P749`
(*parent organization*) against the English Wikipedia intro, 148 companies. A
`P749` statement carrying an end time names a parent the company *used to* have,
so this is a labelled **staleness** set.

Context before any arm. The current parent is named in the intro on only
**0.696** of articles. `stale_by_cancellation` flags a sentence on **0.338** of
them — against 0.004 of scientific abstracts — because company prose is dense in
cancellation language.

| arm | answers | correct | precision | picks a **former** parent |
|---|---:|---:|---:|---:|
| naive patterns | 0.622 | **0.392** | 0.630 | 0.027 |
| + sentence gate | **0.568** | **0.351** | 0.619 | 0.027 |
| + clause gate | 0.615 | 0.378 | 0.615 | **0.020** |

**The sentence gate loses coverage and accuracy and removes no staleness at all.**
*Miramax* is the worked example — current *beIN Media Group* / *Paramount*, former
*Filmyard* / *The Walt Disney Company* — where the sentence gate answers *"Walt
Disney Company"*, because it kept the sentence naming the dead owner and deleted
the one naming the live one.

> **The unit of staleness is a clause, not a sentence, and the generated surfaces
> could not have shown that** — one sentence carries one claim there, which is why
> the gate leaves all three byte-identical. That is a defect in the benchmark's
> **granularity**, and `audit`'s spans, `unconsumed`, `evidence_conflict` and
> `filter_stale` all rest on the same assumption.

**And the unit is a real object, not a slider.** Sweeping five granularities gives
a **peak** on both corpora, and the ends fail identically: on Wikipedia the
*finest* split reproduces the *sentence* split's numbers to three decimals in
every column — 0.542 / 0.327 / 0.024 — because a splitter that cuts through
`a subsidiary **of** X` leaves no fragment matching the pattern, which is
indistinguishable from deleting the sentence. **Over-splitting is over-deleting
by another route**, so the fix has a principled stopping point: cut at boundaries
the patterns do not cross.

**Reproduced in the benchmark, and fixed.** `stale_clause` prefixes a real
member's filing with a former-parent clause — *"sub_0, formerly a subsidiary of
sub_97, reported 105.87 USD, filed 29 May 2026"*. Over 120 seeds the sentence gate
takes the accumulating reader from **0.925 to 0.625**: not merely useless but
**actively harmful**, exactly the *Miramax* mechanism. `filter_stale(…,
unit="clause")` gives **1.000** to both readers, and it does two jobs at once —
it removes the dead claim *and* the second entity that made the filing's binding
ambiguous. **A gate that cuts at the right granularity does not just delete less;
it simplifies what is left.** Default stays `"sentence"` so earlier numbers keep
their meaning.

And the proportion is sobering: the former-parent error is **2.7%** of articles
while precision among answered is **0.63** against a 0.696 ceiling. On real text
the staleness problem is a small slice of the error and the dominant one is that
extraction is hard — perfect staleness handling moves accuracy 0.392 → 0.419.

### And a packed sentence is ambiguous by definition

The constructive half. Each generator now takes a **`packed`** option that renders
two claims as one sentence, with a span for each over the same text — the
granularity real prose has and none of these surfaces ever did.

| domain | packed | ambiguity mass | accuracy | floor |
|---|---|---:|---:|---:|
| solvency | no | **0.000** | 1.000 | 0.567 |
| solvency | **yes** | **0.741** | **0.567** | 0.567 |
| scheduling | no | **0.000** | 1.000 | 0.658 |
| scheduling | **yes** | **0.279** | **0.658** | 0.658 |

**Both readers collapse to their floor, exactly**, and the mechanism is one diff:
scheduling's `has_capability` goes from four claims to two while every capacity
survives, because `read_signature` branches on shape with an `elif` chain and a
packed sentence matches the capacity branch first.

**The audit predicts it offline** and ranks solvency as the worse case — the first
thing in this whole line that the instrument gets *ahead* of. It does so because
packing is what it is about, and that is a theorem:

> **A signature is a function of the sentence.** A sentence realising two claim
> kinds maps to both, so `ambiguity_mass` is bounded below by the share of
> multi-claim sentences and **no signature reader can be packing-robust**. Real
> prose is packed.

Flood is the control and gives the design rule: **accumulate, do not branch.**
`read_content_roles` recovers both kinds from a packed sentence because it folds
crossings into links rather than selecting a branch — which is a property of
**control flow**, exactly what the audit cannot see. The theorem and its escape
sit either side of the instrument's boundary.

**Built deliberately, it strictly dominates.** `read_signature_accumulating` in
both collapsed domains extracts every claim pattern per sentence rather than
selecting one branch, binding a solvency filing to the entity *nearest the money*
— positional and content-free. Packed: **1.000** in place of 0.567 and 0.658.
Unpacked and on every honest distractor surface: **identical** to the branching
readers (solvency 1.000 / 0.475 / 0.475 / 0.433, scheduling 1.000 / 0.767 /
0.967), so the extra permissiveness admits nothing the branching reader refused.

That sharpens the theorem rather than escaping it: **the signature loses the
classification; accumulation recovers the content.** No reader can decide a packed
sentence's kind from its signature, and the claims were never gone.

### The floor is liftable by reading, in exactly one domain

The uncued stale sentence — *"sub_98 left the group in April"* — is stale because
of what **leave** means, and `symbolic_ai_generators/wordnet.py` reads WordNet
from the distributed archive with the standard library only. Three corrections
were needed and each is a scope statement about the resource:

- **supersenses classify by subject matter, not aspect** — `cease` is
  *verb.stative* and `divest` is *verb.possession*, exactly like `own`;
- **ancestor depth decides the false-positive rate** — `change` and `transfer`
  sit near the root and account for 9,090 of 9,584 token fires on real prose;
- **sense dominance, not sense priority** — first-sense selection fires on
  `dated`, whose first WordNet sense is the romantic one.

With all three, solvency's uncued arm goes **0.475 → 1.000 at no cost on the
clean surface** — the first thing that moves that arm by *reading* rather than by
refusing.

And the same gate takes **flood from 0.589 to 0.014** and scheduling from 0.767
to 0.675. `can` is what kills flood: WordNet has it as a verb — *"terminate the
employment of"* — so one of its two senses reaches `remove`, and it appears 90
times in thirty documents. Sense dominance protects against a *rare* wrong sense
and not against a *low-sense-count* word one of whose readings is a transition.

| | `stale_by_cancellation` | `stale_by_verb` |
|---|---|---|
| vocabulary | **closed-class**, 11 cues | **open-class**, 11,529 lemmas |
| real prose firing | **0.004** | **0.156** |
| three generated surfaces | **byte-identical** | +0.525 / −0.092 / −0.575 |

> **A closed-class feature transfers; an open-class lexicon does not.** Its
> false-positive rate grows with the vocabulary it draws on, and a *deletion*
> gate's damage grows with the claim density of the surface — and the two
> multiply.

### The floor, and the one thing that lifts part of it

The uncued arm is where every **detector** stops. What moves it is the other kind
of response — not deciding whether the claim is true, but proving the answer does
not depend on it. `symbolic_ai_generators/solvency/certificate.py` asks whether
the verdict survives removing **any single member**, and on the uncued arm
**certified ⟺ correct, exactly**: 0.485 accuracy with 103 silent errors becomes
0.485 coverage with **zero**.

It is only the **monotone half**, and the mechanism is not the one predicted.
Removing a member can only *lower* the sum, so a `False` verdict survives every
deletion for free: the check fires on **1.000** of false verdicts and **0.000** of
true ones, and its clean-surface coverage of 0.550 *is* the false-verdict share.
Fourth appearance of the same asymmetry here — what is cheap to prove is the
negative.

And it carries a warning that generalises past this domain. Add a spurious
*filing* — a channel the membership hypothesis does not cover — and coverage
**rises** 0.485 → 0.935 while accuracy among the certified falls to 0.481. It
rises *because* the corruption is larger: the spurious figure pushes the sum
clear of the threshold, so no member deletion can flip it. Flood's certificate
does the same, firing on 12.7% of the `hard_distractors` surface against 5.6% of
the clean one, because phantom links add 2-edge-connectivity.

> **A certificate that asks "would a small perturbation change the answer?" reads
> a large error as stability.** Coverage is not a measure of reliability, and
> comparing coverage across surfaces is a trap. Report it with the accuracy among
> the certified, on the same surface, always.

### And the explanation fabricates where the reader does

Inspectability is one of the five properties, and it had only been checked on the
easy surface. Rendering from the **read** world and checking every citation
against the **true** one, 300 seeds:

| renderer | surface | cites | **false / citation** | any false | **\| correct** | `ungrounded` |
|---|---|---:|---:|---:|---:|---:|
| template | clean | 2.01 | 0.0025 | 0.005 | **0.000** | **0.000** |
| template | honest | 2.01 | 0.0025 | 0.005 | **0.000** | **0.000** |
| complete | clean | 11.74 | 0.0117 | 0.066 | 0.052 | **0.000** |
| **complete** | **honest** | 11.56 | **0.0388** | **0.378** | **0.076** | **0.000** |

**A correct answer with a fabricated justification, at 1 in 13.** And it is not a
volume effect — per citation the complete renderer is **15.5×** worse, because the
extra facts it cites are the **load-bearing set computed from the read world**,
which is exactly where a phantom link lives. Citing more is not the problem;
citing *what the answer depends on* is, when the answer depends on something
invented. The template renderer, citing two facts the reader gets right whatever
the distractors do, is **surface-independent** at 0.000.

`ungrounded` flags **none** of it, in every cell — its scope note with a number
attached. And it reprices an earlier row: *"an explanation that omits nothing
material, for 37% more words"* priced completeness in **length**; the currency is
**truth**.

**And the fabrications are exactly where the arity law says they must be.** By the
predicate each citation rests on: `mass`, `capacity`, `needs`, `demand`,
`bridge_on` and `load_limit` are **0 false in 1,680 citations**; `flooded` 0.044,
`depot` 0.066, and **`link` 0.642** — 70% of every falsehood in 4% of the
citations. `link` is multi-valued with no second source, which is the channel
detection fires 0.000 on.

So `render.uncorroborated()` marks the citations nothing here can check —
**88 of 88 false citations flagged, inside 7.5% of them.** The renderer cannot be
made honest; it can stop presenting eleven facts as one kind of thing.
*"Here are eleven facts, four of which nothing corroborates"* is a third option
beside the two-fact summary and the eleven-fact account, and it is the honest one.
Precision is 0.51. The recall is 1.000 because no reader error here lands on a
value — and testing *why* produced something better than the caveat. Overlapping
the value registry, as a real vocabulary would be, takes accuracy **0.673 → 0.189
→ 0.000** and produces **no** value falsehood at any setting: **a value error
silences rather than fabricates**, because a mis-slotted mass disqualifies a
vehicle so nothing is cited about it. Citations fall 2,266 → 1,452 → 280 and the
`link` fabrications vanish with them.

Two things fall out. **The value registry is worth the entire capability on the
honest surface** — 0.673 → 0.000, where it had only been priced as a ceiling on
the easy one. And **fabrication counts fall as capability falls**, 88 → 27 → 27,
so the most broken reader fabricates least in absolute terms because it says
almost nothing: report fabrication against coverage or not at all. The conditional
to carry is that values which **gate** qualification silence, and values which
**feed** the computation fabricate — and there the marker would miss them.

### And an explanation's error rate is not bounded by the answer's

Flood's values **gate** — a mis-slotted mass disqualifies a vehicle, so nothing is
cited and the explanation stays honest. Solvency's **feed**: revenue figures are
summed and the renderer states the consolidated total as its central sentence.
200 seeds, rendered from the read reading:

| surface | verdict wrong | **stated total wrong** | mean \|error\| | `ungrounded` |
|---|---:|---:|---:|---:|
| clean | 0.000 | 0.000 | 0.000 | 0.000 |
| **hard filing** | **0.485** | **1.000** | **0.398** | **0.000** |
| hard both | 0.550 | **1.000** | **0.999** | **0.000** |

**The stated total is wrong on every case while the verdict is wrong on 0.485**,
because a wrong sum only flips a threshold test when it crosses the threshold. So
**more than half of all cases carry the right verdict justified by a false
number** — flood's version was 1 in 13, solvency's is 1 in 2, and the falsehood is
the sentence the answer is *about*.

Nothing here flags it. `ungrounded` fires 0.000 and is right not to: the spurious
figure **is** in the world as read. And the uncorroborated marker cannot either —
solvency's revenue channel is the one cell above admitting **neither** a second
reading nor insensitivity.

> **An explanation's error rate is not bounded by the answer's.** A derived figure
> is wrong whenever *any* of its inputs is; the answer is wrong only when the
> error crosses a decision boundary. The gap grows with how much aggregation sits
> between the claims and the verdict, so **inspectability is a free property of a
> symbolic pipeline only when the kernel uses claims directly.**

### What each channel admits, and what it costs

Two responses to a claim the reader may have got wrong, and they are gated by
different properties. **Detection** reads the fact a second time and compares —
sound *and* complete, gated by the role's **arity** and by whether a companion
sentence pins it. **Insensitivity** proves the answer does not depend on the
claim — sound but lossy, gated by the shape of the **decision**. Neither is a
better check; they are answers to different questions.

| domain, damaging channel | arity | detection | insensitivity | compute | break-even `W` |
|---|---|---:|---:|---:|---:|
| flood, `link` (phantom road) | multi | **0.000** | 0 wrong at 48.8% | 1.0× | **0.60×** |
| flood, roles (misfire) | single/multi | **0.774 – 0.976**, 0 false alarms | — | ~1× | — |
| scheduling, `has_capability` | multi | **0.000** | 0 wrong at **52.5%**, 43.5% of it free | 3.07× | **2.95×** |
| scheduling, `needs_capability` | **single** | **1.000** | — | ~1× | — |
| solvency, `owns` | multi | **0.000** | 0 wrong at 48.5%, all of it free | 1.0× | **free** |
| solvency, `revenue` | multi | 0.000 | **none possible** — a sum moves on every term | — | — |

`W` is what **one wrong answer must cost in units of one right one** before
refusing pays — `cost.break_even_wrong_cost`. It exists because
`usd_per_solved_above_floor` counts answers, so a sound system that refuses half
of them scores *worse*, which is the gap `cost.py`'s own header names. Solvency's
certificate is free because its certified set **is** its correct set; flood's is
not free despite costing nothing to run, because it keeps only 72% of the correct
answers and something has to pay for the other 28%.

Three readings worth carrying:

- **The detectable errors are the harmless ones.** Scheduling's detectable
  channel costs 0.035 and its undetectable one costs 0.210 with every failure
  unsound; flood's most detectable misfire direction costs 0.865 and its
  undetectable one 0.655. Arity has nothing to do with damage.
- **Undetectable is not uncertifiable.** Every multi-valued channel above admits
  insensitivity, and in two of three the useful half is **free** — deleting a
  claim can only make an instance *more* infeasible or a sum *smaller*, so the
  negative verdict is certified with no extra solve. That is the fourth
  appearance here of *what is cheap to prove is the negative*.
- **Only an aggregating decision denies both.** Solvency's revenue channel is
  multi-valued *and* every term moves the sum, so it has no second reading and no
  insensitivity. That is why the repair there had to be in the **reader** —
  membership from ownership, plus the staleness gate — and why it needed **both**:
  each alone bought 0.000 and 0.035, together 0.550.

### The rule this leaves

> **A distractor that cannot be admitted, or that is admitted and cannot matter,
> tests nothing.** Every rejection number in this repo predating 2026-08-19 was
> measured against one of those two, and `hard_distractors=True` — now present in
> all three generators, defaulting to `False` so published numbers keep their
> meaning — is the setting new work should use.

## The substrate carries a task no single kernel can, at $2.15e-8 per solved episode above floor

**Status: provisional, 2026-08-18 — measured, ablated against three controls,
floored against seven baselines, checked against an oracle that shares no code
with it, and not yet challenged by anyone who did not write it.**

This is a different *kind* of row from everything below it. Every other number
in this file is a model on the 179-lesson curriculum. This one is the first
number produced by the substrate the repo pivoted to on 2026-08-18 — a typed
world-program runtime, in which language, logic, physics and geography are
overlapping views over one world rather than separate apps.

The task (`symbolic_ai_generators/flood/`): a generated flood-logistics world.
Six regions wired as a **ring plus chords**, so the road network is genuinely
cyclic; flooding closes one or two regions; two thirds of the links carry a
posted bridge limit as a `Quantity` in kg; three trucks with unladen masses and
capacities; a demand site needing a stated mass. **Which vehicles can deliver?**
A vehicle qualifies with the capacity and *some* route whose every bridge admits
its laden mass — and the shortest route is frequently the one with the weak
bridge.

One flow DAG, six nodes, three kernels, two couplings. Datalog computes the
reachability closure over the cyclic network; ASP builds its completion space
from datalog's *derived* facts and enumerates candidate routes; SMT checks the
laden mass against the bridge limits, which are exactly the claims the
relational projection **discards** — its discard record says so, with the
reason *"a Quantity carries a unit; datalog is untyped and projecting it would
drop the unit"*. ASP literally cannot see the numbers it would need.

200 seeds, against a brute-force oracle whose source is asserted by test to
contain no reference to clingo, z3, datalog, `get_kernel` or `evaluate`:

| arm | agreement |
|---|---|
| **full flow (datalog + ASP + SMT)** | **1.000** |
| ablation: ignore flooding (no datalog) | 0.690 |
| ablation: ignore bridge limits (no SMT) | 0.535 |
| ablation: first route only | 0.855 |
| floor: capacity ≥ demand and laden ≤ **max** limit | **0.440** |
| floor: capacity ≥ demand only | 0.410 |
| floor: always none | 0.350 |
| floor: always all | 0.315 |
| floor: lightest vehicle only | 0.135 |

**Lift +0.560 over the strongest of seven floors. Every ablation is strictly
worse, so no kernel is decorative**, and removing SMT costs the most, which is
the right ordering — the load arithmetic is the part nothing else can do at all.

Priced, at the stated sheet of $0.02/core-hour:

    mean cost per episode     $1.20e-08
    $/solved above floor      $2.15e-08      (46.6M per dollar)
    mean cpu / wall           5.5 ms / 5.5 ms

**What it prices is reasoning given a world, not language.** No parser is in the
ledger. The report exists so the task has a natural-language surface and so the
oracle reading is free by construction; turning that report back into the world
is the problem this repo measures at 0.016 exact recovery, and it is untouched
here. Reading this as a language result would be the corpus confound again.

Full write-up, including the seven floors and the two predictions that missed:
`notes/findings/2026-08-18-three-kernels-solve-a-task-none-of-them-can.md`.

## The channel is walked: 0.989 against a 1.000 lookup floor, control at chance

**Status: provisional, 2026-08-17 — measured, controlled, mechanism logged, not
yet challenged by anyone who did not write it.** The section below records the
same channel half-taken at 0.532; both stand, and this supersedes its number.

`acc | derived, not copyable`, 1,325 fills, 704 eval episodes, 8 draws:

| | `derive:wordnet` | control `-perm` | `-shuffled` |
|---|---:|---:|---:|
| **`frontier-007`** | **0.9890** | **0.1429** | **0.9890** |
| `frontier-001`…`-006`, seven variants | 0.5315 | 0.0722 | 0.5315 |
| the twenty published models | ≤ 0.155 | ≤ 0.178 | ≤ 0.155 |
| derivation floor — a lookup, *told* the premise | 1.0000 | 0.1669 | 1.0000 |
| blind marginal | 0.1672 | **0.1433** | 0.1672 |

`treatment − control` is **+0.846** on a channel measured 0.833 wide, and the
control lands on **0.1429** against its own blind marginal of **0.1433** —
chance, to three decimals. `-shuffled` ties the treatment to four decimals, the
isomorphism prediction every published model also satisfies. A lookup *handed*
the premise gets 1.000; this chooses its own and gets 0.989.

Pooled, on `runs/full179`: `label_acc` **0.4376**, the highest in the repo,
+0.081 over `frontier-001` and **6.3× its renamed accuracy** (0.2188 vs 0.0345).
Still ~eleventh on bits and still 0.22 down under renaming where `corefer` is
0.003 down, so this is not a reasoning result.

**The cause is the precision floor alone, and my "conjunction of three" was
wrong.** I reported the result as needing three changes together, on the grounds
that single-factor ablation had returned seven nulls. `agent-refuter` ran the
single-factor ablation *on the winning model* — which I never did — and it is one
sufficient cause:

| on `derive:wordnet`, `acc \| derived, not copyable` | |
|---|---:|
| `frontier-001` (floor 0.5) | 0.5315 |
| `frontier-006` = `keep_by_path` + `propose_support=2`, floor 0.5 | 0.5315 |
| **`frontier-floor`** = the floor and nothing else | **0.9748** |
| `frontier-008` = floor + both | 0.9890 |
| `frontier-008` with `propose_support=12` | 0.9890 |

`propose_support` is **exactly inert**; `keep_by_path` is worth **+0.0142** and
only *after* the floor. The guard my account named,
`[slot=1, nsib=2] -> map:sib@2`, is **not in the fitted model** — the carrying
rule sits at the one-atom guard `[slot=1]`. The seven nulls were seven variants
that all left the floor at 0.5, and what they showed was that nothing *else*
matters, not that the cause was conjunctive. **One global precision floor cannot
serve both ends of a guard lattice** survives as the mechanism; the story about
how it was found does not.

`frontier-floor` also **beats** `frontier-008` on pooled accuracy (0.4493 vs
0.4407), on bits, on `acc | rest, not copyable`, and on type (0.8637 — which is
`frontier-001`'s number, the one `frontier-009` was separately built to recover).

**On four columns. Nobody checked the fifth, and it is the one that matters
most.** `frontier-floor`'s renamed accuracy is **0.0469**, a drop of −0.406 —
**the least equivariant model in the family**, worse even than `frontier-001`'s
−0.372. Composing it with the repaired type head (`frontier-floortype`,
registered under that name after `frontier-best` turned out to be a false claim)
inherits it exactly. Against `frontier-typepoint`, which differs *only* in
`keep_by_path` and `keep_per_guard`:

| | cost | buy |
|---|---:|---:|
| `label_acc` | −0.0063 | |
| `label_bits` | −0.059 | |
| **renamed accuracy** | | **+0.174** |

the same trade `frontier-003` found from the other direction. **There is no
single best frontier model**: `frontier-floor`/`-floortype` for accuracy and
bits, `frontier-typepoint` for equivariance.

**And the pointed conjunct couples the heads.** `type_bits` came in at 0.9361
against `frontier-typepoint`'s 0.9074 on an *identical* type configuration —
because that conjunct reads the label head's prediction. "Every label number is
bit-identical" remains a valid control for a type change; the reverse is now
false, and any type comparison across different label heads is confounded unless
`type_pointer` is off.

**And the arm had only ever been measured in accuracy.** A rule fitted to noise
here emits one of six values and is right about 1/6, which is what chance also
reads as — so the void condition could never have fired. `derived_split.py` now
prints **bits** on the derived bucket, and the abstention baseline is
`frontier-nomap` at **10.16 bits in both arms**:

| | treatment acc | treatment bits | control acc | control bits |
|---|---:|---:|---:|---:|
| `frontier-008` | **0.989** | **2.363** | 0.143 | 9.281 |
| `frontier-001` | 0.532 | 5.663 | 0.072 | 9.710 |
| `frontier-nomap` | 0.000 | 10.166 | 0.000 | 10.161 |

In the control the model is **better than abstaining** (9.281 against 10.161), so
"confidently wrong" overstates it — it is mildly informative and useless at
argmax, which is a different thing and is what the column was added to
distinguish.

**And the ~2 bits are identifiability, not calibration — my first reading of
this was wrong.** A `map` rule's confidence was made per **table entry** rather
than per rule (`frontier-perkey`), on the argument that the entry is the
sub-population. **It is not**: the six kind entries fire **589** times in
training and only **24.3%** of those are derived fills, so per-entry precision is
0.348 and its bound 0.29 — which is exactly the confidence measured. Bits went
2.363 → **2.472**, marginally worse.

Three candidate separators, all measured, none works: the **rule** (0.66, its
precision where it fires), the **guard** (best covering guard 0.531 pure), the
**entry** (0.243 derived). **Nothing the model has at prediction time identifies
a derived fill**, so 2.363 bits is *correct calibration under genuine
uncertainty*, not mass thrown away. Being right 87/87 there is a property of the
bucket rather than knowledge the model has about it — and the reading below,
that accuracy is the trustworthy column here, is the wrong way round: accuracy
scores the model only where its rule happens to be right.

**The gate cannot tell the arms apart.** On the fills where the label rule fires,
its argmax is right **87/87** in the treatment and **0.205** in the control, and
the gate it is given is **0.330** against **0.318**. `MassCalibrator` keys on the
rule's pooled score — the carrying rule is a 399-entry table scoring ~0.66 over
the whole curriculum while being right 1.000 on this sub-population — so **an
average cannot see a sub-population**, for the third time in one day and now on
the gate. Roughly **1.6–2.3 bits are recoverable here by calibration alone**,
with no change to what the model believes.

**And it is not about table size.** The pair-count curve, each rung against its
own control and its own blind marginal — `-kN` widens the *pool* the episode's
six kinds are drawn from, the per-episode map stays six wide, the correspondence
stays fixed corpus-wide:

| k | instances per pair | treatment | control | blind | **lift** |
|---:|---:|---:|---:|---:|---:|
| 6 | ~30 | 0.989 | 0.143 | 0.167 | **0.846** |
| 12 | ~15 | **1.000** | 0.092 | 0.115 | **0.908** |
| 24 | ~7.7 | 0.896 | 0.072 | 0.039 | **0.824** |
| 60 | ~3 | 0.641 | 0.027 | 0.016 | **0.614** |

The derivation floor is 1.000 at every rung, so the ceiling does not move. **At
k=60 the model holds sixty corpus-wide pairs, each seen about three times in
training, and answers 64% of the bucket against a 1.6% blind marginal** — forty
times chance. Six pairs was not doing the work. Two of the four pre-registered
predictions were *too pessimistic*: k=24 was called at 0.4–0.8 and came in at
0.896, and k=60 was predicted to collapse to chance and did not. The cross-fit is
per key rather than per rule, so a table's rare keys degrade individually instead
of sinking the rule that owns them.

**It is two variables, and the one-variable version was mine and is refuted.**
Raising `n_train` recovers the wide pools: k60 goes 0.641 → **0.910** at 40 seeds
and **0.962** at 80, so the model is not capped near twenty-four pairs and the
headline does not need hedging to "a six-pair correspondence". But holding
instances-per-pair fixed at ~7.7 and varying only the pool gives **1.000 / 0.956
/ 0.896** for pools 6 / 12 / 24 — monotone in width at identical supervision. I
published "instances-per-pair predicts the score and pool width does not" from
three consistent points; the fourth, chosen because it was the one that could
embarrass the claim, killed it. Pool width costs 0.104 at thin supervision and
0.006 at thick. A mechanism is available and untested: at pool 6 every episode
draws all six kinds, so the map is *complete in every episode*, and completeness
rather than width may be the operative variable.

**And I broke the type head for eight variants without noticing.** Every knob
after `frontier-001` was tuned on `label_acc` and `_induce` reads its knobs off
the *model* rather than the *head*, so each went to the type head too — a column
that was not in the table I was reading. `type_acc` went 0.8633 → 0.8607 →
0.8491 → 0.8539, turning a **+0.023 lift into −0.045**, below a floor only two of
nineteen models had ever cleared. `frontier-009` induces the type head under its
own settings: label numbers identical to `frontier-008` (0.4414, 7.141) and
**type lift +0.036**, better than `frontier-001`'s. See
`notes/lessons/2026-08-17-a-default-computed-in-init-captures-the-base-classs-values.md`,
which also records the worse bug the fix introduced for ten minutes — a default
computed in the base `__init__` captured the base values, silently moving
`frontier-008`'s published `type_acc` with nothing in its own definition changed.

**Named weakness:** `min_precision = 0.2` was chosen after seeing that 0.5
excluded the rule. It was not searched over the derived bucket and no value was
selected by that number, but it was *informed* by it, which is weaker than a
value settled on the development split. The clean version is a per-guard floor
and is not built.

## The derivability channel is taken, and it costs the vocabulary

**Status: provisional, 2026-08-16 — measured, controlled, mechanism traced, and
not yet challenged by anyone who did not write it.** The section below it says
nothing takes the channel; that was true of twenty models and is no longer true.
Both sections stand: the old one is still the correct reading of those twenty.

`frontier-001` adopts the loop from *Hypothesis Frontier* (arXiv:2608.10843,
Batzoglou, 2026-08-11) — propose formulas, score them with an **exact
verifier**, aim the next round at the residual errors, prefer the shortest
formula of a given verified precision. The LLM is replaced by enumeration over a
guard lattice, so the verifier is the only thing deciding what survives.

**The one change that matters is a hypothesis *form*, not a search.** Every
rule-based model here concludes a **copy** (some node's label) or a **constant**.
`ilp-001` is a genuine FOIL search and induces the relational chain, but its
clause head still binds to another node's label. The derive arm plants
`label(X) = m(label(Y))` for a finite corpus-wide `m`, which is neither — so no
amount of search finds it, and `ilp` scoring exactly 0.000 beside a search that
works is the evidence that the failure was **expressive, not procedural**.

`acc | derived, not copyable`, 1,325 fills, 704 eval episodes, 8 draws:

| | `derive:wordnet` | control `-perm` | `-shuffled` |
|---|---:|---:|---:|
| **`frontier-001`** | **0.532** | **0.072** | **0.532** |
| `frontier-nomap` — same search, no map form | 0.000 | 0.000 | — |
| four models scoring the shared back-off | 0.155 | 0.178 | 0.155 |
| the other fifteen | 0.000 | 0.000 | 0.000 |
| derivation floor (a lookup) | 1.000 | 0.167 | 1.000 |

`treatment − control` is **+0.460**; every other model in the table is at or
below zero on that difference. **The rule was read, not inferred:** the
hypothesis answering the bucket is `[slot=1, nsib=4] -> map:sib@2`, and its
entries at the six planted kinds are `shoe→lace, body→abdomen, ship→bay,
garment→arm, building→annex, auto→buffer` — **all six recovered verbatim**.
Where it fires it is right **61 of 61**; the 45% it does not cover, it declines.
In the control that rule fails verification and **is absent from the fitted
model**. In `-shuffled` the same guard survives with the same support and table
size, its six entries are the scrambled graph's values, and they agree with real
WordNet **zero** times out of six — which shows, rather than asserts, that this
instrument reads *derivability* and never *meaning*.

**The price is measured, by a control in the model's own hypothesis class.**
`frontier-nomap` is the identical search with the `map` form removed:

| | `frontier-001` | `frontier-nomap` |
|---|---:|---:|
| `label_acc`, base curriculum | **0.4042** — first of 24 | 0.2954 |
| `label_bits` | 7.433 — **eleventh** of 24 | 8.541 |
| renaming drop | **−0.372** | **−0.066** |
| `type_acc` | 0.863335 | 0.863335 |

So the map form buys **+0.109 accuracy and 1.11 bits and costs 0.306 of
equivariance** — and the derived slot is 0.20% of positions, so almost all of
that cost is the map firing where no derivation was required. 356 of 444 label
rules are symbol-keyed maps: offered a table over symbol identities and a
structural copy, a cross-fitted verifier prefers the table nearly everywhere,
because on this curriculum it verifies better.

**Read the two rankings together, because they disagree by ten places.**
`frontier-001` is first of twenty-four on `label_acc` — +0.047 over the previous
best, a quarter of the whole field's spread — and eleventh on `label_bits`, and
it is the second least equivariant model ever measured here, behind
`ensemble-001`. It votes for one symbol, so being unsure and being wrong are the
same observation to it, which accuracy cannot see and bits is made of.

**What a refuter should attack first.** On the *copyable* half of the derived
bucket `frontier-001` goes 0.496 → 0.078 between the arms, where every pointer
holds its score (`corefer` 0.410 → 0.399). The pre-registration said that half
could not separate the arms; it separates by 0.418. The model replaces an
available copy with a derivation whenever the derivation verifies better in
training, which is rational under that distribution and brittle under the one
condition designed to break it.

## Derivability: a channel 0.833 wide, provably open, and nothing takes it

The semantic-constraint line's second attempt, and the one whose control can
fail. The first arm re-*labelled* the curriculum from a knowledge graph and
returned mean −0.0013 with a degree-preserving scramble as its control — an
isomorphism, so a corpus-only learner sees the same problem and the control could
not lose. This arm changes what is **derivable** instead of what things are
called.

**Treatment** `derive:wordnet` — the attribute slot is *not drawn*. It follows
from the object's kind through a six-pair map fixed corpus-wide, read off
WordNet's `part` relation: `ship→bay, building→annex, garment→arm, auto→buffer,
body→abdomen, shoe→lace`. Six pairs rather than thousands, deliberately: drawing
kinds from ~13,810 graph words would have been a second null-by-construction, by
sparsity.

**Control** `derive:wordnet-perm` — the same six kinds and six values and the
same bijection, composed with a **fresh uniform permutation per episode**. A
bijection composed with a permutation is a bijection, so collision structure,
copyable share and tree shapes are identical by construction. The one thing
removed is *cross-episode co-occurrence of two symbols in one term* — the only
channel the treatment has.

**The control provably can fail, and this is shown without any model.** A
*derivation floor* — a one-symbol lookup weaker than anything in the sweep — over
1,345 derived fills:

| | treatment | control | shuffled |
|---|---:|---:|---:|
| derivation floor, not copyable | **1.000** | **0.167** | 1.000 |
| the same lookup, sibling-blind | 0.167 | 0.143 | 0.167 |

**The channel is 0.833 wide and the control closes it.** That is the thing the
previous arm never had.

**Twenty models. Nothing takes it.** `acc | derived, not copyable`, n = 633:

| | derive | perm |
|---|---:|---:|
| `brill` / `ctw` / `grammar` / `ngram` | 0.155 | 0.178 |
| `symbolalg-001` | 0.145 | 0.156 |
| **the other fifteen** | **0.000** | 0.000 |
| mean | **0.038** | 0.043 |

**Fifteen of twenty score exactly zero**, and the five that score anything sit
*below their own arm's blind marginal of 0.167* — they are reproducing the value
frequency, not deriving. The mean moves −0.005, **against** the treatment. On the
*copyable* half of the same bucket those models reach 0.211 (`corefer` 0.410,
`ensemble` 0.395, `ptrgen` 0.329) and score the same in the control: their route
is coreference and only coreference.

`derive − shuffled` is **exactly 0.000 on 20 of 20 models** — the isomorphism
prediction, written down before the run and then measured.

**Coverage caps what this could ever have shown, and it was measured first.**
The binder derives a value for 728 of 728 scene objects it is offered, but that
is **175 graph positions — 0.205% of nodes, in 11 of 179 lessons**. Stated before
running: pooled `label_acc` cannot move by more than ~0.003 even if the derived
bucket went to 1.00, so **a flat pooled table here is arithmetic, not evidence**,
and the honest measurement is the conditional one above. Raising that ceiling is
a curriculum change, not a graph change.

**What this does and does not say.** It does not say semantics is worthless:
`derive` and `derive-shuffled` are indistinguishable, so this instrument reads
*derivability* and never *meaning*. What it says is that when a symbol is made
derivable — provably, with an 0.833-wide channel a one-symbol lookup walks
straight through — **not one of twenty models takes any of it.** Together with
`label_acc` being 72% a copy score and a pointer scoring 0.000 on the
non-copyable quarter even with an oracle, the picture is consistent: these models
corefer, and they have no mechanism that derives.

## Read this before any number below it: `label_acc` is 72% a copy score

**Status: challenged and survived, 2026-08-15 — with one of its three readings
refuted and corrected in place below.** An agent that did not write it re-ran the
whole arm from scratch (the published weights are untracked) and reproduced all
twelve summaries **bit-identically** in `final`, `floors` and `renaming`. It is a
*decomposition*
of the published numbers rather than a new measurement — `0.72 x copyable +
0.28 x not` reproduces every row in this file **including the floor**, verified
independently (corefer 0.3565 vs 0.357, grammar 0.1874 vs 0.187, floor 0.1434 vs
0.143). What could still make it true-but-trivial is named at the end.

`label_acc` has been this repo's central number from the beginning. It mixes two
questions in a 72:28 ratio and nothing ever reported them apart: **does some
visible node of the same graph already carry the answer's label?**
`runs/infill-node-r015`, all 179 lessons, 5,233 fills, the published
`mask_rate=0.15` setting on the run's own draw.

| model | acc \| copyable | acc \| **not** | acc (all) | renaming drop |
|---|---:|---:|---:|---:|
| `corefer-001` | 0.494 | **0.003** | 0.357 | 0.003 |
| `omegaclaw_rank-001` | 0.469 | 0.063 | 0.356 | 0.017 |
| `ptrgen-001` | 0.462 | 0.010 | 0.336 | 0.005 |
| `routes-001` | 0.448 | **0.000** | 0.323 | −0.000 |
| `vsa_perm-002` | 0.435 | 0.043 | 0.326 | 0.010 |
| `brill-001` | 0.350 | 0.137 | 0.290 | 0.130 |
| `grammar-001` | 0.191 | **0.178** | 0.187 | 0.159 |
| `ngram-001` | 0.175 | 0.154 | 0.170 | 0.143 |
| **floor** (content-blind lookup) | *0.158* | *0.106* | *0.143* | — |

**Correction, within the day, by the refuter: the "below the floor" reading is
wrong and I published it here before it was checked.** It is true that every
renaming-invariant model scores 0.000–0.081 on the non-copyable quarter against a
0.106 lookup floor. It is not a valid comparison. **That floor is a memorising
lookup, and the bucket boundary is exactly the line a renaming-invariant model
cannot cross by construction** — naming a symbol no visible node carries requires
remembering the vocabulary, which is the one thing these models are built not to
do.

Read against a **renaming-invariant pointer floor**, which is in the same
hypothesis class, the sign changes:

| floor | copyable | not copyable | pooled |
|---|---:|---:|---:|
| lookup (`split_floor`) — memorises | 0.1581 | **0.1058** | 0.1432 |
| pointer (`split_copy_floor`) — equivariant | 0.3345 | **0.0000** | 0.2394 |
| **oracle** pointer | 1.0000 | **0.0000** | 0.7216 |

A pointer scores **exactly zero** on the non-copyable bucket *even with an
oracle*, because there is nothing to point at. So `corefer-001`'s 0.0034 there is
not "below a floor" — it is marginally above the only floor its own hypothesis
class admits, and the ceiling for any pointer on that quarter is zero. Against
the pointer floor on the copyable bucket it is **+0.159**, genuinely above.

The finding that survives is therefore sharper and less damning: **these models
are pointers, and a pointer cannot generate a symbol that is not already
present.** That is a statement about the hypothesis class, not a failure to reach
a baseline. The lesson is
`notes/lessons/2026-08-15-a-floor-outside-the-models-hypothesis-class.md`.

**The published ranking inverts on the sub-population.** `corefer-001` is first
of twelve pooled and **eleventh** where nothing can be copied; `grammar-001` is
eighth and **first**. A ranking is a property of its metric — and now also of its
sub-population, and this repo has only ever published the pooled one.

**Crossed with the renaming test at last, and the non-copyable gain is entirely
vocabulary.** The two instruments had always been run apart — renaming pooled,
the copyable split on original episodes only — so `frontier`'s 0.325 on the
non-copyable bucket had never been challenged directly:

| model | `acc\|cp` | `acc\|not` | renamed `acc\|cp` | renamed `acc\|not` |
|---|---:|---:|---:|---:|
| `frontier-floortype` | 0.495 | **0.325** | **0.055** | **0.003** |
| `frontier-typepoint` | 0.490 | 0.314 | **0.306** | **0.003** |
| `frontier-nomap` | 0.381 | 0.073 | 0.317 | 0.000 |
| `corefer-001` | 0.494 | 0.003 | 0.492 | 0.000 |
| floor | 0.158 | 0.106 | **0.002** | **0.003** |

Every model lands at 0.000–0.003 on the renamed non-copyable bucket, which is the
renamed floor; the floor itself goes 0.1432 → 0.0022 pooled. The theorem stated
above is now measured rather than argued.

**And the equivariance difference between the `frontier` variants is entirely in
the *copyable* bucket**, which was not predicted. The two differ only in
`keep_by_path`/`keep_per_guard`; their renamed non-copyable halves are identical
at 0.003 and the whole 0.174 gap is renamed `acc | copyable`, 0.055 against
0.306. So keeping more than one rule per guard buys no reasoning that survives
renaming — it buys back the model's ability to **point**, which the map head
otherwise crowds out. Not "equivariance for accuracy" but *how much of the copy
head survives having a map head bolted on*.

**And frontier's pointing has a hard ceiling that `corefer` is already past.** On
renamed episodes, the answer is reachable by **any** of frontier's ten fixed
paths on only **0.4124** of copyable fills. `frontier-typepoint` gets 0.3060 —
**74% of its own ceiling** — and `corefer` gets **0.4920**, *above* it. So the
0.186 gap is not search: better selection over the same paths can buy at most
0.106, and the rest needs paths frontier does not have. Four sibling slots and
`prev` do essentially all the work (0.21–0.29 each, heavily overlapping);
`gparent` and the three `psib@k` reach almost nothing.

**And adding the pointer inverts the diagnosis.** `frontier-point` adds it as an
eleventh *path* — so guards, cross-fit, ranking and gate all apply unchanged, and
`copy:point` is "copy whatever the pointer chose". It is `corefer`'s stage one
with neither its prose feature nor its reranker. All four predictions held:

| | fixed paths | with the pointer |
|---|---:|---:|
| reachable ceiling, renamed copyable | 0.4124 | **0.5200** |
| renamed `acc \| copyable` | 0.306 | **0.340** |
| `label_acc` | 0.4414 | **0.4460** |
| `type_lift` | +0.062 | **+0.112** |

**The ceiling is now 0.5200 and `corefer` scores 0.4920**, so for the first time
frontier's language can express what `corefer` achieves and **the remaining gap
is selection, not representation** — the opposite of every previous round's
conclusion. Efficiency fell 74% → 65% of ceiling, which is the honest cost:
widening the language left headroom the search is not taking.

Two things fell out. The pointer's own top-1 is right on **0.4449** of copyable
fills, against the **44%** `corefer-001`'s docstring records for its stage one —
two separately written naive-Bayes pointers over the same three feature families
agreeing to a fifth of a percent. And the *type* head improved without being
aimed at, +0.062 → +0.112, because the pointer extends the type paths too and the
pointed-at type is the whole of `corefer`'s type advantage.

**And the selection loss was committing to a path.** Decomposing
`frontier-point` on the 1,985 renamed copyable fills *where the answer is
reachable*: right 0.6463, **fired on a path without the answer 0.2902**, resolver
wrong 0.0635, **no rule fired 0.0000**. It never abstains and the resolver is
almost never the problem — the loss is first-match-wins committing to one path
when another matching rule reads the one that holds the answer. A vote does not
commit, and `frontier-pointsoft` moves +0.044 into "right" and −0.049 out of
"committed wrong", with the third category unmoved:

| | acc | **bits** | type | renamed | ren `acc\|cp` |
|---|---:|---:|---:|---:|---:|
| `frontier-point` | 0.4460 | 7.092 | 0.876 | 0.248 | 0.340 |
| **`frontier-pointsoft`** | 0.4372 | **6.457** | 0.876 | **0.267** | **0.371** |
| `corefer-001` | 0.3572 | 6.955 | 0.946 | 0.350 | 0.492 |

**6.457 is 7th of 46 on `label_bits`, and every model above it scores 0.169–0.319
on accuracy where this scores 0.437** — the first row here that is strong on both
columns at once. That was *not* what the experiment was for: it was aimed at
renamed copyable accuracy, predicted +0.03, and got it; the 0.635 bits came
along.

The remaining loss is now **weighting**: on 24.1% of reachable fills the truth is
in the vote set and is outvoted.

**And the knob for that was already measured, as "flat".** `vote_sharpness` was
swept once on `frontier-soft` and recorded as inert: bits spanning 6.959–6.984
over a sixteen-fold range. It *is* still inert on bits with the pointer
underneath (6.392–6.448) — but the **renamed** column, which that sweep did not
rank by, spans **0.049** where on `frontier-soft` it spanned **0.0008**, sixty
times less. The knob did not change; the vote set did. `frontier-soft`'s median
top-share is 1.0000 and it fires on 2,287 of 3,497 fills; `frontier-pointsoft`'s
is 0.7894 and it fires on all 3,497 — there is disagreement to reweight for the
first time, and it is specifically between renaming-invariant `copy` votes and
memorising `map` ones.

`frontier-pointflat` (sharpness 0.5, settled on the development split, three
numbers pre-registered and all held on eval: renamed 0.318 vs ≈0.30, acc 0.411 vs
≈0.41, bits 6.500 vs ≈6.45):

| model | acc | bits | renamed | **ren `acc\|cp`** | % of 0.520 ceiling |
|---|---:|---:|---:|---:|---:|
| `frontier-typepoint` | 0.4414 | 7.141 | 0.221 | 0.306 | 59% |
| `frontier-point` | 0.4460 | 7.092 | 0.248 | 0.340 | 65% |
| `frontier-pointsoft` | 0.4372 | 6.457 | 0.267 | 0.371 | 71% |
| **`frontier-pointflat`** | 0.4110 | 6.500 | **0.318** | **0.434** | **83%** |
| `corefer-001` | 0.3572 | 6.955 | 0.350 | 0.492 | 95% |

65% → 83% of ceiling in two changes, neither touching what the model can
*represent*; the gap to `corefer` is 0.058, from 0.186 when the pointer was
added. It is not free — accuracy falls 0.026 and bits rise 0.043 — so this is the
accuracy/equivariance trade again, now steerable by a continuous knob instead of
by adding or removing a rule form.

A knob inert in one column and a strong lever in another is
*a-ranking-is-a-property-of-a-metric* applied to a **parameter** rather than to a
model ranking. The old reading was not wrong; it was complete only for the column
it reported and was written as though it were general.

**The mechanism behind it holds, and the prediction from the mechanism does
not.** The story was that flattening helps by demoting `map`, the memorising form
whose table is stale under a renaming. `map_vote_weight` (a multiplier on `map`'s
vote mass; 1.0 inert) confirms it — 0.25 moves renamed 0.2601 → 0.2976, +0.0375
of the 0.049, from a knob that touches nothing else. But the prediction was that
it would buy that **more cheaply**, and matched on renamed the two knobs are one
curve: 0.2754 costs acc 0.4286 via sharpness and 0.4288 via `map` weight, and at
~0.297 demoting `map` is 0.006 *worse*. Equivariance is bought with accuracy at a
fixed exchange rate and it does not matter which of two structurally unrelated
levers you pull. A mechanism can be the right account of *what* a knob does and
say nothing about *how efficiently* it does it: the frontier belongs to the
hypothesis mixture, not to the knob.

Two nulls fell out, both useful. Pushing sharpness below 0.5 **saturates** —
0.25/0.125/0.0 give renamed 0.3055/0.3055/0.3070 for 0.016 more accuracy, so
`frontier-pointflat` already holds 99.3% of what a uniform vote would, and the
knob is closed rather than licensing another descendant. And `map_vote_weight=0`
ranks **7th of 16 on the equivariant objective while being the worst row present
on bits (8.431 against ~6.4)**: silencing `map` makes nodes abstain to the
structural prior, so the renaming drop collapses to 0.0168 because there is
barely a prediction left to lose. Rank on one number and that gets promoted.

**"A fixed exchange rate" was wrong, and the check that killed it also settled
whether the arc was pushing a constraint or sliding along one.** Taking all 44
models with both columns as points in (`label_acc`, `renamed_label_acc`), the
Pareto front is five models. Of 17 families, **15 sit strictly under it** — so
the trade is a **model property, not a task constraint**, and the pointer arc was
pushing. But the rate along the front is not fixed at all:

| step | Δrenamed | Δacc | rate |
|---|---:|---:|---:|
| `frontier-floortype` → `frontier-point` | +0.2007 | −0.0015 | **0.007** |
| → `frontier-pointsoft` | +0.0196 | −0.0090 | 0.459 |
| → `frontier-pointflat` | +0.0511 | −0.0262 | 0.513 |
| → `corefer-mass` | +0.0324 | −0.0535 | **1.651** |

**235x**, and the trade is convex: the first 0.20 of equivariance is free and
only the last stretch is expensive. That is the same error as calling the
sharpness curve "flat" — reporting the shape of a curve from the segment I
happened to sample — made twice in one day. It also reframes the 0.058 gap to
`corefer` I had been treating as the target: it is the most expensive region of
the entire front, and closing it by tuning is the worst available use of effort.

Four of the five front models are this week's chain, in order, so every step was
a real Pareto improvement. **The caveat matters more than the result**: effort
predicts front membership almost perfectly. `frontier` (n=20) and `corefer`
(n=3) hold the whole front while eleven of the fifteen families under it have
exactly **one** registered model. That is evidence twenty attempts beat one, not
that the architecture is better. `omegaclaw_rank-001` is **0.0015** under the
front from three variants and is now the strongest untouched lead in the repo.

That is the **third** head to return the same diagnosis. The label head's
derivability null was expressive, not procedural; the type head needed a pointer
rather than a fourth column; and the copy head reaches 74% of what its paths
allow while the paths allow 41% of what a pointer would. **The hypothesis
language is the constraint, and twice over the missing piece is specifically the
ability to point at an arbitrary node** — which is what `corefer` is and nothing
else.

**The plain reading: these models do coreference. Where there is no coreferent to
find, they are worse than a table.** "The best model reaches 0.357" should be
read as "reaches 0.494 at finding a symbol already on screen, and 0.003 at
producing one that is not."

**The same fact, arrived at independently and from the other side.** Hiding every
node that carries the episode's *answer* — 0% copyable by construction — gives
`corefer-001` **0.001** against a 0.101 floor, and nine of twelve models land on
the abstention row, four of them matching "say nothing" to nine decimal places.
See the generation section below.

**What would make this true but uninteresting**, and it is being checked now: if
the non-copyable fills are mostly the invented nonce symbols the vocabulary
cannot name, then "everything scores zero" is a fact about coverage rather than
about reasoning, and the floor's 0.106 becomes the thing needing explanation.
Pooled `label_coverage` is 0.82; per-bucket coverage had not been measured when
this was written.

## What is established

**Every ranking this repo has published is an accuracy ranking, and the models
rank close to inversely by bits.** `label_bits` has been in every
`summary.json` from the beginning and was never given a lift, so it was never
compared. On the full curriculum:

| model | lbl acc | rank | lbl bits | rank |
|---|---:|---:|---:|---:|
| `grammar` | 0.187 | 14 | **6.09** | **1** |
| `evidence` | 0.219 | 12 | 6.26 | 3 |
| `ngram` | 0.170 | 17 | 6.41 | 4 |
| `corefer` | **0.357** | **1** | 6.95 | 6 |
| `omegaclaw_rank` | 0.356 | 2 | 8.09 | 11 |
| `brill` | 0.244 | 10 | 9.08 | 19 |

The cause is the shared mixture, `(1-c)*backoff + c*votes`. A model that knows
the answer is one of ten and no more has argmax accuracy 0.1, and `c` was fitted
as an argmax accuracy, so it kept 0.1 of the mass and gave 0.9 back to a unigram.
Deciding well and estimating well were made to pull against each other by the
interface, not by the reasoning. **A ranking is a property of a metric and never
of a set of models**; both columns are now printed by `compare`.

**Fitting the mixture weight as a mixture weight is worth +0.017 lift and 0.58
bits.** `ptrgen-001` and `ptrgen-argmax` are the same pointer, the same
features, the same decision procedure, differing in one method: whether the gate
is fitted by maximising held-out likelihood or by measuring argmax accuracy.

| | lbl acc | lbl lift | bits |
|---|---:|---:|---:|
| `ptrgen-001` (likelihood) | 0.336 | +0.225 | **5.91** |
| `ptrgen-argmax` (accuracy) | 0.321 | +0.208 | 6.49 |

The accuracy gain was not predicted and has a mechanism: raising `c` cannot
reorder the votes, but it does move the boundary between a voted symbol and the
structural prior, and the votes win that comparison more often than they lost it.

**An ensemble pays in bits only when the members are actually diverse, and the
control proves it.** `ensemble-001` is `ptrgen` x `grammar`, chosen on the
renaming column — one loses 0.003 accuracy when every symbol is permuted, the
other 0.159. `ensemble-pointers` is `ptrgen` x `corefer`, two pointers over the
same features, registered as the control.

| | lbl acc | bits | bits vs best member |
|---|---:|---:|---:|
| `ptrgen-001` alone | 0.336 | 5.91 | — |
| `ensemble-001` (diverse) | 0.336 | **4.77** | **-1.14** |
| `ensemble-pointers` (correlated) | 0.340 | 5.91 | -0.00 |

4.77 bits is the best in the repo by a wide margin, and the correlated pair
gains *exactly nothing*. The fitted weight is 0.55 — an interior optimum, so
neither member is carrying it. `ROADMAP` rejected ensembling on a measured
ceiling for the **copy head** and that rejection stands; this is the label head,
and every ensemble previously considered was pointer-with-pointer, which the
control now shows is the case that does not work.

**And the entire 1.14-bit gain is vocabulary memorisation.** Run the renaming
test on it — permute all 340 symbols, do not refit — and it is the least
equivariant model ever measured here:

| model | plain | renamed | drop |
|---|---:|---:|---:|
| `ptrgen-001` | 0.390 | 0.392 | **-0.002** |
| `ensemble-pointers` | 0.392 | 0.396 | **-0.004** |
| `omegaclaw_em-001` | 0.450 | 0.423 | +0.027 |
| `grammar-001` | 0.290 | 0.008 | +0.282 |
| `ensemble-001` | 0.467 | **0.038** | **+0.429** |

So the finding stands and its sign is the opposite of what it looked like.
Diversity *is* what an ensemble buys, and the diversity available here is
"one member reads structure and the other memorises the corpus" — which is why
the correlated control gains nothing and why the gain does not survive a
renaming. `ensemble-001` is the best density estimator in the repo and it is not
a symbolic model; `ensemble-pointers` keeps the equivariance and buys nothing.

The honest summary is that **on this task, bits and equivariance are in
tension**, not that an ensemble helps. Which makes the next line the important
one:

**A symbolic model can still win on bits — `ptrgen` already does.** At 5.91 it
beats `grammar`'s 6.09, the previous best, while dropping 0.002 under renaming
against `grammar`'s 0.282. The 1.14 bits on top of that are memorisation and the
0.18 below it are not. Those are different quantities and only the second is
what this repo is trying to measure.

**The label task is a binding problem being scored as classification.** 71.9% of
scored answers already sit on a *visible* node of the same episode, so the real
question is "which node do I corefer with", not "which of 8,192 symbols is this".
The best model reaches 0.357 accuracy against a **0.722 copy ceiling**. More than
half the reachable signal is untouched by every model here.

**`type_bits` had never been compared, and it inverts the type ranking.** The
same sentence that produced `a-ranking-is-a-property-of-a-metric` for the label
head is true of the type head: both columns have been in every `summary.json`
from the start and only accuracy was ever quoted. Ranked over 44 rows,
`gru-001` is **31st on type accuracy and 4th on type bits**, `tpr` 33rd and 6th,
`transformer` 35th and 10th — the neural models are calibrated and inaccurate.
The rule-based lines are the mirror: `frontier-010` is **7th on accuracy and
24th on bits**, accurate and overconfident. Only `corefer-001` (0.9458 / 0.3479)
and `rgt-001` (0.9154 / 0.3576) are top on both, and they are exactly the two
models recorded below as the only ones with a positive type lift.

Every type gate here is a hand formula. Fitting frontier's by likelihood
(`frontier-typemass`) buys **0.110 bits**, 1.0441 → 0.9342, moving it 24th → 14th
with `type_acc` unchanged and every label number bit-identical. `corefer` is at
0.3479, so calibration closed a tenth of a bit and **the remaining 0.59 is a
different order of thing** — a question about the type head's hypothesis
language, not its confidence.

**Node type is very nearly determined by tree shape.** A content-blind
backed-off lookup reaches 0.860. That is the floor now, and on it only two of
nineteen models are positive: `corefer` (+0.612) and `rgt` (+0.395, a network).
Every other model that looked good at type was reproducing a lookup table.

**And `corefer`'s +0.612 is one conjunct.** Its type key is a backed-off ladder
over `(ptype, slot, depth, arity, sibling type, pointed type)`, and the floor is
a lookup of exactly that shape minus the last term. `corefer-nopoint` drops it
and changes nothing else:

| | type acc | type bits | type lift | label acc / bits |
|---|---:|---:|---:|---|
| `corefer-001` | 0.9458 | **0.3479** | **+0.612** | 0.357157 / 6.9547 |
| `corefer-nopoint` | **0.8514** | 0.8300 | **−0.065** | 0.357157 / 6.9547 |

Minus that one term it is *below* the floor, and every label number is
bit-identical — the label pointer never reads it. So one of this repo's two
positive type results is the single feature **"what kind of node did my
coreference pointer land on"**, and the induced type heads need a *pointer*, not
a better rule language: every other atom in that ladder is already among
`frontier-010`'s eight. Priced here at **+0.095 accuracy and 0.48 bits**. Stated
against overclaiming: that term is the output of a fitted pointer, so it is where
the *pointer's* value is cashed for the type head rather than a cheap feature.

**And the conjunct does not transfer.** `frontier-typepoint` adds the ninth atom
to a model that already has the other eight — the type of whatever visible node
carries the symbol its own *label* head predicts, a **derived** pointer worth
0.4936 alone against `corefer`'s fitted one. `type_acc` moves **0.8666 →
0.8686**, +0.002 where `corefer` gets +0.095, with every label number
bit-identical. So the value is in the **pointer**, and the conjunct is only where
it enters: *the type head's ceiling is set by the quality of the pointer behind
its pointed-type term*. Four variants have now given `frontier`'s type head its
own knobs, atoms, gate and a pointer conjunct, moving it 0.8633 → 0.8686 and
1.0316 → 0.9070 — it needs a coreference model, not another column, and building
one inside it would be building `corefer` inside it.

A second, separable observation: `corefer-nopoint` is *less accurate* than
`frontier-typemass` (0.8514 vs 0.8666) and *better calibrated* (0.830 vs 0.934).
A back-off ladder and a rank-ordered rule list at comparable accuracy do not give
comparable bits — the ladder retreats to a general key with honest support, the
rule list fires its top match and lives with that rule's average.

**Capacity spent on symbol identity is wasted.** `ilp` reaches +0.198 label lift
with 74 counts; `ctw` reaches -0.040 with 819,990. The task re-randomises which
symbol fills which slot every episode, so parameters attached to symbol identity
have to be unlearned at test time.

**Renaming separates models the score cannot.** Permute all 2,105 symbols,
without refitting. Every rule-based model, sorted by what it loses:

| equivariant (≤0.03) | mostly structural | vocabulary-dependent |
|---|---|---|
| `routes` -0.000 | `syllogism` -0.024 | `symbolalg` -0.041 |
| `corefer` -0.003 | `ruleinduce` -0.027 | `ctw` -0.088 |
| `evidence` -0.003 | `omegaclaw_flat` -0.030 | `brill` **-0.130** |
| `omegaclaw_rank` -0.017 | | `workspace` **-0.130** |
| `omegaclaw_ctx` -0.018 | | `ngram` **-0.143** |
| `analogy` -0.019 | | `grammar` **-0.159** |
| `ilp` -0.021 | | |

Thirteen of sixteen lose under 0.05 — the symbolic models really are mostly
reading structure, which is the thesis of the repo and had never been measured
across the board. The exceptions are informative: `grammar` and `ngram` are
vocabulary methods by construction and behave that way, while `brill` and
`workspace` were not expected to and do.

`corefer` and `workspace` tie at 0.357 label accuracy and sit at -0.003 and
-0.130. The score cannot tell them apart; this can.

## Nulls and near-nulls worth not repeating

All four were built expecting a win, all four were pre-registered with what
would refute them, and all four came back small. Same sweep, same floors,
`runs/ptrgen`.

**Joint decoding helps the model that gains candidates, not the model that
gains reach — the opposite of the prediction.** Masked nodes are hidden 15% at a
time, so a claw reaching for a coreferent node lands on `None` whenever the
harness hid the evidence and the question together. Filling the surest nodes
first and re-reading the graph fixes that, and was predicted to help
`omegaclaw_ctx` most because its claws name specific structural positions.

| | lbl lift | bits | typ lift |
|---|---:|---:|---:|
| `omegaclaw_ctx-001` | +0.234 | 7.87 | -0.071 |
| `omegaclaw_joint-001` | +0.233 | 7.89 | -0.091 |
| `ptrgen-001` | +0.225 | 5.91 | +0.565 |
| `ptrgen_joint-001` | +0.230 | 5.87 | **+0.681** |

`omegaclaw` does not move at all; `ptrgen` gains a little on labels and a lot on
type. The interpretation was fixed in advance — *if only one moves, the effect
is about reach rather than about decoding* — and it applies: a committed node is
one more candidate for a model that scores every visible node, and mostly
nothing for a claw that wanted one particular position. **Sequential decoding is
not what helped.** The teacher-forcing boundary is worth less on the prediction
side than the scope note implied.

**Widening the claw set with a route the search discovered makes accuracy
slightly worse.** `ilp` is the one model here whose hypothesis space is not a
list somebody wrote down, and it does use that freedom: 38% of its clause
firings land where no claw reaches, and it is right there 82% of the time. Its
strongest clause is a *typed, slot-selected sibling*, which `CLAWS` cannot
express — it has `sibling0` and `prev_sibling` and no way to say which sibling.
Added as `omegaclaw_reach-001`, `sibling_pred` fires at **0.803** reliability
against 0.232 for `mirror` and 0.163 for `peer`, the two the base class calls
the strongest operator every model here agrees on.

It still loses: +0.226 against `omegaclaw_ctx`'s +0.234, with bits slightly
better (7.72 against 7.87). The number that predicted this was already in the
diagnostic — `ilp` is uniquely right on only **2.2%** of nodes, because the claw
set reaches the same answer by another route nearly everywhere. **Reach was
never the constraint**, and the family's "control beats reach" claim comes out
of this stronger than it went in: the best single operator anyone has found here
does not pay for itself once eleven worse ones are already voting.

**EM credit assignment is worth +0.006 lift, and re-ranks the claws sharply.**
`omegaclaw_em-001` splits one unit of credit among the claws that were right
instead of giving each a whole hit — `peer` and `mirror` are two routes to the
same coreferent node and agree constantly, so counting records several
independent solutions to one problem. It reads +0.240 against `omegaclaw_ctx`'s
+0.234, second-best in the sweep: a real but small gain in score.

The *diagnostic* value is larger than the score change. Which claws keep their
reputation once the double count is removed, on all 179 lessons:

| claw | counted | EM | kept |
|---|---:|---:|---:|
| `prev_sibling` | 0.361 | **0.196** | 54% |
| `mirror` | 0.177 | 0.109 | 62% |
| `sibling0` | 0.255 | 0.107 | 42% |
| `slotmate` | 0.181 | 0.064 | 35% |
| `echo` | 0.200 | 0.043 | 21% |
| `prev` | **0.243** | 0.042 | 17% |
| `peer` | 0.100 | 0.026 | 26% |

The prediction written down before running it was that the vague aggregates —
`echo`, `slotmate`, `prev` — would lose most and the sharp structural claws
would keep theirs. That is what happened. `prev` falls from first to sixth: "the
nearest labelled node before this one" is right largely in the company of a claw
that had a reason, and hard counting cannot see it. `prev_sibling` and `mirror`
are what survive.

**A three-lesson slice said something else and it was wrong.** On that slice
`peer` collapsed from 0.141 to 0.005, which read as a clean discovery that
`peer` is subsumed by `mirror`. On 179 lessons `peer` keeps 26%, loses less than
`prev` or `echo`, and is not singled out. Fourth time a small slice has produced
a confident wrong answer here.

## The text surface, and a harness bug that made it unmeasurable

**Eleven of nineteen models cannot emit a single token of text.** `ptrgen`,
`corefer`, the whole `omegaclaw` family and both ensembles implement
`node_votes` and not `text_votes`, so they abstain to the unigram back-off and
all score identically: **8.51 bits/token, `answer_acc` 0.000**. The leaderboard
this repo optimises is masked-node only, and masked-node accuracy is disjoint
from generation. Of the models that *can* generate, only the counting ones are
any good — `ngram` 2.35 bits, `grammar` 2.43, `ctw` 4.30, against
`ruleinduce` 7.69 and `syllogism` 7.71, barely distinguishable from saying
nothing.

**The tokenizer was deleting underscores.** `_PIECE_RE` was an alternation of
four cases and `re.findall` drops whatever matches none of them; `_` matched
none. `'foo_bar_baz'` round-tripped to `'foobarbaz'`. On a twelve-lesson slice,
**9 of 85 answer strings and 17 of 60 episode texts did not survive a round
trip** — and a string the tokenizer cannot represent cannot be emitted by any
model, so those lessons' `exact_match` was pinned at zero for reasons unrelated
to any model. Both patterns are now total; after the fix, 0/85 and 0/60.

`test_encoding_is_lossless` existed, passed, and missed it: its fixture drew
episodes containing no underscore. **That is the six-lesson-slice error in a
different costume** — sampling the world rather than covering it — and it is now
the fifth time that shape of mistake has produced a confident wrong reading
here. The replacement tests assert on the alphabet, not on a fixture.

**Refuted: the degenerate generation is not a decoding-rule artefact.**
`symbolic-ai-old-A` found a 0.00 → 0.40 swing on a gridworld from sampling
instead of arg-max, with no parameter change, and this repo's
`'Reply with exactly one of: o1'` output has the same signature. It does not
replicate:

| | greedy | T=1.0 | T=0.7 top-50 |
|---|---:|---:|---:|
| `ngram` in-answer-set | 0.000 | 0.050 | 0.050 |
| `ctw` | 0.000 | 0.017 | 0.000 |
| `grammar` | 0.000 | 0.050 | 0.033 |

`exact_match` stays 0.000 everywhere. Sampling from a broad distribution is
worse to read than its mode, not better. The useful part was the greedy output
itself — gold `'opt_c'`, generated `'optd'`, the right shape with the underscore
missing — which is what led to the bug above.

## The transfer question, measured

Curriculum against real English prose, same protocol, `symbolic_ai_models/asymptotics.py`.
Every curve carries two nulls: a within-sequence shuffle (destroys order, keeps
the sequence's own subject matter) and a global resample (destroys both, leaving
the plug-in estimator's floor). `order = raw - within`, `latent = within - global`.

```
CURRICULUM  1,074 episodes, 183k tokens        REAL ENGLISH  572 chunks, 97k tokens
   d    I(d)  within  global   order  latent      d    I(d)  within  global   order  latent
   1   4.136   1.676   1.357   2.461   0.319      1   4.122   2.461   2.315   1.661   0.146
   8   3.003   1.692   1.382   1.311   0.310      8   2.642   2.497   2.346   0.145   0.151
  32   2.402   1.746   1.456   0.656   0.291     32   2.628   2.603   2.455   0.025   0.148
 128   2.418   1.876   1.926   0.542  -0.050    128   3.365   3.414   3.275  -0.048   0.139

effective rank 333.7 / 2,323 contexts (14%)    effective rank 773.1 / 1,809 contexts (43%)
top-50 singular values 37.7%                    top-50 singular values 26.0%
```

**Correction to a number published in this log's first draft.** "`I(d)` plateaus
at ~2.35 bits at d=128, a constant-latent signature" was measured from the raw
plug-in curve with no control. Most of that 2.35 is estimator bias: the global
null alone reads 1.36–1.93 over the same range. The real latent term is **0.31
bits**, not 2.35 — a seventh of what was claimed. The plateau is real; its
magnitude was almost entirely an artefact of an uncontrolled estimator.

**The finding that matters for the programme.** The two corpora differ most in
*order* structure, and in the direction that is bad for transfer:

| | curriculum | real English |
|---|---:|---:|
| order structure at d=8 | 1.31 bits | 0.15 |
| order structure at d=32 | 0.66 | 0.03 |
| order structure at d=128 | **0.54** | **-0.05** |

Real prose's positional dependence is **gone by d≈16**. The curriculum's is
still worth half a bit at d=128, because a lesson renders one rigid template —
fact, then pattern, then query over the same symbols — so the token 128 places
back is genuinely informative about this one. **That is a property of the
generator, not of language**, and any method that earns its score by exploiting
long-range positional regularity will look far better here than on prose.

**The low-effective-rank claim holds, and by a wide margin.** 14% of contexts
against 43% for prose, with the spectrum more concentrated (37.7% vs 26.0% in
the top 50). A minimal sufficient statistic for prediction really is small on
this curriculum, which is what makes an exact symbolic machine affordable — the
premise of agenda item (A) survives.

**Caveats, stated because the proxy is weak.** The "real English" corpus is 97k
tokens of this repository's own technical prose, not a language corpus: small,
one register, one author. Values below about 0.05 bits are inside the
estimator's resolution here. What it can support is the *contrast* in order
structure, which is an order of magnitude and survives any reasonable correction;
what it cannot support is a claim about natural language in general.

## Vector-symbolic models: good at bits, weak at deciding, exactly equivariant

`runs/vsa`, all 179 lessons, same config and floors as every other row. An
episode is encoded as `trace = sum_j role(j) * filler(j)` over bipolar
hypervectors and a masked node is answered by unbinding at its role and cleaning
up against the candidates. No learned layers — elementwise multiply, add and
sign over one 4096-vector.

| model | lbl acc | lbl lift | bits | bits lift | typ lift | copy lift | rename | secs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `vsa-002` | 0.219 | +0.089 | 6.80 | +0.275 | -0.486 | -0.115 | 0.029 | 37 |
| `vsa_seeded-002` | 0.212 | +0.081 | 6.76 | +0.278 | -0.486 | -0.122 | 0.035 | 37 |
| `vsa_pure-002` | 0.200 | +0.066 | 6.94 | +0.259 | -0.486 | -0.115 | **0.002** | 38 |
| `corefer-001` | **0.357** | +0.250 | 6.95 | +0.258 | +0.612 | +0.096 | 0.003 | 208 |
| `ptrgen_joint-001` | 0.340 | +0.230 | **5.87** | **+0.374** | +0.681 | +0.078 | 0.004 | 156 |

- **Weak at deciding, respectable at estimating.** +0.089 label lift puts it near
  the bottom; +0.275 bits lift puts it fourth of everything measured, ahead of
  `corefer` and every `omegaclaw`. That is the graded-by-construction claim
  doing what it said: cleanup returns a similarity to every candidate, so the
  output is a distribution rather than a winner with a confidence attached.
- **Exactly equivariant, at full scale.** `vsa_pure-002` drops **0.002** under a
  permutation of every symbol. The proof holds: the winning cleanup score
  reduces to `sum(role_i * role_j)` because `cb[s]**2 == 1`, so it cannot depend
  on which symbol won. No other model here is equivariant *by construction*
  rather than by measurement.
- **The seed is a null.** `vsa_seeded-002` is -0.007 accuracy, +0.003 bits lift,
  and +0.006 renaming drop against the random codebook. Consistent with the
  codebook test: sign-quantising a random projection of sparse co-occurrence
  only doubles the average off-diagonal similarity, so the seed is weak by
  construction. A real pretrained table drops into the same interface and is the
  experiment this null is asking for, not a refutation of seeding.
- **The copy head is below its floor** (-0.115). Reading the cleanup as a
  pointer is worse than copying from a fixed relative offset. Reported rather
  than dropped; it is the sharpest thing wrong with the model.
- **Cheap.** 37s against `corefer`'s 208s, at 8,254 parameters (one hypervector
  per symbol plus 62 role atoms).

**Correction, and it is the sixth of its kind here.** On a three-lesson slice,
turning off the shared `structural_fallback` took `vsa-002` from 0.305 to 0.102
— two thirds of its accuracy — and that was written into a commit message and a
docstring before the sweep ran. On 179 lessons it is 0.219 to 0.200: **9%, not
67%.** The slice overstated it sevenfold.

What survives the correction is still worth having: the fallback is a memorising
component every rule-based model inherits, and it is where this model's renaming
sensitivity lives (+0.029 with it, +0.002 without). Separating mechanism from
shared floor is a harness change worth making for the whole table — but the
claim that it dominates any model's score is not supported.

## Parsing text back into the graph: `symbolic_ai_parsers`

A second, separate package, because the parser layer in `symbolic_ai_models`
answers a different question. There a `Parser` is `text -> ParseResult` — word
classes, brackets, facts — scored by pairwise class agreement. Here a parser is
`str -> Graph` and has to produce the term the text was rendered from: nodes,
types, labels, parents. The old layer is not deleted and its four reasoners keep
using it; it is **superseded for this objective, not wrapped**, because a
`ParseResult` cannot be turned into a `Graph` without inventing the structure it
declined to commit to. One bridge is registered as a control (`legacy-001`,
lifting the old `regex` parser's `facts`), and it loses — see the table.

Numbers below are from `runs/parsers_full179.json`: all 179 generatable lessons,
16 training episodes each, 8 eval episodes each at seeds a million away, macro
averaged over lessons, four rendering languages. `symbolic-ai-parsers sweep` is
the authority.

### A tree alignment cannot be used to score attachment

Written first, and it read as a strong result. Comparing a predicted graph to
the true one needs an alignment, and the natural one is the top-down /
isolated-subtree mapping: roots align, and the children of two aligned nodes are
aligned to each other. That mapping only ever adds a pair once the pair's
parents are paired — so **every aligned node has a correct head by
construction**, and the UAS computed over it is identically 1 wherever it is
defined. It reported 0.95 for a parser that copies a remembered graph and does
no parsing at all. What it measures is how many nodes were *alignable*.

`uas` and `las` now use a content alignment — the k-th node carrying a label is
the k-th gold node carrying it, which is the exact analogue of dependency
parsing comparing two analyses token index by token index. The tree alignment is
kept for `type_acc`, where identifying a node by where it sits is what makes
agreeing about its type a real question. Both degeneracies are pinned by tests.

A smaller one, caught by a test rather than by reading: counting occurrences is
a statement about node numbering, so scoring canonicalises both graphs
breadth-first before anything else.

### A floor for every metric, fitted per metric

`bracket_f1` is PARSEVAL over `(type, label, leaf yield)` and `label_f1` is the
multiset of labels with structure ignored; the full set of ten is below. Five of
them never call an aligner, deliberately, so a result resting on the alignment
has a witness that does not. Each gets its own text-blind constant floor, fitted
by search over training graphs held out against each other — per metric, because
the constant maximising `label_f1` is not the one maximising `bracket_f1`.

The floor search itself was checked rather than trusted: quadrupling it to 200
candidates against 120 targets moves the floor by at most 0.013, so the lifts
above it are not an artefact of a thin search. The larger setting is the
default.

English, 179 lessons:

| parser | uas | las | type_acc | bracket_f1 | label_f1 | exact |
|---|---:|---:|---:|---:|---:|---:|
| **floor** (text-blind constant) | 0.075 | 0.051 | **0.548** | 0.004 | 0.123 | 0.000 |
| `prior-001` (one constant graph) | 0.028 | 0.020 | 0.502 | 0.004 | 0.033 | 0.000 |
| `legacy-001` (the old layer's facts) | 0.065 | 0.041 | **0.410** | 0.067 | 0.382 | 0.000 |
| `bracket-001` (layout, written down) | 0.145 | 0.084 | 0.644 | 0.020 | 0.455 | 0.000 |
| `retrieve-001` (memorise, no parsing) | 0.568 | 0.511 | 0.943 | 0.228 | 0.758 | 0.008 |
| `template-001` | 0.576 | 0.515 | 0.958 | 0.234 | **0.832** | **0.016** |
| `template-002` | 0.545 | 0.487 | 0.935 | 0.214 | 0.798 | 0.008 |
| `template-seeded` | 0.575 | 0.512 | 0.939 | **0.241** | 0.839 | 0.015 |

Three things to read off it, none of them the ranking:

- **`type_acc` has a floor of 0.548 and `bracket_f1` has one of 0.004.** They
  are not comparable numbers and a parser quoted on one of them without the
  other is being quoted selectively. `legacy-001` sits *below* the type floor
  (lift **-0.307**) while clearing the bracket floor (+0.063); `bracket-001` is
  the reverse shape. This is the same pattern the model half of the repo has —
  seven rule-based models below the type floor while clearing the label floor.
- **Exact graph recovery is essentially unachieved.** The best row is 0.016.
  Whatever these parsers are doing, it is not parsing in the sense of getting
  the answer right.
- **Memorisation gets most of it.** `retrieve-001` does no parsing whatsoever —
  nearest training prompt by word overlap, emit its graph — and reaches 0.758
  label F1. `template-001`'s refill step is worth **+0.074 label F1 and +0.008
  exact** over that, and nothing at all on `bracket_f1` (0.234 vs 0.228). On a
  templated corpus, recall is most of the score, and any parser number here that
  is not read against `retrieve-001` is unreadable.

### Ten metrics, because six were already disagreeing

`exact`, `uas`, `las`, `type_acc`, `bracket_f1`, `label_f1`, and then four
graph-level ones: `edge_f1` (Smatch's triple set, exact here because a label
plus a type names a node, so no hill climbing is needed), `path_f1` (root-to-node
lineages), `wl_f1` (Weisfeiler-Lehman subtree kernel, two rounds — the only
score here that is about neighbourhoods rather than trees, and the only one that
would survive these graphs ceasing to be trees), and `ted_sim` (an upper bound
on tree edit distance, from the constrained mapping). Five of the ten never call
the aligner.

They were added because the first six already ranked parsers differently and one
number was hiding it. On the full curriculum, `cky-001` against `bracket-001`:

| | uas | type_acc | bracket_f1 | edge_f1 | label_f1 |
|---|---:|---:|---:|---:|---:|
| `bracket-001` | 0.145 | **0.644** | 0.020 | 0.080 | 0.455 |
| `cky-001` | **0.299** | 0.594 | **0.168** | **0.261** | **0.527** |
| floor | 0.075 | 0.548 | 0.004 | 0.039 | 0.123 |

An induced grammar is worth **eight times** the layout baseline's bracket F1 and
loses to it on node type. Both are true, they are not reconcilable into one
ordering, and this is the ordinary case rather than a curiosity — a table with
one column would have reported whichever was written first.

### Classical parsers: a treebank the corpus does not have

The three parsers that *compose* an answer rather than retrieving one, which was
the standing open question in this file. They need spans, and the generator
records none — it hands over the term and the string and nothing about which
characters a subterm produced. `symbolic_ai_parsers/treebank.py` recovers them
from two facts about the curriculum: arguments are copied into the prose
verbatim in every language, and a predicate renders as one punctuation-delimited
clause. Nodes are assigned to clauses greedily by argument overlap.

**79% of clause-shaped graph nodes find a clause** (22,844 of 28,899 at 16
episodes per lesson), which is the honest ceiling on everything built from it.
The scaffolding above the clause — record, field, list — is not recovered at all
and is assembled from block layout, so the classical parsers are grammars *of
clauses* with a hand-built document skeleton. That cap is in the code.

The induced grammar is 4,487 productions over two preterminals — `ARG` and the
literal word — with `P(ARG | token)` from training counts and the unseen-token
rate estimated on hapaxes rather than written down (it comes out at **0.716**:
a token never seen in training is usually a nonce symbol, and usually an
argument). Surface order and graph slot are stored separately, which is the one
piece of linguistics in the file and is what lets Turkish's verb-final rendering
be one extra production over the same head rather than a new predicate. A test
asserts exactly that.

Productions are flat, so the LR(0) item-set automaton of this grammar *is* the
trie of right-hand sides. All three parsers walk the same automaton:

| | size | uas | type_acc | bracket_f1 | edge_f1 | label_f1 | ted_sim |
|---|---:|---:|---:|---:|---:|---:|---:|
| floor | | 0.075 | 0.548 | 0.004 | 0.039 | 0.123 | 0.313 |
| `bracket-001` (written down) | 1.91 | 0.145 | **0.644** | 0.020 | 0.080 | 0.455 | 0.401 |
| `lr-001` (deterministic) | 2.34 | 0.175 | 0.547 | 0.062 | 0.129 | 0.369 | 0.326 |
| `cky-001` (exhaustive chart) | 1.52 | 0.299 | 0.594 | **0.168** | 0.261 | 0.527 | 0.472 |
| `shiftreduce-001` (perceptron) | 1.09 | **0.309** | 0.556 | 0.164 | **0.267** | **0.528** | **0.515** |
| `retrieve-001` (no parsing) | 1.00 | **0.568** | **0.943** | **0.228** | **0.697** | **0.758** | **0.768** |

Three things, and the third is the one that matters:

- **The chart earns its search.** `cky-001` is 2.7x `lr-001` on bracket F1 and
  2x on edges, on the same grammar and the same lexicon. The pre-registered
  alternative — that a deterministic maximal-munch pass would match the chart,
  making the search wasted work — is refuted: these productions share prefixes
  and differ later, which is exactly the case a chart exists for.
- **A learned greedy oracle recovers what the chart gets by searching.**
  `shiftreduce-001` matches `cky-001` within noise on every metric, beats it on
  `uas`, `ted_sim` and `edge_f1`, and does it in one left-to-right pass. It also
  over-generates far less: **1.09 nodes per gold node against the chart's 1.52**,
  which is where the `ted_sim` gap comes from. This is transition-based parsing's
  standing claim, and it reproduces here.
- **All three still lose to memorising.** `retrieve-001` does no parsing at all
  and beats the best of them by +0.06 bracket F1, +0.43 edge F1 and +0.23 label
  F1. Composing an answer is not yet competitive with recognising which of 179
  lessons the text is.

### The compositional parsers are the *most* vocabulary-bound

Share of the English score kept, on `bracket_f1`:

| parser | zh | tr | sw |
|---|---:|---:|---:|
| `cky-001` | 0.06 | 0.07 | 0.27 |
| `lr-001` | 0.05 | 0.06 | 0.08 |
| `shiftreduce-001` | 0.08 | 0.11 | 0.29 |
| `retrieve-001` | 0.40 | 0.86 | 0.87 |
| `template-002` | **0.46** | **0.72** | **0.73** |

This was not expected and is the opposite of the usual story about grammars
versus lookup tables. The reason is structural: a production's right-hand side is
keyed on **literal words**, so translating the frame words invalidates every
rule at once, while a template lookup can be keyed on punctuation and line
structure and never needs to read a word. A grammar over word classes rather
than word forms would be the obvious repair and has not been built.

### Cross-language: the clean test, and my prediction was wrong

`langcurriculum` takes a language when it renders and takes none when it
structures, so the same seed gives a different string in every language and a
**byte-identical graph**. For the masked-node task that is a disappointment
(`tests/test_language.py`). For a parser it is the ideal experiment: the target
is fixed, the input is translated, nothing else changed.

The pre-registered prediction, written into `parsers/template.py` and committed
before the sweep ran, was that a dictionary-seeded parser would collapse in
Chinese and a grammar-learning one would not. **The opposite happened.** Share
of the English score kept:

| parser | lookup signal | zh retrieval | zh label F1 kept | tr | sw |
|---|---|---:|---:|---:|---:|
| `template-001` | "layout" | **0.02** | **0.16** | 0.29 | 0.87 |
| `retrieve-001` | word identity | 0.34 | 0.47 | 0.89 | 0.90 |
| `template-seeded` | word identity | 0.34 | 0.38 | 0.79 | 0.80 |
| `template-002` | punctuation and lines | **0.74** | **0.60** | 0.82 | 0.84 |

The parser designed to be language-independent was the one that collapsed
hardest, and word identity — the thing translation is supposed to destroy —
transferred better than it did. The cause is worth writing down because it is
not about parsing at all:

**`layout_features` was not measuring layout.** It counted tokens, measured
their mean length, and counted how many were ASCII. Every one of those is a fact
about the *tokenisation*, and Chinese retokenises the same document into far
more, far shorter, non-ASCII pieces. The feature vector moved wholesale and the
nearest-neighbour lookup went to the wrong lesson 98% of the time.

`template-002` is registered beside `-001` rather than replacing it, and uses
punctuation counts and line structure only. Settled on **held-out training
episodes** rendered in each language (seeds 200-201) before it was ever run on
eval:

| feature set | en | zh | tr | sw |
|---|---:|---:|---:|---:|
| `layout_features` (token shape included) | 0.983 | 0.014 | 0.084 | 0.966 |
| `shape_features` (punctuation and lines) | 0.933 | **0.690** | 0.860 | 0.860 |

Two more from the same measurement:

- **NFKC is not enough for CJK punctuation.** It folds `：` and `；`, which are
  compatibility forms, and leaves `、` and `。` alone, which are not. The
  ideographic comma is the list separator in the Chinese rendering, so without
  an explicit fold the document reads as having no separators: Chinese lesson
  identification is **0.212 unfolded and 0.690 folded**.
- **Counting identifiers looks language-independent and is not.** Adding "how
  many ASCII identifier tokens" took English to 0.969 and Chinese to 0.159,
  because in English that count includes every English word and in Chinese only
  the untranslated symbols. It is a vocabulary-size feature wearing a shape
  feature's name. Not used.

The honest summary of the language axis is that **script and tokenisation
dominate it, not grammar versus vocabulary**. Swahili costs almost nothing to
anything (0.80-0.90 kept across the board, and 0.87 even for the broken
`template-001`), because it keeps the Latin script, the layout and a good deal
of untranslated English. Chinese costs everything that touched a token. A
cross-language claim in this repo should say which of those two it is testing.

### Dictionary seeding: a null that shrinks to zero

The knob is `Lexicon.from_curriculum` — build the frame/content judgement from
the whole curriculum's vocabulary instead of estimating it from the training
episodes. It is registered as `template-lex` with `template-001` as the
unseeded control on the identical lookup, and the bare name `template` resolves
over numbered versions only, so nothing can ask for "the template parser" and
get the seeded one.

| training episodes per lesson | `template-001` label F1 | `template-lex` label F1 |
|---:|---:|---:|
| 2 | 0.787 | 0.798 |
| 16 | 0.832 | 0.832 |

**+0.011 at two episodes per lesson, and identical to three decimals at
sixteen** — on every metric and in every language. The judgement it seeds
saturates almost immediately: a template constant appears in *all* of a lesson's
episodes, so two draws already separate it from a content word most of the time.
A curriculum-wide dictionary buys nothing a handful of examples does not, and
`FRAME_THRESHOLD` was not swept to rescue it.

## The VSA was not unbinding anything, and permutation fixed it

`runs/vsa_reach`, all 179 lessons, same config, floors and evaluation seeds as
every other row. The `vsa-002` and `corefer-001` rows reproduce their published
numbers to three decimals, so the two runs are directly comparable.

**The diagnosis, which is a fact about the algebra rather than a measurement.**
`VSAModel._trace` superposes only nodes that have a label, and the masked node's
label is `None`. Its binding was never in the trace, so `role(i) * trace` is not
a recall — it is the crosstalk, and the score of candidate `s` collapses to
`sum over {j : label_j = s} of <role(i), role(j)>`. A role is a *product* of four
independent bipolar atoms, so that inner product is `d` when the two role tuples
are identical and a zero-mean random walk otherwise: measured at `d = 4096`,
**4096 ± 0 on a match against 4 ± 60 on a mismatch**. Sixty-eight standard
deviations. `vsa-002` is a **hard partition** — "the commonest symbol among the
visible nodes sharing my exact `(ptype, slot, depth, arity)`" — which is a table
lookup, and a worse one than the floor's, since it has one key and no back-off.

On a five-lesson diagnostic slice a visible node with the query's exact role
tuple exists for only **37.5%** of scored nodes, and where none exists the model's
label accuracy is **0.000**. The copy head's -0.115 was never a readout defect on
top of a working retrieval. The retrieval had no reach.

**The fix is the operator the family never had.** The copy floor keys on the
relative *node-index* offset `i - source`, and no role atom encodes position.
Permutation is the standard third VSA operator and is exactly what binds order:
`seq = sum_j rho^j(cb[label_j])`, probed at `sum_k w_k rho^{k-i}(seq)` with `w`
counted per structural context on **training** episodes, keyed on the head of the
same ladder the floor keys on. Two things differ from the floor and both are
priced below: it superposes the top six routes where the floor takes the arg-max
over them, and it has a back-off ladder where the floor has one key and a global
fallback.

| model | lbl acc | lbl lift | bits | bits lift | copy acc | copy lift | rename | secs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `vsa-002` | 0.219 | +0.089 | 6.80 | +0.275 | 0.181 | -0.115 | 0.029 | 35 |
| `vsa_pure-002` | 0.200 | +0.066 | 6.94 | +0.259 | 0.181 | -0.115 | 0.002 | 35 |
| `vsa_addr-002` | 0.219 | +0.089 | 6.80 | +0.275 | 0.210 | -0.076 | 0.029 | 44 |
| `vsa_addr_pure-002` | 0.200 | +0.066 | 6.94 | +0.259 | 0.210 | -0.076 | 0.002 | 43 |
| `vsa_transform-002` | 0.242 | +0.116 | 6.69 | +0.286 | 0.254 | -0.016 | 0.021 | 44 |
| `vsa_perm_one-002` | 0.295 | +0.178 | 6.64 | +0.292 | 0.301 | +0.048 | 0.006 | 44 |
| `vsa_perm-002` | 0.326 | +0.213 | 6.49 | +0.307 | **0.310** | **+0.060** | 0.010 | 41 |
| `vsa_perm_pure-002` | **0.337** | **+0.227** | 6.62 | +0.293 | **0.310** | **+0.060** | **-0.003** | 40 |
| `vsa_full-002` | 0.325 | +0.212 | 6.42 | +0.314 | 0.300 | +0.047 | 0.010 | 45 |
| `vsa_full_gated-002` | 0.327 | +0.215 | 6.41 | **+0.316** | 0.299 | +0.045 | 0.008 | 56 |
| `vsa_full_pure-002` | 0.328 | +0.216 | 6.56 | +0.300 | 0.300 | +0.047 | -0.000 | 46 |
| `corefer-001` | **0.357** | +0.250 | 6.95 | +0.258 | **0.336** | **+0.096** | 0.003 | 197 |

Floors: label 0.143, type 0.860, copy 0.266, copy ceiling 0.722. The type head was
not touched and every row sits at -0.486, which is where `vsa-002` already was;
design rule 1 says the two heads do not share machinery and nothing here does.

- **The copy head crosses its floor**, -0.115 to +0.060: a swing of 0.175, larger
  than the entire spread between the four pointers this repo already had.
- **The label head moves further than the copy head did**, +0.089 to +0.213,
  because in this model they are one computation — reaching for a source *is*
  reaching for a symbol. The family was near-last on accuracy and its best row is
  now 0.337 against `corefer`'s 0.357, without giving up its bits. That ranking
  is against the rows in this sweep and the established table above, not a fresh
  nineteen-model run.
- **The control does not carry it, and is not nothing.** `vsa_addr-002` changes
  only the pointer *readout* — a node scores by its address, `<Q(i), role(j)>`,
  rather than by the mass its label received — and recovers +0.039 of the copy
  deficit while leaving the label head identical to three decimals. So a third of
  the pointer's problem was that it was the label head read twice, and two thirds
  was that it could not reach.
- **The analogical transform is the weaker half.** Learning per context which
  roles the answer occupies and superposing them into one query vector (`a:b::c:?`
  in one multiply) is worth +0.027 label lift and +0.099 copy — real, and a third
  of what permutation buys.
- **Superposing both channels is worse than the better one alone, and weighting
  them does not rescue it.** `vsa_full` loses 0.013 copy lift against `vsa_perm`
  and gains 0.007 bits. The obvious defence is that an equal share is too much
  for the weaker channel, so `vsa_full_gated-002` fits the share on held-out
  *training* episodes by held-out likelihood — design rule 4, the mass on
  whichever symbol turned out to be right rather than whether the argmax was it.
  It lands **interior at 1.25** and the row still trails `vsa_perm-002` on the
  head the channel was added for. Pre-registered and refuted: the role transform
  is subsumed once relative position is available, not mis-weighted.

  The first attempt at this answered nothing and is recorded so the mistake is
  not repeated: the grid stopped at 1.0, the fit landed on 1.0, and the model came
  out bit-identical to `vsa_full-002`. A boundary optimum cannot distinguish "this
  is the best balance" from "the grid was too narrow", and reporting it as a null
  would have been wrong.
- **Superposing the *routes* is worth less than it looks, and the control says
  so.** `vsa_perm_one-002` pins `top_k = 1`, which makes it the copy floor's own
  rule — same key, arg-max offset — expressed in hypervectors. It scores **+0.048
  copy lift**, so four fifths of the gain is there before a single route is
  superposed, and the mixture over six routes adds +0.012 copy and +0.035 label
  on top. The honest reading is that the *positional channel* is what was
  missing; the superposition is a real but secondary refinement. Note the
  single-route row still clears the floor it is a copy of, because it inherits a
  back-off ladder the floor does not have, a graded cleanup and a calibrated
  gate — so +0.048 is not "the floor scored above itself", it is what those three
  are worth on top of the same rule.
- **The memorising fallback stops being worth anything — it starts costing.** For
  `vsa-002` the shared `structural_fallback` was +0.019 accuracy and all of its
  renaming sensitivity. For the reaching variants it is **negative**:
  `vsa_perm_pure-002` scores 0.337 against `vsa_perm-002`'s 0.326, and
  `vsa_full_pure-002` 0.328 against 0.325. The fallback was compensating for a
  retrieval that could not find anything, and charging the family its one
  distinguishing property for the service.
- **The best row in the family is now the exactly equivariant one.**
  `vsa_perm_pure-002`: label lift **+0.227**, bits lift +0.293, copy lift +0.060,
  renaming drop **-0.003** over a permutation of all 2,105 symbols, in 40
  seconds. It is within 0.023 label lift of `corefer-001` at a fifth of the
  runtime, and unlike `corefer` its equivariance is a property of the algebra
  rather than a measurement that came out well.
- Still 0.310 of a 0.722 ceiling, and still behind `corefer` on the copy head.

**A seventh small-sample artefact, caught this time before it was written up.**
The first equivariance measurement of the permutation variants used the module's
24-episode test fixture and read **+0.051** against `vsa_pure-002`'s 0.000 —
which says the new channel bought its accuracy by memorising. The obvious
mechanism, superposition crosstalk (the sequence trace is loaded by *every* node
where the role trace is not), was checked and refuted: raising `d` from 4096 to
16384 moved the drop the wrong way. Re-measured with more episodes:

| eval episodes | `vsa_pure` | `vsa_perm_pure` | `vsa_full_pure` |
|---:|---:|---:|---:|
| 24 | +0.000 | +0.051 | +0.051 |
| 72 | +0.010 | +0.005 | +0.010 |
| 192 | -0.002 | +0.008 | +0.008 |

It was sampling noise, and the full curriculum agrees: `vsa_perm-002` is +0.010
against `vsa-002`'s +0.029 — *less* renaming-sensitive, not more. The lesson is
the one this repo keeps paying for, with one difference worth recording: this is
the first time the artefact was caught by re-measuring at a larger sample rather
than by a later sweep contradicting a published claim.

## The readout is worth more than the model, and it survived an independent attack

`runs/agent-sweep/` and `runs/agents-readout179/`, all 179 lessons, 716
evaluation episodes, 2,632 scored fills, `repair`. **The floor is `context`
0.2025 in every row below**, which is what makes them one table.

The same fitted `corefer-001` — same model, same episodes, same prior, same
calibrator — read two ways:

| agent | reads the output as | candidates | `label_acc` | lift |
|---|---|---:|---:|---:|
| `graphread` | **a move** | 24 | **0.5080** | **+0.383** |
| `graphread-capped` | a move | 8 | 0.3609 | +0.199 |
| **floor** (`context`) | — | | *0.2025* | *0* |
| `abstain` | nothing at all | — | 0.0866 | −0.145 |
| `wrap` | **text** | 8 | 0.0851 | −0.147 |
| `wrap` | text | 24 | 0.0767 | −0.158 |
| `wrap-envcal` | text | 24 | 0.0760 | −0.159 |
| `random` | — | — | 0.0543 | −0.186 |

**This is the largest effect in the repo and it is not a model difference.**
Models span about 0.1 of lift. One readout swap spans 0.43 — and `corefer-001`
was registered and sweeping the whole time, able to do this, with no way for the
harness to ask.

**It was attacked by an agent that did not write it, and the gap grew.** The
author named two confounds and ran neither; both were run, with thresholds
committed 22 minutes before the first number landed.

- **The candidate cap is real, asymmetric, and runs backwards.** `wrap` sees 8 of
  `repair`'s 24 candidates and `graphread` sees all 24, so part of the gap was
  truncation. Capping `graphread` to 8 costs it 0.147 — so the cap was worth a
  third of the published gap. But the direct control says `wrap` at **24** scores
  **0.0767, *lower* than its 0.0851 at 8**: the extra candidates cost `wrap`
  nothing because it was never using them. On equal candidate sets the gap is
  **0.4312, larger than the 0.4229 published.**
- **The calibrator was a third difference nobody had named** — `wrap` fitted on a
  freshly built `choice`, `graphread` on the run's own environments. Equalising
  it is worth 0.0007. Equalising all three differences leaves **0.4320**, the
  largest of the four framings. A gap that grows as its confounds are removed is
  the opposite of a confounded result.

**And the comparison row turns out to be silence, which corrects the finding's
own interpretation.** `wrap` 0.0851 against `abstain` 0.0866 — four fills of
2,632, and *identical on `success` to sixteen figures* over 716 episodes. So the
claim that "reading this model as text is actively bad" is unearned. The honest
statement is cleaner and stronger: **reading these models as text is
indistinguishable from saying nothing at all**, and eleven of nineteen models
cannot emit a token anyway.

**A slice finding died on the way.** "Abstention on `repair` is below chance" was
measured on six lessons and inverts at 179: `abstain` 0.0866 against `random`
0.0543 is **0.032 above** chance, not 0.060 below. Both rows moved, in opposite
directions, and no mechanism for either move has been measured. The note named
this as its own live risk and was right to.

## Generation: absent, not mis-measured — and the reframe that predicted otherwise was wrong

The pre-registered claim was that the `lm` task's total failure (11 of 19 models
unable to emit a token, `exact_match` 0.000 everywhere) was a **readout artefact**,
because the same fitted `corefer-001` scores 0.508 read as a move and 0.085 read
as text. Masked-node prediction at 15% is parse-tree infilling, the renderer is
deterministic, so generation should reduce to graph completion plus an exact
render. **That was checked first because it could refute, and it did.**

`runs/infill-ans`: hide every node whose label is the episode's answer. All 179
lessons, 716 episodes, 841 scored fills, floor **0.101** refitted under this
regime.

| model | `ansnode_acc` | lift | renaming drop |
|---|---:|---:|---:|
| `grammar-001` | 0.181 | +0.089 | 0.184 |
| `ngram-001` | 0.169 | +0.075 | 0.164 |
| *floor* | *0.101* | — | — |
| `gparse-none` — **emits nothing** | 0.004 | −0.108 | — |
| `corefer-001` | **0.001** | −0.111 | 0.001 |
| `routes-001`, `evidence-001` | 0.000 | −0.112 | — |

**Nine of twelve models land on the abstention row**, and `ptrgen-001`,
`vsa_perm-002` and both `omegaclaw` rows match "say nothing" to **nine decimal
places** — two of them in bits as well. The only three rows that clear the floor
lose all of it under a symbol permutation. Changing the readout releases nothing:
the models that can answer on the graph are the same memorisers that could
already answer on the text.

Two controls, because the task design could have manufactured the null:

- **`nodeans1`** hides only the *first* copy, so a pointer has something to point
  at: `corefer` goes 0.001 -> **0.072**, sixty-fold, and is *still* below its
  0.092 floor. So the zero was substantially design — **and the pointer still
  does not answer.**
- **Undertraining**: answer-masking supplies 8x fewer examples, so fit under
  scatter and score under answer. `corefer` 0.0012 -> **0.0000**, `ptrgen`
  0.0036 -> 0.0000. More supervision makes it worse.

**The mask rate is a supply knob, not a difficulty knob** — and this is the
cleanest quantitative prediction the repo has made. `corefer-001`, floors
refitted at every rate:

| | 0.15 | 0.35 | 0.60 | **0.90** |
|---|---:|---:|---:|---:|
| copy ceiling | 0.722 | 0.680 | 0.583 | **0.302** |
| acc \| copyable | 0.494 | 0.488 | 0.486 | **0.597** |
| acc \| **not** copyable | 0.003 | 0.003 | 0.004 | **0.001** |
| split floors, copyable / not | 0.158 / 0.106 | 0.159 / 0.106 | 0.158 / 0.104 | **0.183 / 0.102** |
| **predicted from the supply alone** | — | 0.337 | **0.289** | 0.151 |
| **observed `label_acc`** | 0.357 | 0.332 | **0.285** | **0.181** |
| prediction error | — | +0.005 | **+0.004** | **+0.030** |

**Over most of the range the ceiling moves and the ability does not.** From 0.15
to 0.60 the copy ceiling fell 0.139 while `acc | copyable` moved 0.008, and a
supply-only model — hold both conditional accuracies at their 0.15 values, move
only the share — predicted the pooled score to **0.005 and 0.004**. That
prediction was committed while the 0.35 arm was still running. Both split floors
stayed within 0.002, so nothing became harder for something that cannot read a
symbol; only the opportunity to copy shrank.

**At 0.90 the supply model breaks, and not in the model's favour after all.**
Predicted 0.151, observed **0.181** — a 0.030 miss where the previous two were
0.004. The split, computed on a refit that is bit-identical to the published
arm and pre-registered before it landed: `acc | copyable` **rises** to 0.597 and
`acc | not copyable` **falls** to 0.001. The cause is survivorship, and the proof
is a predictor that cannot improve — the structure-only split floor's copyable
column is 0.158 / 0.159 / 0.158 and then **0.183**, flat for three rates and up
exactly where the model's went up. **Copyability is defined by what is
*visible*, so the mask rate controls the bucket's composition**: the share of
the copyable bucket whose label occurs ten or more times goes 22% -> 42%, which
is two thirds of the movement. Hold the evidence at constant *concentration*
(visible same-label nodes over visible labelled nodes, which falls from 61.6 to
7.3 per fill) and the comparison inverts — the 0.15 conversion rates applied to
the 0.90 mix predict **0.212**, so the fine supply variable overshoots by 0.031
almost exactly as the coarse one undershoots by 0.030. And `copy_lift`, which
was in every `summary.json` all along, falls monotonically for **six of six**
pointer models and is negative for all six by 0.60 (`corefer` +0.096, +0.057,
−0.013, **−0.149**). And the survivorship is a fact about the bucket rather than
about the models: split **all twelve ways** at 0.90, `acc | copyable` rises for
six and falls for six, and the line between them is the mechanism — **every one
of the four vocabulary models falls** (`brill` −0.226, `ngram` −0.108, `grammar`
−0.090, `ctw` −0.033) while five of the eight equivariant rows rise (`evidence`
+0.165, `ptrgen` +0.107, `corefer` +0.103). Survivorship hands its gift to
predictors that *point*, because what survives into the copyable bucket is a
repeated label. `routes` (−0.033) and `ruleinduce` (−0.038) are equivariant and
still lose ground, through a bucket that got 0.025 easier for a lookup table.
**Story 2 is dead for eleven of twelve**: `acc | not copyable` *falls* everywhere
except `ptrgen` (0.010 → 0.034), so the memorisation channel carries *less* of
the mixture at 90% masking, not more. And the pooled leader leads on the wrong
channel — `ptrgen` is first pooled at 0.195 and `corefer` first on copying at
0.597, the gap being entirely `ptrgen`'s memorisation column, which is exactly
zero under renaming. `routes-001` shows what the mix hides: its
two largest multiplicity strata fall by **0.109 and 0.168** while its pooled
conditional falls by 0.033. Standardised over the concentration mix, **all five
models measured are below their own 0.15 conversion rate** — `corefer` −0.099,
`ptrgen` −0.120, `vsa_perm` −0.149, `evidence` −0.149, `routes` −0.242, against
`copy_lift` of −0.149, −0.153, −0.164, −0.148, −0.219 — and 19 of 20 band
comparisons put 0.90 below 0.15. `evidence-001` has the largest pooled *rise* of
the six, +0.165, and a −0.149 shortfall.

**Attacked the same day by an agent who wrote their own scoring code, and the
direction held while the size did not.** Six of six models negative under `v/V`,
six of six under a bandless logistic, six of six holding node type; the banding
is priced at +0.013, so the reading understated rather than flattered. But the
shortfall's *magnitude* is an extrapolation — 2.6% of the 0.15 fills have `V` in
the 0.90 arm's range — and holding node type takes `corefer` from −0.098 to
−0.062, so **−0.099 is an upper bound and not an estimate**. The refuter also
found the better control: tokenizers are byte-identical across arms, so the
**0.15-fitted weights scored on the 0.90 draw, with no refitting, gain +0.1038 of
`acc | copyable`** against the 0.90 arm's +0.1035. A predictor whose ability is
frozen picks up the entire rise — survivorship measured directly, with no
covariate and no floor. *The ability was never flat; the conditional
that looked flat is a mixture whose weights the knob controls.* See
`notes/findings/2026-08-15-the-ninety-percent-point-is-a-different-bucket-not-a-better-model.md`
and the lesson it produced,
`notes/lessons/2026-08-15-a-conditional-is-not-a-fixed-question.md`. Provisional:
author-designed controls only.

Both pre-registered expectations were refuted: pointer models do **not** degrade
fastest (they retain 86% against 65% for no-pointer rows — and the pointer axis
was itself wrong, since `omegaclaw_rank` has no pointer head and behaves exactly
like `corefer`; the axis that works is the renaming column), and there is no
cliff at 0.35.

**Masking a whole subtree is the knob that moves the ability.** At matched budget,
nine of nine models are worse: supply barely moves (ceiling 0.722 -> 0.698) while
`acc | copyable` drops 0.111 for `corefer`, 0.113 for `ptrgen`, 0.133 for
`routes` — twenty times what the mask rate cost. The floor's own copyable
advantage collapses 0.052 -> 0.002, so what is lost is **local context**, not
model capability.

**And partial credit has been flattering everything by a factor of ten.**
`corefer-001` gets **0.0380** of episodes entirely right at `mask_rate=0.15`
against its 0.357 partial-credit score, **0.0014** at 0.35, and **0.0000** on
the answer task. The ordering differs too — `ruleinduce` is fourth pooled and
first exact.

**The rung-4 bound this was first written with points the other way.** It said
that because the renderer is deterministic, `exact_match` is bounded *above* by
whole-graph exactness. Determinism gives the opposite implication: a function
maps equal inputs to equal outputs, so a right graph renders to right text and
`exact_match >=` graph exactness. An upper bound needs the render to be
**injective**, which nothing here has measured. Measured instead: **a third of
all scored fills carry symbols that never appear in the prompt at all**, so a
wrong graph can still render right, and `corefer-001`'s rung-4 number lies in
**[0.038, 0.15]** at 0.15 — one episode in seven at the top end, not "essentially
unachieved". At 0.90 both ends are ~0 and the conclusion is safe. Rung 4 is
therefore **open**, not answered by a bound. See
`notes/findings/2026-08-15-rung-fours-bound-points-the-other-way.md`.

## `005`: the type head is saturated, not unattacked

`runs/metta005`, 19 rows, all 179 lessons, same floors as every other row: label
0.143, type 0.860, copy 0.266, copy ceiling 0.722. The IR-as-a-knob line's first
candidate — **AtomSpace/MeTTa, whose native operation is match and rewrite**.

**The type head moved for the first time, and it still lost.**

| | type acc | type lift | type bits lift |
|---|---:|---:|---:|
| every other VSA-family row | 0.7922 | −0.4855 | +0.4931 |
| **`metta_type-005`** | **0.8203** | **−0.2849** | **+0.5660** |

That is **+0.201 of type lift**, the largest movement any row in this family has
shown on the head this log called "the last one nothing has attacked" — and it is
still **0.285 below the floor**. Both halves are the result. The reframe is what
to take away: **the type column was saturated, not unattacked.** A six-level
backed-off ladder over tree shape is simply very good, and reading what a node
*contains* — a direction no key in this repo had ever had — is worth a fifth of
the gap and loses anyway.

Design rule 1 held, and was checked in the arithmetic rather than asserted:
against `metta-005`, the `metta_type-005` row moves type lift by +0.201 while
`label_lift`, `label_bits_lift` and `copy_lift` are **identical to four
decimals**. The type gain did not come from the label route, which is the mistake
`corefer` paid 0.174 -> 0.004 for.

**Expressiveness is not the binding constraint — third independent
confirmation.** The pre-registration predicted the label null and named the
reason: `omegaclaw_reach-001` added `ilp`'s best discovered operator and lost;
candidate recall climbing 82.7% -> 98.7% moved accuracy by 0.000. Confirmed wide,
0.274 against `corefer`'s 0.357. MeTTa *can* express things `CLAWS` cannot — the
typed slot-selected sibling, the downward direction, arbitrary-length joins,
bounded transitive closure — and it does not help the head this repo leads with.

**A structural bits gain that survives renaming.** +0.011 bits lift at a **+0.001**
renaming drop, all 2,105 symbols permuted without refitting — against
`ensemble-001`'s +1.14 that collapsed 0.467 -> 0.038 on the same test. A tenth
the size, keeping essentially all of it. Accuracy is flat (0.213 vs 0.214), so an
"atomspace roles win" headline and an "atomspace roles are a null" headline are
both available from this table and both misreport it.

**A `Graph` cannot be content-addressed into an atomspace.** The
pre-registration's own proposed encoding would have collapsed **42.3% of all
nodes** (26,351 of 62,253, affecting 97.1% of graphs), because a `Graph` is a tree
of *occurrences* and an atomspace is a set of *values*. Caught by the round-trip
test covering all 179 lessons rather than sampling a fixture — the
`test_encoding_is_lossless` failure mode, caught before it could publish
anything. An outside `hyperon 0.2.10` agrees on 1,575 bindings with 0
disagreements, with a self-test proving the check can fail.

**Cost fired, and the absolute rate is refused.** The IR alone is 2.6x, the full
schedule 9.5x. The calibration control read `vsa_sum-004` at 0.50x its published
throughput, so no absolute rate from that pass is quotable and none is quoted.
For context `vsa_sum-004` at d=4,096 is already 15x below `APPROACH.md`'s target
before any atomspace exists, and **a `005` row at d=256 was never run** — the
cheap experiment this line skipped.

**The copy result survives an independent attack, and shrinks by two thirds.**
`metta_perm_pure-005` reaches **+0.1091** copy lift against `corefer-001`'s
+0.0959 — the first thing in this repo's history to lead the pointer. A refuter
who did not write it eliminated the three artefact hypotheses that would have
killed it:

- **Same question.** The scored `(batch, row, node)` key lists are *identical*
  across all four models on every draw; pads and self excluded symmetrically.
- **Not the shared back-off.** `structural_fallback` reaches `symbol_logits`
  only, never the pointer. Decisively: the flat pointer back-off scores **0.0000**
  and coverage is **1.000** for every model, so on this head abstention is
  punished rather than subsidised and the "back-off wearing the model's name"
  mechanism cannot operate.
- **Not one lucky mask.** Paired McNemar plus a lesson-cluster bootstrap over
  five draws, including 716 **fresh** episodes: `metta` leads 5/5 and the order
  never flips.

**But the improvement was quoted against the wrong baseline, and the honest
number is a third of it.** The finding compared to `vsa_perm_pure-002` (+0.060)
and omitted `vsa_perm_hks_wide_pure-004` at **+0.0926** — which this same log
names the second-best pointer. Decomposed properly: **+0.0327 for graph-derived
roles at all, and +0.0165 for the atomspace specifically.** That increment is
significant on all five draws; the headline +0.049 was never the atomspace's.

And **on the published draw alone the lead over `corefer` is not significant** —
56 items in 5,785, McNemar p = 0.057. Replication carries it, not that mask. Two
further honest notes: second place is a coin flip (`corefer` vs `hks_wide`
changes sign across draws), and the lead is bought on questions with 3+
coreferent sources and given back on two-source questions.

One thing the leading row has outright: **its pointer is bit-identical under a
permutation of all 2,105 symbols**, where `corefer`'s moves because
`_pair_features` reads prompt mention counts. It reads strictly less and wins.

**Correction to a number quoted throughout this file.** `copy_ceiling` is
computed over `label_n` = 5,233 and quoted against `copy_acc`, which is scored
over 5,785. On its own denominator the ceiling is **0.7305**, not 0.7216. Every
"0.722 copy ceiling" here is that mismatch; the conclusion it supports — that
more than half the reachable signal is untouched — is unaffected, since 0.346 of
0.7305 is if anything further from the ceiling.

## Roles derived from the graph, and a bandwidth nobody had fitted

`runs/vsa_role`, 27 rows, all 179 lessons, same floors as every other row: label
0.143, type 0.860, copy 0.266, copy ceiling 0.722. Attacked by an agent that did
not write it; **all four load-bearing conclusions survive and the headline was
0.053 too low.**

A role in `vsa-002` is the product of four random atoms indexed by
`(ptype, slot, depth, arity)`, and because the codebook is bipolar the candidate
score reduces exactly to the **role Gram matrix**. Swapping the role construction
and touching nothing else is therefore a controlled experiment by arithmetic.

`_pure` rows — no shared memorising fallback, so the algebra is what is measured:

| model | role Gram | lbl lift | bits lift | copy lift | rename |
|---|---|---:|---:|---:|---:|
| `vsa_null_pure-004` | i.i.d. — **the bottom row** | −0.125 | 0.201 | −0.320 | +0.003 |
| `vsa_hks_shuf_wide_pure-004` | signature **shuffled**, matched | −0.075 | 0.166 | −0.264 | +0.000 |
| `vsa_spec_shuf16_pure-004` | eigenmap shuffled, matched | −0.070 | 0.192 | −0.259 | −0.003 |
| `vsa_spec_pure-004` | Laplacian eigenmap | −0.044 | 0.212 | −0.232 | −0.001 |
| `vsa_pure-002` | product of atoms | +0.066 | 0.259 | −0.115 | +0.002 |
| `vsa_sum_pure-004` | **sum** of the same atoms | +0.083 | 0.282 | −0.097 | −0.000 |
| `vsa_hks_wide_pure-004` | **heat-kernel signature, fitted** | **+0.160** | 0.292 | −0.014 | +0.006 |
| `vsa_perm_hks_wide_pure-004` | signature + permutation | +0.187 | **0.316** | **+0.093** | −0.002 |
| `vsa_perm_pure-002` | partition + permutation | **+0.227** | 0.293 | +0.060 | −0.003 |

**The graph beats the hand-built coordinates, and by twice what was published.**
`vsa_hks_wide_pure-004` uses **no hand-built coordinate of any kind** — no parent
type, no slot, no depth, no arity. Each node's role is its heat-kernel signature,
a spectral quantity invariant under graph automorphism. At **+0.160** against the
hand-built partition's +0.066 and the hand-built graded ladder's +0.083.

**The published +0.107 was measured at a bandwidth the data does not want.** All
four `vsa_hks*` rows fitted `knob = 0.5` — the **bottom** of their grid. Extended,
the fit lands **interior at 0.25** and gains +0.053. This repo wrote a lesson that
same day saying a boundary fit is a failed fit until re-run wider; **the lesson
was invoked on the arm that lost and skipped on the arm that won**, and on the
losing arm it gave the wrong reading. That is now its own lesson,
`notes/lessons/2026-08-14-a-guard-applied-only-to-the-arm-that-lost.md`.

**The shuffled control is load-bearing and the effect is bigger than claimed.**
Permuting the signature rows across nodes preserves the Gram's value multiset and
destroys only the correspondence to the graph: +0.160 → −0.075. But the family had
no *bottom* row, so "gradedness contributes nothing on its own" had nothing to be
nothing against. `vsa_null_pure-004` (i.i.d. roles) supplies it at −0.125, so
gradedness alone is worth **+0.051**, and two unrelated shuffled embeddings agree
on that to 0.001. The corrected split is **82% correspondence, 18% gradedness** —
not 100/0.

**The pre-registered eigenmap is refuted**, at −0.044, below the floor, beating
its own matched control by only 0.026. Extending the diffusion grid 64x leaves it
**bit-identical**, so `t = 16` was an interior optimum all along and "a wider grid
cannot rescue it" has gone from an argument to a measurement. The mechanism given
for it — a term tree alternates functor and argument levels, so a label-carrying
node is always an even number of hops away — was a three-lesson slice and does not
survive: "always even" is **91.2%** at 179 lessons, and "the nearest visible node
never carries the answer" is 0.022, not 0.000. **The direction survives, the
absolutes do not.**

**`*` → `+` is still the cheapest result here.** Superposing the four atoms
instead of binding them is +0.017 label lift on the `_pure` pair and halves the
renaming drop, with no graph at all — and without it, a win for any graph
embedding would be unattributable between "graded helps" and "graph-derived
helps".

**The three heads still disagree, and that is the strongest thing in the work.**
Redrawn at the fitted bandwidth, `vsa_perm_pure-002` leads on label (+0.227), the
signature leads on bits (0.316) and on copy (+0.093). `vsa_perm_hks` is the
**second-best pointer in the repo**, behind `corefer-001`'s +0.0959. There is no
single ranking of these two models; which is better is a property of the metric.

**And every row in the family sits 0.486 *below* the type floor.** The work quotes
that floor and never returns to it. Nothing here has attacked the type head.

## `006`: the Lean gate closes, and the kernel loses to an arity check

The IR-as-a-knob line's second candidate was **Lean — a representation that can
*refuse* an answer** rather than score it low. It was pre-registered with a
gating diagnostic designed to kill it before a model was ever written, because
the pointer's constraint is measured to be discrimination rather than recall:
candidate recall climbing 82.7% -> 98.7% moved dev copy accuracy by 0.000. So a
typechecker helps only if it prunes candidates *without* pruning the gold one.

All 179 lessons, 537 held-out **training** episodes (eval's seeds untouched),
4,443 scored holes, median 55 candidates each. Reproduced on an independent draw
of 895 episodes at different seeds; nothing moves by 0.01.

| filter | prune (median) | gold survival | matched random |
|---|---:|---:|---:|
| `open` — the sound kernel | 0.286 | 0.988 | 0.634 |
| `declared` — Lean's own rule | **0.355** | **0.984** | 0.486 |
| `closed` — the committing arm | 0.797 | 0.797 | 0.256 |
| **`arity` — the floor** | **0.370** | **0.988** | 0.506 |
| `shifted` — the must-fail control | 0.286 | **0.578** | 0.663 |

**One arm cleared the pre-registered thresholds and it is dominated on both axes
by the floor.** The floor is: *reject a candidate iff no visible occurrence of it
has the hole's number of children.* No types, no unification, no intermediate
representation — any of the nineteen registered models could compute it from the
`Graph` it already reads. The pre-registration's own row-one language applies
exactly: **the IR is a re-encoding with no filter.** No threshold was moved; the
number cleared its threshold and failed its floor.

The two are not nested — the kernel rejects 3,659 candidates the floor keeps and
keeps 5,468 the floor rejects — so taking both prunes 0.388 against the floor's
0.370. **+0.018 of prune for an entire intermediate representation**, against a
measured baseline where sixteen points of candidate recall bought 0.000.

**The instrument works, which is what makes the null readable.** `shifted` — the
same kernel pointed at a different hole of the same episode — holds its prune
rate at 0.286 while gold survival collapses 0.988 -> 0.578, *below* its own
matched-random. The filter reads the hole. And it is not "right but
unaffordable", the failure mode the pre-registration worried about: 291,000
candidate checks per second, about 1.1 s for a full sweep.

**Why there was nothing left for a type system.** Every entity symbol in an
episode collapses into one metavariable component — `alice`, `apple` and
`manipulate` share a type, because the generator never made them differ. Only
`Nat/Str/Chr/Prop` are rigid and all come from literals. What remains is kind and
arity, and arity is free.

**No `lean-006` was registered and no sweep was run.** Phase 2 was never entered.
That is the gate doing its job, and it is the cheapest death any line here has
had.

This is promoted despite its controls being author-designed, and the reason is
worth stating: the failure mode that makes an author's controls untrustworthy is
constructing them to *pass*. Here they killed the author's own line, and the
must-fail control failed as required. A null from the agent that built the thing
runs against its own incentive; a win does not.

## The advantage is `1/f`, and `f` is a property of provenance

The largest correction this file has had to absorb, and it invalidates the
*framing* of every cost row above it rather than their arithmetic.

Every cost comparison in this repo has priced a **cheap-and-wrong** system
against an **expensive-and-assumed-perfect** one. Nobody deploys either. The
choice anyone would make is a hybrid — cheap structure answers what it can, the
rest escalates — and its price is fixed by the escalated fraction `f`:

```
advantage = model / (f x model + (1-f) x ours)   ~   1/f
```

**Neither side of that has a lever.** Measured on affiliation → ROR linking over
5,000 OpenAlex works:

- **The cheap half's accuracy barely matters.** Halving the tier where the
  extractor produces nothing (12.3% → 5.7%, via whole-phrase containment and a
  k-rarest-token candidate lookup) doubled the advantage at 0.60 quality,
  bought 3–8% in the middle, and bought **nothing** at 0.85 — 1.8× before and
  after.
- **The escalated prompt cannot be narrowed.** A cheaper model tier is not ours,
  because the opponent can use the same one. A shorter prompt *would* be ours —
  and is unavailable: adding the k candidate names makes it **1.5× larger**
  (r = 0.68×, k median 5), and the two prompts that genuinely are shorter
  (2.11× and 8.19×) are exactly the two that strip the evidence needed to
  choose. **You cannot both narrow the choice and shrink the prompt, because
  the narrowing is information.**

So on a derived-structure task the number is **1.8× at 0.85 quality**. The
million-fold figures elsewhere in this file price a system running at **53%**
quality.

**And then the same formula in the other regime.** `f` is the fraction of
queries the system cannot settle. Where structure is *filed*, there is no
extraction step to fail — a regulator did it and is legally accountable — so `f`
is only what the data itself leaves undetermined:

| regime | `f` | quality | advantage |
|---|---:|---:|---:|
| **FILED** — GLEIF `ultimate_parent`, **single-source** | **0.216%** | 1.00 | **463×** |
| FILED — incl. closure-vs-filed conflicts | 4.274% | 1.00 | 23× |
| **FILED** — SEC → GLEIF, **CROSS-SOURCE** | **14.7%** | 1.00 | **7×** |
| **DERIVED** — OpenAlex affiliation → ROR | **56.0%** | 0.85 | **1.8×** |

**259× end to end, but the steps are 68× / 4×** — so the cliff is *not* at the
filed/derived edge. It is at the **first identity boundary, inside the filed
regime**, and crossing boundaries is what a federated substrate is for. Same
formula and same code. The advantage is a
property of the domain's **structure-provenance**, not of the technology — which
reconciles the two halves that looked contradictory: this file's earlier
advantages were all measured on GLEIF and SEC, both **filed**, and they were
real. **Quoting either number without naming the regime is the error.**

The mechanism, stated so it can be attacked: in the filed regime `f` is the rate
at which *the world is contested* — disputed ultimate ownership at 0.216%,
disputed sovereignty at 0.068% — which is small and irreducible. In the derived
regime `f` is the rate at which *extraction fails*, which is large and is a
property of the method.

**What is charged and what is granted.** The symbolic side pays for building the
world it answers from. The model is granted perfect accuracy, zero output tokens,
and only the dependency rather than the corpus. Every ratio is therefore a lower
bound and needs no API credentials to stand — which matters, because the accuracy
comparison is still blocked (`ROADMAP.md` 0b).

**Two caveats that belong beside the number, not under it.** Quality 1.0 in the
filed regime is relative to **the filing**, the same circularity as an automated
extractor being its own anchor — better, since a filer is legally accountable,
but not truth. And `f` counts undetermined answers as escalations when this
repo's ambiguity machinery returns the *alternatives enumerated*; a caller that
can act on a retained mixture escalates none of them, so 463× is conservative.

Scripts: `escalation_frontier.py`, `regime_dichotomy.py`, `session_ledger.py`,
`query_floors.py`. Notes: the four findings dated 2026-08-18 under
`the-million-fold-advantage-...`, `the-advantage-is-a-property-of-provenance-...`,
`the-first-arrow-is-cheap-and-bad`, `the-extractor-that-wins-on-facts-...`.

## Federation on identifiers, and why exactness is the product

The `1/f` section above says the advantage collapses at the first identity
boundary — 463× within one filed source, **7×** across two. Closing that looked
like a data-acquisition problem, so the data was acquired: GLEIF's free daily
**ISIN → LEI** mapping, where for US securities `isin[2:11]` *is* the CUSIP, and
13F holdings are CUSIP-keyed. **The first join in this repo that goes through
identifiers rather than names.**

**It does not close the cliff. It converts it.** An identifier join is
unambiguous by construction — **0 of 7,503** bridged CUSIPs map to more than one
LEI — and what replaces ambiguity is **coverage**, which is the larger problem.
A coverage gap escalates exactly as an ambiguity does, so the identifier join
*alone* (f = 77.7% per security) is **worse** than the name join it was meant to
improve on.

**And coverage has four readings spanning 3.5×:**

| denominator | coverage |
|---|---:|
| per distinct security | 22.3% |
| per position held | 58.6% |
| per dollar held, **aggregate** | **79.1%** |
| per dollar held, **median filer** | **58.0%** |

The aggregate describes a handful of giant filers holding large caps with LEIs,
not a typical one. **Which denominator you quote decides the story**, and this
repo now has that error recorded in three forms in a single session.

### The vertical slice, and an answer that has to be an interval

Three filed sources, two identifier joins, no names: 13F holdings → ISIN-LEI →
GLEIF entities, answering *what is the country exposure of this filer's
portfolio*. World built in **5.8 s**; **~260 µs** per portfolio. Most positions
have unknown domicile, so *"of the ones we know, X% are US"* would quote a
conditional as a share. `additive_bounds` returns **exact attained extremes**,
and the lower bound carries a **witness** a reader checks by following two joins
per position.

| US exposure, value-weighted | p10 | p50 | p90 | band ≤ 20 points |
|---|---:|---:|---:|---:|
| interval width | **8.7%** | 42.1% | 88.2% | **25.2% of filers** |

Value-weighting **doubles** the usable share (13.4% → 25.2%) and makes the worst
cases worse (p90 71.0 → 88.2), because one large unbridged position dominates a
portfolio that equal weighting had diluted. **One filer in four gets a band tight
enough to act on.** Honest uncertainty rather than a point estimate that would
have been a lie — and not yet a product.

### And the sentence the whole session was working toward

The bounds are wide because an unbridged position could be anywhere. The
**identifier format** constrains it: a 9-character CUSIP is assigned to US and
Canadian issuers, and foreign issuers get a **CINS** number beginning with a
letter. 89.4% of held CUSIPs are digit-leading. Checked where ground truth
exists, digit-leading CUSIPs resolve to US or CA **89.1%** of the time — the leak
being US-listed foreign issuers and **Cayman**-domiciled holding companies (KY
115, GB 127, JP 76) whose parent domicile is what GLEIF records.

> **The format carries real information and not enough to bound.** A rule that
> fails one time in nine produces intervals silently wrong 11% of the time —
> exactly the lie the interval exists to avoid. An apparatus built on *exact
> attained extremes* has no place for an 89% regularity.

**So: structure in an identifier does real work for free, and not the work
exactness needs.** Where the product is a **guarantee** rather than an estimate,
an 89% regularity is unusable. That is a narrower and more defensible statement
of what this substrate is for than "cheaper than neural inference", and it is
what the cost work and the federation work agree on: **exact answers with
certificates, at `1/f` the price, where `f` is how much of the workload your
structure covers.**

### How the arm ends: an uncertain input must not collapse a certain output

The bound was honest and usable for **23.7%** of filers. `additive_bounds` has
always reported *where the width comes from* — `Bounds.width_by_subject`, widest
first — and the slice ignored it. Settling unbridged positions widest-first, the
**five widest carry 57.5%** of the width, and ten escalations put **77.5%** of
filers inside a 20-point band for **$0.045**.

**That product was illusory, and the check that killed it is the one the arm was
built to make.** It reported *usability* and never *truth*. Tested on the bridged
subset where the answer is known, a band narrowed by `k` lookups of accuracy `a`
still contains the truth only:

| lookup accuracy | k=0 | k=10 | k=20 |
|---:|---:|---:|---:|
| 1.00 | 100% | 100% | 100% |
| **0.95** | 100% | **63.3%** | 42.3% |
| 0.90 | 100% | 40.7% | 17.1% |

**Coverage tracks `a^k`** — 0.95¹⁰ = 59.9% against an observed 63.3%. Any single
wrong lookup breaks the band, because the policy resolves *widest-first* and one
error displaces the band by that position's full weight. **The concentration that
made the product cheap is what makes it fragile.**

**The fix is this file's own ethos rather than a new mechanism.** Treating a
lookup as having *settled* a position is exactly the collapse the ambiguity
machinery exists to refuse. If at most `m` of `k` lookups are wrong, widen both
ends by the `m` largest resolved weights:

| m | coverage | median band |
|---:|---:|---:|
| 0 *(naive)* | 63.3% | 10.4% |
| **1** | **96.9%** | **23.7%** |
| 2 | 100.0% | 28.7% |

So at the same $0.045: doing nothing is a **43.5%** band always true; naive
resolution is **10.4%** and true 63% of the time; **widening for one error halves
the band to 23.7% and stays true 96.9%.** `additive_bounds` needed no change —
only the right input.

> **An uncertain input must not collapse a certain output.** That is the
> sharpest thing the federation arm produced, and it was reached by attacking
> each previous step: an honest-but-unusable bound, an attribution that made it
> cheap, a check that showed the cheap version false, and a construction that
> recovers most of the gain while keeping the guarantee.

**And it raises the blocker's priority.** The band's reliability is `a^k`, and
`a` — the accuracy of a real model on this lookup — is unmeasured, because the
comparison is still blocked on credentials (`ROADMAP.md` 0b). That blocker now
bites a **product** claim, not only a cost row.

Scripts: `bridged_join.py`, `vertical_slice_country_exposure.py`,
`bound_attribution.py`. Notes: the 2026-08-18 findings under
`three-sources-two-joins-...` and `the-advantage-is-a-property-of-provenance-...`.

## Awaiting independent challenge — the promotion queue

`notes/` promotes into this file **only once something independent has tried to
break the finding**, because this repo has had author-designed controls pass
while being hollow. Four results are currently strong, measured on the full
curriculum, and **not yet in this file on purpose**. They are listed here so the
queue is visible rather than implicit — a finding nobody knows is waiting is a
finding that never gets challenged.

| finding | what it claims | what would promote it |
|---|---|---|
| ~~graph-derived roles~~ | — | **PROMOTED**, above. All four load-bearing conclusions survived an independent attack; the headline moved *up* 0.053 once the bandwidth was fitted rather than pinned at its grid's edge. Four of the refuter's five written predictions were refuted, all in the finding's favour. |
| the dimension / throughput curve, same note | quality saturates at **d = 1,024** for every construction and the last 64x buys nothing; `vsa_sum-004` at d = 256 matches `vsa-002` at d = 4,096 on accuracy at **17x the throughput** | **still queued, and it needs a quiet machine.** The quality half survived: one arithmetic claim, "all three decline slightly", is wrong — `vsa-002` *rises* 0.2146 → 0.2180 from 1k to 64k. The right statement is that all three move by ≤0.004 in either direction, which is the saturation the section claims. The throughput half was not re-measured: the box was at load 35 and a contaminated pass read `vsa_sum-004` at 1,391 tok/s against a published 18,995 |
| ~~the action readout~~ | — | **PROMOTED**, above. Attacked by an agent that did not write it; both named confounds run, plus a third nobody had named; the gap grew from 0.4229 to 0.4320 as they were removed. Its own interpretation was corrected in the process and a slice finding it rested on was refuted. |
| `notes/findings/2026-08-13-one-parser-over-word-classes-transfers-the-class-identities-do-not.md` | over 46 WALS-coded languages, abstraction transfers and the induced class *identities* are a liability held out; `Treebank.coverage` predicts held-out transfer at **r = +0.886** and survives partialling out script and untranslated share | a second, independent handle on coverage — the one intervention tried moved bracket F1 by +0.002, which is not enough to call a +0.886 correlate a passenger. See `notes/questions/2026-08-14-a-second-handle-on-treebank-coverage.md` |

| ~~the copy lead~~ | — | **PROMOTED**, above. Survived an independent attack that eliminated three artefact hypotheses — same scored key lists, back-off provably absent from the pointer, leads 5/5 draws including fresh episodes. The *improvement* did not survive: quoted against the wrong baseline, the atomspace-specific increment is **+0.0165**, not +0.049. The attack also found a denominator mismatch in `copy_ceiling` affecting every copy number in this file. |

| `notes/findings/2026-08-18-a-query-pays-for-the-conflicts-it-reads-and-4992-of-them-cost-one.md` | a query over a world holding 4,992 unresolved conflicts reads a median of **0** and a max of **1** of them; 117,129 answers in 0.3s where whole-world enumeration is refused (2^4992); `additive_bounds` matched enumerated extremes 3,273/3,273 | an independent reader tracing `possible_answers_scoped`'s read-set closure loop. The anchor (410/410 against full enumeration on an 8-conflict sub-mixture) is author-designed, and this repo has had author-designed controls pass while hollow — one in this very batch did |
| `notes/findings/2026-08-18-the-advantage-curve-was-mostly-the-framing-and-what-is-left-is-a-constant.md` plus its same-day correction | the ~5e7 constant, and the three factors any advantage figure must now name | ~~a second corpus~~ **DONE**: prose moves the *dependency* 7.4× (41 → 302.3 tokens) and the crossover does not transfer at all (99,512 → 5,242), because it scales with corpus size. Now superseded by the `1/f` section above |
| the certificate arm — `the-certificate-is-worth-nothing-per-quarter-and-1342x-per-filing`, `an-optimum-is-two-claims-...`, `a-witness-grows-linearly-...` | a read-set certificate is worth 0.3–1.0× per quarter and 37×–1,342× per filing, with `advantage <= 1/P_hit` and `P_hit ~ r × keys_per_update / total_keys`; an optimum's witness half is 93× cheaper to keep than its optimality half, narrowing to 72× on a shrinking corpus | **an independent reader.** Every control here is author-designed and two of them failed on first run *in ways that flattered nothing* — but this repo has had author-designed controls pass while hollow. The specific thing to trace: whether the recorded read set is the *dependency* or the *search order*, since it over-approximated by 6,591× on one problem and was exact on another, with nothing in the mechanism distinguishing them |
| `notes/findings/2026-08-18-a-zero-shot-registry-beats-a-learned-dictionary-and-both-plateau-at-62-percent.md` | a zero-shot ROR lookup beats a dictionary learned from 3,500 works on all three splits, at half the cost, with nothing to tune | **a second registry-backed task.** The claim "external resources are givens" is this repo's own principle and this is its first real test; one task is not a validation of a principle |

The one thing the queue must not become is a parking lot for results nobody
intends to challenge. A finding that sits here unchallenged is not "pending"; it
is unverified, and should be read that way.

## What is shaky

- **Every neural number is a lower bound.** All four re-run networks were still
  gaining more than +0.01 per 500 steps when the 2000-step budget ran out; `rgt`
  was accelerating. The family comparison is unsettled and says so.
- **`workspace`'s joint-first label placement is mostly vocabulary.** Uncapping
  its training examples raised original accuracy 0.273 -> 0.352 and renamed
  accuracy only 0.214 -> 0.221. About 91% of that gain does not survive a
  renaming.
- **`corefer` is mine and it leads its own table.** It was built while the
  metrics it leads on were being built. Nothing in it reads eval, and the
  candidate-selection choices were made on a held-out slice of *training*
  episodes, but a reader should weight it accordingly.
- **The marginal-likelihood pointer did not beat naive Bayes at pointing.**
  `ptrgen` and `corefer` share stage-one features exactly, and `ptrgen` trains
  on the marginal likelihood of any correct antecedent where `corefer` asks a
  yes/no question of each pair. Copy lift: **+0.078 against +0.096**, label
  accuracy 0.336 against 0.357. The objective is better posed — several nodes
  usually carry the right label and nothing says which was meant — and it does
  not win on argmax. What it wins on is bits, by a full 1.04, and that is the
  gate and the summed label distribution rather than the pointer.
  `corefer` also has a second-stage reranker and `ptrgen` has none, which is the
  obvious confound and the obvious next experiment; until it is run, no claim
  should be made that the training objective is what separates them.

## What was believed and is false

Each of these was in the README as a result:

| claim | what it actually was |
|---|---|
| "The curriculum invents vocabulary per episode" | 100% of scored labels recur in training |
| "No rule-based model clears the floor" | an artefact of a six-lesson slice; on 179 nearly all do |
| "All neural models beat the label floor, no symbolic one does" | both halves wrong |
| "gru is beaten at -0.050" | it was undertrained at 1.3 passes; +0.079 at 8.9 |
| "rgt is first of nineteen on type at +0.587" | measured against a floor 0.065 too low; +0.395, and below a counting baseline |
| "Every rule-based model clears the label floor" | `ctw` and `synth` do not |
| "Every rule-based model sees the training set in full" | `ilp` saw 1.1% of available examples |
| "The mask rate moves the opportunity, not the ability" | half true: nothing is reconstructed, but `acc \| copyable` is a mixture the mask rate reweights, and `copy_lift` falls for six of six pointer models and is negative by 0.60 |
| "The render is deterministic, so `exact_match <=` graph exactness" | determinism gives `>=`; an upper bound needs injectivity, and a third of hidden symbols never reach the page |
| "The advantage curve spans seven orders of magnitude; 1.85e11 on ultimate parent" | the arithmetic is right and the **framing** carries it: 99,738x of that row was handing the model the whole graph. Priced against an opponent given only what the query depends on, four query classes land within **1.2x** of each other at ~5e7 |
| "A retriever can only guess what an answer depends on" (asserted and refuted the same day) | an ideal retriever certifies determinacy in **<=4 rounds** with zero misses. What survives is that it has no *stopping rule* — silently wrong on 1.128% of the world at its natural stop — and over-fetches **46x** |
| "Ambiguity does not propagate in this graph, amplification 1.0x" | true of the 251 conflicts that occurred, false of the graph. The same conflicts on the highest-exposure nodes contaminate **102x** more; exposure spans 1 to 3,848 inside one relation |
| "Alternatives are retained, not collapsed" | held only inside the process. `FusionResult.to_dict` carried a count and dropped the competing claims, so retention died at the artifact boundary |
| every cost ratio in this file, quoted without a regime | the arithmetic stands; the framing does not. They are `1/f` evaluated where structure is **filed**. On a **derived**-structure task the same formula gives **1.8×** at 0.85 quality |
| "the advantage is 1.1M×–2.5M× per answer above floor" (this file, hours earlier) | true only at `f = 0`, i.e. at **52.6%** quality. Escalating even the 12.3% of cases the extractor cannot touch collapses it to **8.1×**. `cost.py`'s own docstring said so first: *cheap-and-incapable is not a point on the cost curve* |
| "abstention beats guessing" (concluded three times in one day, on fact-level evidence) | true at the fact level, **backwards at the system level**. An abstaining extractor builds a world with half the entities, and aggregate queries pay for *completeness*: the extractor that wins on facts by 0.121 F1 loses on every aggregate query |
| "F1 0.717 is a ceiling the affiliation task imposes" | **my own task construction.** The fetcher flattened authorships, labelling each raw string with every institution its author listed. Grouped correctly the ceiling is **0.988** — the label *is* a function of the input — and the shortfall is genuine extraction failure, not label noise |
| "the witness/complement asymmetry is a new axis, two arms converging" | **four** observations, and two predate the session: a witness verifies **247×** cheaper than solving and an optimality certificate **2.0×** *dearer* than re-solving, both already in `notes/findings/`. `HANDOVER.md` §3 omitted them, which is how the claim got made |
| "bridge, then names where it misses — f 11.4%, 8.8×" (mine, one cycle later) | **invalid.** It multiplied the *coverage* of the CUSIP→LEI join by the *ambiguity* of the CIK→LEI **name** join. Different joins over different entity types, and a CUSIP has no name to fall back to |
| "the crosswalk closes the 68× cliff" | acquired, and it buys **1.29×**. The bridge converts an ambiguity problem into a **coverage** problem, and coverage is larger. The cliff is not the absence of an identifier but the absence of one that **covers the workload** |
| "geography disambiguates entity linking" (promoted to the top of the roadmap on five printed examples) | **it does not.** Three constructions, all at or below abstaining (−0.036, −0.007, −0.001); geography recovers 81% of the damage that admitting ambiguous candidates does and never gets ahead. 65% of ambiguous components carry no geographic evidence at all |

The pattern is worth naming: **six-lesson slices and weak floors both produce
confident results with the wrong sign.** Three separate conclusions inverted when
moved from six lessons to 179. The last two rows add a third mechanism —
**a conditional that the manipulated knob redefines, and a bound quoted in the
direction that closed the question** — both recorded in `notes/lessons/`.

## How to add a variant

Register it beside its predecessor rather than editing in place:

```python
@register("corefer-002", doc="...")      # leave corefer-001 registered
```

Then `sweep --models corefer-001,corefer-002` prints both rows against the same
floors, and the difference is a measurement rather than a claim in a commit
message. Name the suffix for what changed when that reads better —
`corefer-noprose` says more than `corefer-003`.

This exists because the alternative was tried and cost real results. `corefer`'s
type head went 0.174 -> 0.612 in one commit and `workspace` moved from eighth to
joint first when a cap was raised; both were improvements, and both silently
redefined what an earlier published row had meant.

## Open questions

- Can anything reach the 0.722 copy ceiling? Four candidate-level features in a
  row have failed, and a discriminative re-ranker was worse than counting.
  `ptrgen`'s marginal-likelihood pointer is the fifth thing to not help, at
  +0.078 copy lift against `corefer`'s +0.096. The first thing that *did* move
  a pointer a long way is `vsa_perm-002`, and it moved it from far below the
  floor to +0.060 — still third of the pointers, so the ceiling is untouched.

  **Update: something is now first, and the ceiling still stands.**
  `metta_perm_pure-005` reads **+0.1091** against `corefer-001`'s +0.0959, which
  is the first time in this repo's history anything has led the pointer. It is
  0.346 of a reachable 0.722, so **more than half the signal is still untouched**
  and the question is unchanged in substance; what died is only "nothing has ever
  been first". Not promoted — it was not pre-registered and is under challenge.
- ~~**The type head is the last one nothing has attacked.**~~ **Attacked, and the
  finding is that it was saturated rather than unattacked.** `metta_type-005`
  reads what a node *contains* — a direction no key here has ever had — and moves
  type lift from −0.486 to **−0.285**, the largest movement any VSA-family row has
  shown, while still sitting 0.285 *below* the floor. Design rule 1 held: label,
  label-bits and copy are identical to four decimals across that move. A
  six-level backed-off ladder over tree shape is simply very good, and the open
  question is now the sharper one — **is anything except tree shape worth
  anything on this head at all?** Two of nineteen models are positive on type.
  The original text follows, because it is what the attack was aimed at:
  every VSA row sits at
  -0.486, unchanged since `vsa-002`, because the family's type vote is a
  four-feature lookup and the floor is a six-level backed-off ladder. Two of
  nineteen models are positive on type. Design rule 1 says the heads do not share
  machinery, so the fix cannot be "point the label pointer at it" — `corefer`
  already tried that and paid 0.174 -> 0.004.
- **Put a reranker on `ptrgen`.** The cleanest open experiment in the sweep.
  `corefer` beats it on copy by +0.018 and has a second stage it does not; every
  other part of stage one is shared. Until that is run, "naive Bayes points
  better than marginal likelihood" is confounded with "two stages beat one".
- **Which metric should the repo lead with?** `ensemble-001` is first by bits
  and ninth by accuracy; `corefer` is the reverse. The two columns are now both
  printed and nothing decides between them. They are not interchangeable
  summaries of one quality — bits is a proper scoring rule and accuracy is what
  the curriculum's own multiple-choice question asks — so the answer is probably
  "both, always, and never one alone", which is what `compare` now does.
- Is the accuracy/bits frontier a property of the mixture or of the models? The
  interface forces a scalar `c` over a shared support. A model emitting a full
  distribution would not face the trade-off, and none exists here to check with.
- A probit link for `ScoreCalibrator`, as a data-efficiency variant rather than
  a multiple-truths one. See design rule 4 in `ROADMAP.md`.
- Does a parser beat a regex? `corefer` reads prose by counting regex matches,
  and the parser layer — built, tested, scored — has never been tried inside the
  one model where prose demonstrably helps.
- What budget would settle the neural comparison? Parked; it is a control.
- **Can anything beat `retrieve-001` by more than the refill step does?** On the
  `str -> Graph` task a lookup with no parsing in it reaches 0.758 label F1 and
  the best parser reaches 0.832. Until something opens that gap, "parsing this
  curriculum" and "recognising which of 179 lessons this is" are the same
  measurement, and the second one is not interesting.
- **Exact graph recovery is 0.016 at best.** Every other number in the parser
  table is partial credit. Nothing here has actually parsed an episode.
- **Is `template-002`'s Chinese score grammar or is it punctuation?** It keeps
  0.60 of its English label F1 across a full script change, on punctuation
  counts and line structure alone. That is either a real structural signal or a
  fingerprint of 179 distinct document layouts, and the two are distinguishable:
  render with the layout perturbed — bullets to numbers, semicolons to newlines —
  and see whether identification survives. It has not been run.
- ~~Nothing has tried to *build* a graph rather than retrieve one.~~ Done:
  `cky-001`, `lr-001` and `shiftreduce-001` compose one from an induced grammar,
  and all three lose to `retrieve-001`. The open question it turns into is
  sharper: **can a compositional parser beat a lookup on this corpus at all, or
  is 179 templates simply a corpus where recall is the right algorithm?**
- **A grammar over word classes, not word forms.** The compositional parsers are
  the most language-bound things in the package — `cky-001` keeps 0.06 of its
  English bracket F1 in Chinese where `template-002` keeps 0.46 — because a
  production's right-hand side is keyed on literal words. Replacing those with
  induced classes (which is what `symbolic_ai_models/parsers/` produces, and the
  one place the two packages might genuinely meet) is the obvious repair and has
  not been built.
- **The treebank's 21% miss is unexamined.** Clause alignment finds a span for
  79% of clause-shaped nodes. Nothing has looked at which fifth it loses or
  whether they are systematically one kind of lesson, and every classical score
  is capped by it.
