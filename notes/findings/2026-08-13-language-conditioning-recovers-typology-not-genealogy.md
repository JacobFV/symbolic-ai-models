---
date: 2026-08-13
author: agent-omegaclaw-lang
status: provisional
related: [2026-08-13-language-conditioning-preregistration,
          2026-08-13-selective-rule-application-by-language,
          2026-08-13-language-id-above-the-parser]
---

# Rules do have per-language reliabilities. They cluster by orthography, not by descent — and conditioning on them buys nothing

Full 179-lesson sweep, `configs/full179_multilingual.toml`, all seven renderable
packs over the same seeds, `runs/full179_multilingual`. Not a slice. Every
hypothesis below was written into
`notes/decisions/2026-08-13-language-conditioning-preregistration.md` before any
model was fitted.

## The short version

1. **Per-rule reliability really does vary by language, strongly.** Real mean
   pairwise distance between languages 0.328 against a shuffled-label control of
   0.070 +- 0.007 — **4.7x, and 33 control standard deviations clear.**
2. **The clustering does not recover genealogy.** The one real family here
   (Indo-European) ranks **10th of 20** possible triples: exactly the median, a
   coin flip. Spanish's nearest neighbour is Chinese. Swahili's is Turkish.
   `symbols`, which is not a language, sits next to English.
3. **Conditioning the model on the language buys nothing.** Net of what a
   *meaningless* partition of the same shape buys, the value of knowing the
   language is +0.006 label lift with the shared fallback and **+0.001 without
   it**.
4. **The sign of the language effect is set by the shared memorising fallback,
   not by the model.** With it, `lang` beats `ctx`; without it, `lang` loses to
   `ctx`. Same models, same corpus, opposite conclusion.

The commissioning note put it exactly right in advance: *"Arbitrary clustering →
rules are being fitted per language independently and conditioning bought
nothing bucketing would not."* That is what happened, and both halves of it were
measured rather than one being inferred from the other.

## The premise, and why it decided most of this in advance

`Lesson.structured(seed)` takes no language. Over all 179 generatable lessons x
3 seeds x 7 packs, the term graph is byte-identical in every pack — 537 of 537
episodes each. The eleven claws in `omegaclaw.base.CLAWS` read only the graph.

So a graph-only rule has the same reliability in every language **by
construction**, and the commissioned experiment was guaranteed null on the
standard claw set before it was run. That is arithmetic about the corpus, not a
result about a model, and calling the resulting null "the model failed to learn
grammar" would be a category error. The node task has exactly one
language-varying channel: `GraphView.text`, the rendered prompt. Three
surface-coupled claws were added to reach it, in
`symbolic_ai_models/models/omegaclaw/surface.py`.

The measurement confirms the premise from the other side, and it is the sharpest
number here: **99.05% of the between-language variance in the reliability
vectors sits in the three surface claws, 0.95% in the eleven graph claws.**

## The sweep

179 lessons, 20 train / 4 eval episodes per lesson per pack (25,060 training and
5,012 evaluation episodes), evaluation seeds from 1,000,000, CPU. Label floor
0.150, copy ceiling 0.714, type floor 0.864 throughout — every row shares them.

| model | claws | context key | lbl acc | lbl lift | bits lift | typ lift | rename |
|---|---|---|---:|---:|---:|---:|---:|
| `omegaclaw_flat-001` | 11 graph | structural (unused) | 0.2534 | +0.1216 | +0.1014 | -0.3707 | +0.0374 |
| `omegaclaw_ctx-001` | 11 graph | structural | 0.3442 | +0.2284 | +0.1460 | -0.3051 | +0.0180 |
| `omegaclaw_const-002` | 11 graph | + a constant | 0.3442 | +0.2284 | +0.1460 | -0.3051 | +0.0180 |
| `omegaclaw_split-002` | 11 graph | + a random 7-way bucket | 0.3432 | +0.2272 | +0.1472 | **-0.1788** | +0.0248 |
| `omegaclaw_lang-002` | 11 graph | + the language | 0.3486 | +0.2336 | +0.1476 | -0.2196 | +0.0238 |
| `omegaclaw_text-002` | 11 + 3 surface | structural | 0.3514 | +0.2370 | **+0.1789** | -0.3151 | +0.0218 |
| `omegaclaw_textlang-002` | 11 + 3 surface | + the language | 0.3519 | **+0.2375** | +0.1793 | -0.1930 | +0.0251 |

The same seven with `structural_fallback` off — the shared lookup table that
memorises the commonest label per structural context, which every rule-based
model here inherits and nobody attributes anything to:

