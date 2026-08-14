---
date: 2026-08-13
author: agent-omegaclaw-lang
status: provisional
related: [2026-08-13-selective-rule-application-by-language,
          2026-08-13-language-id-above-the-parser]
---

# Pre-registration: what conditioning OmegaClaw on language can and cannot show

Written **before** any model was fitted, so the reading cannot drift towards the
answer already in the note that commissioned it. What follows is the design, the
hypotheses, and the fact that decides most of them in advance.

## The fact that reframes the experiment

`Lesson.structured(seed)` takes **no language**. Measured over all 179
generatable lessons x 3 seeds x 7 language packs (537 episodes per pack):

```
spanish          graph==english 537/537   prompt!=english 537/537
chinese          graph==english 537/537   prompt!=english 537/537
turkish          graph==english 537/537   prompt!=english 537/537
swahili          graph==english 537/537   prompt!=english 537/537
english_synonym  graph==english 537/537   prompt!=english  26/537
symbols          graph==english 537/537   prompt!=english 537/537
```

The term graph is byte-identical in every language. The eleven claws in
`omegaclaw.base.CLAWS` read **only** the graph. Therefore:

> **A graph-only rule cannot have a language-varying reliability.** Conditioning
> `perceive` on language partitions the evidence table into N copies of the same
> distribution. It is data-thinning with no information gained.

This is not a prediction about a model. It is arithmetic about the corpus, and
it means the commissioned experiment — cluster languages by per-rule reliability
and check against genealogy — is **guaranteed null on the standard claw set**,
by construction rather than by measurement. Reporting that null as "the model
failed to learn grammar" would be a category error.

The node task has exactly one language-varying channel: `GraphView.text`, the
rendered prompt, already carried through `collate_graph`'s `meta["prompts"]` and
already used by `GraphView.mentions`. So a live version of the experiment needs
**surface-coupled claws** — rules that consult the text — and the clustering has
to be read off those.

## What is being built

Six rows, one sweep, one corpus (`configs/full179.toml`, all 7 languages
rendered over the same seeds, episodes interleaved language-by-language so the
`max_examples` cap cannot see only English):

| model | perceive carries | claws |
|---|---|---|
| `omegaclaw_ctx-001` (anchor) | structural context | 11 graph |
| `omegaclaw_flat-001` (anchor) | structural context, unused | 11 graph |
| `omegaclaw_const-002` | context + a **constant** token | 11 graph |
| `omegaclaw_lang-002` | context + **language** | 11 graph |
| `omegaclaw_text-002` | structural context | 11 graph + 3 surface |
| `omegaclaw_textlang-002` | context + **language** | 11 graph + 3 surface |

`const-002` is the control the commission asked for: the extra context dimension
is present and carries no information.

## Hypotheses, and what refutes each

**H1 — `const-002` is bit-identical to `ctx-001`.** Appending a constant to a
tuple key is a bijection on contexts, so every count, every weight and every
prediction must be equal. *Refuted by any metric differing at all*, which would
mean the plumbing changed something it should not have.

**H2 — `lang-002` <= `ctx-001`, by a small margin.** Pure thinning: seven tables
of ~4k observations each instead of one of ~28k over the same distribution.
*Refuted if `lang-002` scores meaningfully above `ctx-001`* — which would mean
the corpus is not what the table above says it is.

**H3 — the three surface claws move the score by ~0.** The family has already
measured that widening the reach is worth ~0 (`omegaclaw_reach-001` added the
most reliable single claw ever measured here and still lost). No direction
predicted; this is the one where being surprised would be informative.

**H4 — `textlang-002` > `text-002`.** This is the actual experiment. Once a rule
exists whose reliability genuinely varies by language, knowing the language
should be worth something. *Refuted if the gap is <= 0.*

**H5 — the clustering.** Per-(language, claw) reliability and firing-rate
vectors, taken from the surface claws, should put `english` and
`english_synonym` as the tightest pair (they share 95.2% of their prompts
verbatim), `spanish` nearer to English than `chinese` or `symbols` are, and
`chinese` and `symbols` as the outliers — Chinese because it has no whitespace
word boundaries for `GraphView.mentions`' `\b` regex to find, `symbols` because
it renders labels verbatim.

**This is typology and orthography, not genealogy, and the distinction is not
cosmetic.** Say so before the numbers arrive: with the language database
(`grammar/data/languages.db`, 2 GB, gitignored, absent) unbuilt, `symbolic_ai_data`
renders exactly **five natural languages** — english, spanish, chinese, turkish,
swahili — plus `english_synonym` (English again) and `symbols` (a formal
notation). That is **one** genealogical family with more than one member
(Indo-European: english, english_synonym, spanish) and three singletons
(Sino-Tibetan, Turkic, Atlantic-Congo). A clustering over five points with one
real group cannot support "recovers language genealogy" whatever it shows. The
honest question this corpus can answer is the weaker one: *is there any
per-language structure at all, and is the pair that is literally the same
language the closest pair?*

### H5b — added before any model was fitted, and it contradicts H5

The surface channel was measured on its own first, because if every graph label
rendered verbatim in all seven packs there would be no language signal even in
the text and the experiment would be dead before it started. Share of graph
labels that appear verbatim in the prompt (179 lessons x 2 seeds, 8,334 labels
per pack):

```
symbols          0.978
english          0.808
english_synonym  0.808
swahili          0.693
turkish          0.650
spanish          0.498
chinese          0.285
```

The channel is alive — it spans 0.29 to 0.98. But look at the order: **Spanish
is further from English than Swahili and Turkish are.** English and Spanish are
the one genealogical pair in the corpus, and on the only dimension the model can
actually see they are nearly the furthest apart, because Spanish inflects its
nouns and adjectives for gender and number and the bare label stops matching.

So the sharpened prediction, registered now: the clustering will recover
**morphological richness and orthographic word-boundedness, not descent**, and
the Indo-European grouping will *fail* — while `english`/`english_synonym`, which
are the same language, will still be the tightest pair. If that is what lands,
the commissioning note's inference ("recovers real families -> the model learned
grammar structure") is not available, and the honest conclusion is the narrower
one: the model learned *how hard this language makes it to find a symbol in the
surface*, which is a real and useful thing to learn and is not genealogy.

**H6 — the control.** Shuffle the episode-level language labels, refit, recluster.
The shuffled distance matrix must be flat relative to the real one. *If it is
not, the real clustering is noise and H5 is refuted regardless of what it looks
like.*

## The caveat that does not go away

Language is supplied as ground truth here. Both commissioning notes insist a
supplied signal be measured as its own head with its own floor, or a subproblem
has been assumed away rather than factored out. That measurement is part of this
work: language-ID accuracy from the prompt alone, against the majority-class
floor.
