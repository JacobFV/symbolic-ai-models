# How we are approaching this

`README.md` documents the harness. `RESEARCH_LOG.md` says what is known.
`ROADMAP.md` holds the working rules. This file says **what we are trying to do
and why the work looks the way it does** — because from the inside it looks like
a lot of unrelated models, and it is not.

## The objective, stated so it can be checked

**Low-cost, low-latency language understanding.** Concretely: something that can
serve ultrafast agents, or stand as an LLM alternative at around **$1 per billion
tokens**.

That number is worth taking literally, because it tells us which constraint is
binding. Measured on one CPU core in this repo:

| model | tokens/sec |
|---|---:|
| `omegaclaw_ctx-001` | 235,685 |
| `ptrgen-001` | 210,864 |
| `corefer-001` | 156,960 |

At ~200k tokens/sec, a billion tokens is about 1.4 core-hours — a few cents on
commodity CPU, i.e. **15–30 billion tokens per dollar**. We are already 15–30×
past the cost target.

**So cost is not the constraint. Capability is.** Every model here is cheap and
none of them can yet write a coherent paragraph. That single fact should govern
how effort is allocated: optimising throughput is not the work, and a method that
is 10× slower but actually understands something is a trade we take instantly.

## Why a portfolio, and not a bet

No method here has the answer, and several partial answers are each doing real
work. That is not indecision — it is the honest state of the field this repo is
re-opening. Count-based, grammar-induction, case-based, first-order, vector-
symbolic and pointer methods each capture something the others miss, and the
measurements keep saying so:

- Ranked by **accuracy** the pointer models lead; ranked by **bits** the counting
  models lead. The two orderings are close to inverse. Neither column is "the"
  answer.
- The best density estimator we have (`ensemble-001`, 4.77 bits) is **not a
  symbolic model** — its gain is vocabulary memorisation and dies under renaming.
- The best structural reasoner we have (`vsa_perm_pure-002`) is exactly
  equivariant and still loses to memorising on absolute score.

A portfolio is the correct response to that, and the discipline that makes a
portfolio honest is a **scoreboard that cannot be gamed** — every number against
a fitted floor, every gain against a control that could fail, every claim checked
under renaming. Keep trying everything; keep the scoring merciless.

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
| parsers (`symbolic_ai_parsers`) | text → graph, the inverse of the generator | nothing has actually parsed: best exact recovery 0.016 |
| seeding (`synthex_*`, `template-lex`, `vsa_seeded`) | import structure instead of re-deriving it | three independent nulls so far; balance untested |

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

`OmegaClaw.weigh(name, ctx, claim)` is already this shape and already measured —
extending `perceive` to carry language and partial parse state is the cheapest
real test of the idea. It makes a falsifiable prediction: **cluster languages by
their per-rule reliability vectors and see whether the clustering recovers actual
language genealogy.** If it does, the system learned grammar rather than seven
lookup tables.

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
learning and must not appear in the hot path. This is what makes the cost target
easy: the VSA's only dense step is a projection that runs once at fit, and
inference is elementwise operations over one vector.

## What we keep being wrong about, and the guards

The failures repeat, so the guards are structural rather than intentional:

- **Small slices invert results.** Seven times now. A slice may form a hypothesis
  and may never appear in a report.
- **Self-authored controls pass while hollow.** A result with only its author's
  controls is provisional until something independent tries to break it.
- **The harness moves more than the models.** Models span ~0.1 lift; shared
  components span 0.15–2.0. Suspect the substrate first.
- **A ranking is a property of a metric.** Quote accuracy, bits and renaming
  together, or say which one you chose and why.

See `notes/` for the running notebook, and the memory files for these lessons in
the form that survives a fresh session.

## The honest position on timeline

A purely symbolic system matching a modern LLM on open-domain freeform text is
not something the evidence supports promising. The field spent roughly two
decades on count-based language models with far more resources than this project
has, and the gap that ended the era — generalisation across *similar* contexts,
which discrete backoff cannot do and embeddings can — is still the gap.

What the evidence does support: structured domains, hybrid designs where a small
learned component supplies the interpolation and a large symbolic memory supplies
everything else, and the possibility that a method nobody has tried at this scale
works better than the ones that were. That is why the portfolio stays open, and
why the scoreboard stays strict.
