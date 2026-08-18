# How we are approaching this

`README.md` documents the harness. `RESEARCH_LOG.md` says what is known.
`ROADMAP.md` holds the working rules. This file says **what we are trying to do
and why the work looks the way it does** — because from the inside it looks like
a lot of unrelated models, and it is not.

## What we are trying to build

**A language-understanding substrate whose cost per correct answer is a
different order of magnitude from neural inference, and whose reasoning is
inspectable rather than inferred.**

Not "a cheaper LLM". Cheapness is not the innovation; it is the *consequence* of
the innovation, and the two get confused constantly — including in earlier
versions of this file. The bet is that a large amount of what a transformer
spends parameters on is structure that can be *stated* — binding, coreference,
type discipline, relational chaining, compositional inventory — and that a
system which states it does not have to re-derive it from tokens at inference
time. If that is true, the cost collapse follows for free. If it is false, no
amount of throughput saves it.

This is a **frontier bet, not a benchmark chase.** Nobody has run the pure
symbolic direction at modern scale with modern tooling, so the failure mode to
avoid is not "we lose to GPT-5" — it is "we spent the year proving what was
already known". Every session should be able to name the thing it now knows that
nobody knew on Monday. A method that is 10x slower and actually understands
something is a trade we take instantly.

## The north star: $ per unit of useful capability

**Retired: tokens/sec.** This file used to lead with it — ~200k tokens/sec on one
CPU core, therefore 15-30 billion tokens per dollar, therefore "we are already
15-30x past the cost target". Every step in that chain is true and the
conclusion does not follow. What it established is

> cost(**the symbolic operations we currently run**) ≪ $1/Btok

and what it was read as saying — including by us — is

> cost(**a system with useful language capability**) ≪ $1/Btok

Those are different claims and only the first was ever measured. The gap is not
rhetorical. The best exact parse recovery in this repo is **0.016**; nothing here
turns text into a graph. A system that reached usefulness by putting a neural
semantic parser in front of the symbolic core would be priced by *that*
component, and a symbolic core that is free does not make a $0.30/Btok parser
cheaper. **Cheap-and-incapable is not a point on the cost curve. It is a point
off the capability axis.**

A metric that improves when you delete capability is not a north star; it is a
way to win an argument. So the north star is a **ledger**, not a rate:

| denominator | what it refuses to let us claim |
|---|---|
| `$ / 1B input tokens` | *(the old number, kept as an input)* |
| `$ / solved episode` | cheap per token, useless per answer |
| **`$ / solved episode above floor`** | cheap per answer the *floor* already bought |
| `$ / correctly recovered proposition` | cheap text-in, nothing understood |
| `ms / action` | cheap in aggregate, unusable live |
| `bytes / retained proposition` | cheap to run, ruinous to hold |

`symbolic_ai_core/cost.py` computes it and `symbolic-ai-models cost <runs>`
prints it. Two properties are load-bearing and are the reason it is code rather
than a paragraph:

**The floor divides the numerator.** The headline column divides by
`accuracy − floor`, so a system at or below its floor reads `inf`. That is the
correct entry, not a formatting bug. Sorting the table by `$/Btok` would put a
system that understands nothing at the top, which is the precise misreading the
module exists to prevent.

**Cost is charged to the system, never to the component.** A `System` is a list
of components — CPU components priced from a measured rate, API components
priced from a vendor sheet — and its cost is the *sum*. There is no accessor
that reports "our part is free". If the symbolic reasoner only works because
something upstream produced a graph, that upstream part goes in the ledger even
when it does not exist yet: `--parser-usd-per-btok 0.30`.

Running it today says something worth knowing. On the `both` sweep, **eighteen
of nineteen models cost infinity per answer above floor** — only `ngram` beats
the answer floor at all. That is the honest state of the programme and it was
invisible behind a throughput table.

**Throughput is still worth measuring.** It is an *input* to the ledger and never
the headline. And it must come from a deliberate quiet-box run: timing on this
machine measures the neighbours as often as the model (`scripts/vsa_dim_curve.py`
documents the 3.4x spread that taught us), so a row derived from a run's total
`seconds` is marked **NOT QUOTABLE** and may not appear in `RESEARCH_LOG.md`.