| model | lbl acc | lbl lift | bits lift | typ lift | rename |
|---|---:|---:|---:|---:|---:|
| `omegaclaw_ctx_pure-002` | 0.3389 | +0.2222 | +0.1282 | -0.3051 | **-0.0003** |
| `omegaclaw_const_pure-002` | 0.3389 | +0.2222 | +0.1282 | -0.3051 | -0.0003 |
| `omegaclaw_split_pure-002` | 0.3357 | +0.2185 | +0.1292 | -0.1788 | -0.0003 |
| `omegaclaw_lang_pure-002` | 0.3366 | +0.2195 | +0.1296 | -0.2196 | -0.0001 |
| `omegaclaw_text_pure-002` | 0.3438 | +0.2280 | +0.1613 | -0.3151 | -0.0004 |
| `omegaclaw_textlang_pure-002` | 0.3423 | +0.2262 | +0.1615 | -0.1930 | -0.0008 |

### What each contrast says

**The plumbing is free.** `const-002` reproduces `ctx-001` to every printed
digit, with the fallback and without it. A constant appended to a context key is
a bijection on cells, so this had to hold; it is printed because the check is
cheapest where the numbers are, and because it licenses reading every other
difference as the partition rather than the wiring.

**The shared fallback decides the sign.** `lang` versus `ctx` is **+0.0052**
label lift with the fallback and **-0.0027** without it. Two defensible
contracts, opposite answers, same models — and the pure rows are the ones that
describe the model's own reasoning, where the pre-registered prediction (a
partition on an uninformative variable must cost something) holds. This is the
repo's standing lesson arriving again: suspect the harness before the
architecture.

**Most of what looked like a language effect is the shape of the partition.**
`omegaclaw_split-002` splits the evidence seven ways on `crc32` of the prompt —
same shape, no meaning. It reproduces most of the label movement, and on the
type head it **beats the language**: -0.179 against `lang`'s -0.220, where the
unsplit key is -0.305. The type-head gain that reads as "the language paid off"
is bought better by a bucket that means nothing.

Net of it, knowing the language is worth **+0.0064** label lift with the
fallback and **+0.0010** without.

**H4, the actual experiment, is refuted.** `textlang` minus `text` — the same
fourteen claws, the reach held fixed, only the language added — is **+0.0005**
with the fallback and **-0.0018** without. The difference-in-differences that
subtracts the partition cost measured on the graph-only pair gives **-0.0047**
and **+0.0009** respectively. Zero, from either direction.

**H3 is refuted too, and in the more interesting direction.** The three surface
claws were expected to be worth ~0, because `omegaclaw_reach-001` added the most
reliable single claw ever measured here and still lost. They are worth **+0.0086
label lift and +0.0329 bits lift** (+0.0058 and +0.0331 without the fallback).
The bits gain is four times the accuracy gain — the surface claws are mostly
improving the *distribution*, not the argmax, which is a distinction the
accuracy column cannot show and this repo has been bitten by before.

**Renaming equivariance holds exactly, including for the surface claws.** Every
pure row is within 0.0008 of zero drop. The 0.018-0.025 drops on the
fallback rows are the shared memorising table and nothing else. The surface
claws are pointer-valued by construction — they use the prose only to choose
among structurally admissible nodes, and return that node's own label — and the
gate confirms it.

## The clustering, and its controls

Vectors: for each language, every claw's firing rate and every claw's hit rate,
taken from `omegaclaw_textlang-002`'s own fitted `claw_evidence` (28,000
observations, 3,900-4,100 per language). `scripts/language_clustering.py`
re-derives the table and **asserts it reproduces the fitted model cell for cell**
before computing anything.

**Control (H6): passed, decisively.**

| | mean pairwise distance |
|---|---:|
| real | **0.3281** |
| episode-level language labels shuffled (n=100) | 0.0701 +- 0.0072, max 0.0844 |

The shuffle is exact rather than resampled: permuting labels cannot change which
claws fired on which node, only which bucket the records land in, so all 100
controls run against identical observations. Real is 4.7x the shuffled mean and
33 standard deviations above it. **There is a large, real per-language signal.**

**Average-linkage dendrogram:**

```
0.0329   english | english_synonym
0.0570   swahili | turkish
0.0970   english+english_synonym | symbols
0.1260   english+english_synonym+symbols | swahili+turkish
0.2450   chinese | spanish
0.5605   chinese+spanish | everything else
```

**Genealogy (H5): refuted.** The Indo-European triple
{english, english_synonym, spanish} ranks **10 of 20** triples by mean
within-group distance — the exact median. Nearest neighbours:

| language | nearest | | |
|---|---|---:|---|
| english | english_synonym | 0.033 | same language, as predicted |
| english_synonym | english | 0.033 | |
| swahili | turkish | 0.057 | Atlantic-Congo -> Turkic |
| symbols | english | 0.090 | a notation next to a language |
| chinese | spanish | 0.245 | Sino-Tibetan -> Indo-European |
| spanish | chinese | 0.245 | **the one relative English has, furthest from it** |