## What the benchmark has to become

The 179-lesson curriculum is a **development harness. It is not the benchmark**,
and it has been doing both jobs for long enough that its artefacts are being read
as findings. Its own README documents the reasons:

- **Only ~1.4% of scored language-modelling positions are the answer.** The rest
  is the question and fixed boilerplate — "Answer with exactly one of". A model
  can hold a large `token_lift` purely by reproducing scaffolding, and for most
  of this repo's history that is what the headline column was measuring.
- **Structural floors are strong**, and several published lifts turned out to be
  the floor being set too low rather than the model being good.
- **Two defensible metrics rank the models close to inversely** (`label_acc` vs
  `label_bits`). A ranking is a property of a metric; every early ranking here
  was an accuracy ranking that never said so.
- **Slices invert.** Ten times.
- **Teacher forcing.** Scoring the next token given the true prefix is not the
  regime any deployed use of this would run in.

None of that makes the curriculum bad — it is an unusually good *development*
instrument, because an episode is a pure function of its seed and the graph the
prose came from is exactly known. It makes it the wrong thing to *report* on.

**What the next benchmark must have**, stated so a candidate can be rejected:

1. **Episode-level scoring, not position-level.** One episode, one verdict. The
   fraction of scored positions that are the answer is 100% by construction, and
   `$ / solved episode` becomes computable rather than estimated.
2. **Free generation, not teacher forcing.** The model produces the answer from
   the prompt with no true prefix. Anything else is scoring a regime nobody runs.
3. **Structure the model did not generate.** Graded against something outside
   the generator being modelled. `derive:wordnet` already has this property and
   is the template: the attribute is *not drawn*, it follows from WordNet, so a
   model that copies cannot score.
4. **A floor built from every feature the model sees.** Not a weaker floor that
   makes the lift look larger. This is where more published claims here have
   died than anywhere else.
5. **Renaming invariance reported beside the raw score, always.**

Work that moves the benchmark toward those five properties outranks work that
moves a model up the existing table. A model that gains 0.01 on a harness we
have decided not to report on has bought nothing.

## Why a portfolio, and not a bet

No method here has the answer, and several partial answers are each doing real
work. That is not indecision — it is the honest state of a field this repo is
re-opening. Count-based, grammar-induction, case-based, first-order,
vector-symbolic and pointer methods each capture something the others miss:

- Ranked by **accuracy** the pointer models lead; ranked by **bits** the counting
  models lead. The two orderings are close to inverse. Neither is "the" answer.
- The best density estimator we have (`ensemble-001`, 4.77 bits) is **not a
  symbolic model** — its gain is vocabulary memorisation and dies under renaming.
- The best structural reasoner we have (`vsa_perm_pure-002`) is exactly
  equivariant and still loses to memorising on absolute score.

The discipline that makes a portfolio honest is a **scoreboard that cannot be
gamed**: every number against a fitted floor, every gain against a control that
could fail, every claim rechecked under renaming, and now every cost against the
capability it bought.

**What retires a method:** a measured null with its control, reproduced on the
full curriculum, written into `RESEARCH_LOG.md`. **What does not:** one slice, one
weak implementation, or a hunch. Three seeding nulls do not close seeding — they
say *this* seed, *this* way, at *this* data scale, did not pay.

## The methods in play, and what each is for