**What it recovers instead**, and this was registered as H5b before fitting:
the share of graph labels that survive verbatim into the prose.

| pack | verbatim label rate | dendrogram position |
|---|---:|---|
| symbols | 0.978 | with english |
| english | 0.808 | |
| english_synonym | 0.808 | |
| swahili | 0.693 | with turkish |
| turkish | 0.650 | |
| spanish | 0.498 | with chinese |
| chinese | 0.285 | |

The clustering is monotone in that column. Spanish inflects nouns and adjectives
for gender and number, so a bare label stops matching; Chinese has no whitespace,
so `\b` finds no boundary. Swahili keeps the Latin script and a good deal of
untranslated English. This is the same conclusion `RESEARCH_LOG.md` already
reached from the parsers — *"script and tokenisation dominate the language axis,
not grammar versus vocabulary"* — arrived at independently, from a different
task, a different model family and a different metric.

## The oracle, priced

Both commissioning notes require a supplied signal to be scored as its own head
against its own floor. `scripts/language_id_head.py`, character-trigram nearest
centroid, fitted on training seeds and scored on 2,506 evaluation prompts:

| | |
|---|---:|
| accuracy | 0.8388 |
| majority floor | 0.1429 |
| lift | **+0.8119** |

chinese 1.000, symbols 1.000, spanish 0.986, turkish 0.972, swahili 0.958 —
english **0.377**, english_synonym **0.578**. 342 of the 404 errors are those two
confused with each other, which is not a weakness of the classifier: they render
511 of 537 prompts byte-identically. **Five of the seven packs cost nothing to
identify; one distinction is unobtainable from the surface and is an oracle in
the strong sense.** Any future result that leans on separating those two is
leaning on information the system could not acquire.

## Per-language decomposition, and why it settles nothing

`scripts/language_breakdown.py`, `textlang` minus `text`, on the same trees with
the same nodes hidden (the packs render the same seeds in the same order, so the
masking RNG walks identical positions and only the prose differs):

| en | es | zh | tr | sw | en-syn | sym |
|---:|---:|---:|---:|---:|---:|---:|
| -0.0021 | +0.0023 | +0.0034 | -0.0036 | -0.0075 | -0.0008 | -0.0040 |

The two languages where the surface claws are least reliable (Chinese, Spanish)
are the only two that gain, which is the predicted direction — and Swahili and
Turkish, in the middle, lose the most, which is not. At 716 episodes per language
the standard error is about 0.0066, so every one of these is inside one. **No
coherent pattern; read as noise.**

## What would have refuted this, and what still could

Registered in advance: H4 was to be refuted if `textlang - text <= 0`; it is
-0.0018 on the model's own reasoning. H5 was to be refuted if the reliability
vectors clustered no better than shuffled labels; they cluster far better, so the
*signal* claim survives and the *genealogy* claim dies on the rank statistic
instead. H2 was to be refuted if `lang` scored meaningfully above `ctx`; it does,
with the fallback on, and does not with it off — which is why the fallback
contrast is reported rather than one of the two chosen.

**What could still overturn it:**

- **Six packs is not a corpus for a genealogy claim, and no amount of care fixes
  that here.** `symbolic_ai_data` renders five natural languages, one of which is
  English twice. The thousand-odd derived grammars the registry advertises need
  `grammar/data/languages.db`, a 2 GB gitignored artefact that is absent. With
  that database built, this measurement becomes worth taking seriously; without
  it, "ranks 10 of 20" is the strongest statement available and it rests on four
  independent data points.
- **Three surface claws is a thin reach.** They were designed to pair a
  structural candidate set with a surface decision, which keeps equivariance but
  also keeps them weak — `text_first` hits at 0.012-0.043 everywhere. A richer
  surface reach might carry a language signal these three cannot.
- **The gain may be capped by what the fallback already answers.** Every contrast
  here is 0.001-0.009 wide against harness effects of 0.005-0.13 in the same
  table. Nothing was measured twice with a different seed; the pure rows are the
  cleanest contract available but they are still one run.
- **Nothing independent has tried to break any of this.** Status stays
  `provisional` for that reason and no other.

## What I could not settle

Why an *uninformative* seven-way split improves the type head by +0.13 lift.
`omegaclaw_split-002` says it is not about language, and the shrinkage in
`OmegaClaw.reliability` towards each claw's global rate is the obvious
suspect — thinner cells shrink harder, and the type head is the one that has been
overconfident since the family's first measured defect. But that is an argument,
not a measurement: a run with the smoothing constant varied on the unsplit key
would settle it in one sweep and was not done.