| method | what it is for | where it stands |
|---|---|---|
| counting (`ngram`, `ctw`, `grammar`) | density estimation, coverage | best on bits, worst on accuracy, vocabulary-bound |
| pointers (`corefer`, `ptrgen`) | binding — "which node do I corefer with" | best on accuracy; 71.9% of answers sit on a visible node |
| operator families (`omegaclaw`) | learning *which rule to trust where* | control beats reach: +0.107 for context-conditioning, ~0 for more operators |
| first-order (`ilp`) | relational chains, learned not enumerated | reaches novel routes 38% of the time, uniquely right on 2.2% |
| vector-symbolic (`vsa_*`) | graded, compositional, capacity-dense, cheap | exactly equivariant; +0.227 lift at 40s once permutation was added |
| parsers (`symbolic_ai_parsers`) | text → graph, the inverse of the generator | **nothing has actually parsed: best exact recovery 0.016** |
| seeding (`synthex_*`, `template-lex`, `vsa_seeded`) | import structure instead of re-deriving it | four independent nulls; balance now tested and it was not the mechanism |

The parsing row is the one to look at. It is the only seam with **no working
member in it**, it is upstream of everything else, and it is the component whose
absence makes the cost claim unfalsifiable. If a system here ever becomes useful,
the ledger says the parser is what it will cost.

## The design we are converging on

Not a single algorithm, but a small number of committed choices:

**1. Binding is the primitive, not classification.** The label task is a binding
problem scored as classification — most answers are already present in the
episode. Pointer-valued and role-filler methods are the ones that keep working.

**2. Selective rule application, conditioned — not bucketed.** A rule should fire
based on context, on the structure parsed so far, **and** on higher-level facts
about the situation such as which language this is. Languages share composition,
consolidation, abstraction and association rules through common descent, so one
parser per language throws that sharing away. One rule set, conditionally
applied, keeps it.

`OmegaClaw.weigh(name, ctx, claim)` is already this shape and already measured.
It makes a falsifiable prediction: **cluster languages by their per-rule
reliability vectors and see whether the clustering recovers actual language
genealogy.** If it does, the system learned grammar rather than seven lookup
tables.

**3. Higher mechanisms supply the situation; specialists consume it.** Language
identity is a fact about the situation, not about the string, so it belongs above
the parser — eventually as an in-context-learned signal rather than an oracle.
The caveat is permanent: **a supplied signal must still be measured as its own
head with its own floor**, or we have assumed away a subproblem instead of
factoring it out.

**4. Seed what exists; keep it learnable.** Re-deriving structure humanity has
already built is a cost, not a thesis. Take the codebook, the lexicon, the
concept layer from prior work where one exists — and keep every seeded component
replaceable by a learned one, because the point is to skip the re-derivation, not
to freeze the structure. Every seed ships with its from-scratch control, or we
cannot tell what it bought.

**5. Dense at fit time, sparse at run time.** Dense arithmetic is allowed while
learning and must not appear in the hot path. This is what keeps the *cost*
denominators small once the *capability* numerators become non-zero — the VSA's
only dense step is a projection that runs once at fit, and inference is
elementwise operations over one vector.

## What we keep being wrong about, and the guards

The failures repeat, so the guards are structural rather than intentional:

- **Small slices invert results.** Ten times now. A slice may form a hypothesis
  and may never appear in a report.
- **Self-authored controls pass while hollow.** A result with only its author's
  controls is provisional until something independent tries to break it.
- **The harness moves more than the models.** Models span ~0.1 lift; shared
  components span 0.15–2.0. Suspect the substrate first.
- **A ranking is a property of a metric.** Quote accuracy, bits and renaming
  together, or say which one you chose and why.
- **A cost is a property of a system.** Quote the ledger, or say which component
  you left out of it.

See `notes/` for the running notebook, and the memory files for these lessons in
the form that survives a fresh session.

## The honest position on timeline

A purely symbolic system matching a modern LLM on open-domain freeform text is
not something the evidence supports promising. The field spent roughly two
decades on count-based language models with far more resources than this project
has, and the gap that ended the era — generalisation across *similar* contexts,
which discrete backoff cannot do and embeddings can — is still the gap.

What the evidence does support, and what the work is actually aimed at:
structured domains where the answer is a binding rather than a continuation;
hybrid designs where a small learned component supplies the interpolation and a
large symbolic memory supplies everything else; and the possibility that a method
nobody has tried at this scale works better than the ones that were. That is why
the portfolio stays open, why the scoreboard stays strict — and why the
scoreboard now prices what it scores.
