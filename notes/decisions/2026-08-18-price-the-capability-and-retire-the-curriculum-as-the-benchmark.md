---
title: The north star is $/solved-above-floor, and the 179-lesson curriculum is a development harness
date: 2026-08-18
status: decided
tags: [cost, benchmark, positioning]
---

## The fork

An outside critique landed on two of this repo's load-bearing claims at once.
Both were correct and both had been sitting in `APPROACH.md` unchallenged for
long enough that they were being cited rather than checked.

### 1. The cost headline proved something narrower than it was read as proving

`APPROACH.md` led with throughput — ~200k tokens/sec on one CPU core, therefore
15–30 billion tokens per dollar, therefore "we are already 15–30× past the cost
target", therefore "cost is not the constraint, capability is". Every step is
true. The conclusion is not what the words say.

What was established:

> cost(**the symbolic operations we currently run**) ≪ $1/Btok

What it was read as saying, including by us in three separate write-ups:

> cost(**a system with useful language capability**) ≪ $1/Btok

The gap is load-bearing, not rhetorical. Best exact parse recovery here is
**0.016** — nothing in this repo turns text into a graph. A system that became
useful by putting a neural semantic parser in front of the symbolic core would
have *that* component's price as its price. A free symbolic core does not make a
$0.30/Btok parser cheaper.

The sharper statement of the problem: **throughput improves when you delete
capability.** A metric with that property is not a north star; it is a way to
win an argument. `synth` at 3.3 s/action and `syllogism` at $0.05/Btok sit at
opposite ends of the old table and *both* answer nothing.

### 2. The curriculum is doing two jobs and only qualified for one

The 179-lesson curriculum has been the development instrument and the reporting
instrument simultaneously. Its own README already documents why the second role
does not hold:

- only **~1.4%** of scored LM positions are the answer; the other 98.6% is the
  question and "Answer with exactly one of:";
- a back-off n-gram scores `token_lift` **0.77** and `answer_lift` **0.05** on
  the same run;
- structural floors are strong and several published lifts were the floor being
  set too low;
- `label_acc` and `label_bits` rank the models close to inversely;
- slices have inverted a result ten times;
- everything is teacher-forced, which is not a regime any deployment runs.

None of that makes it a bad harness. An episode is a pure function of its seed
and the graph the prose came from is exactly known — that pairing is rare and is
why the repo exists. It makes it the wrong thing to *report* on.

## The decision

**One: the north star becomes a ledger, and the ledger is code.**

`symbolic_ai_core/cost.py`, printed by `symbolic-ai-models cost <runs>`:

| denominator | what it refuses |
|---|---|
| `$ / 1B input tokens` | — *(the old number, demoted to an input)* |
| `$ / solved episode` | cheap per token, useless per answer |
| **`$ / solved episode above floor`** | cheap per answer the *floor* already bought |
| `$ / correctly recovered proposition` | cheap text-in, nothing understood |
| `ms / action` | cheap in aggregate, unusable live |
| `bytes / retained proposition` | cheap to run, ruinous to hold |

Two properties are the reason this is a module and not a paragraph:

- **The floor divides the numerator.** The headline column divides by
  `accuracy − floor`. A system at or below its floor reads `inf`, and the table
  sorts on that column so "cheapest per token" cannot reach the top.
- **Cost is charged to the system.** A `System` is a list of `Component`s and
  its cost is the sum; there is no accessor that reports "our part is free".
  The parser this repo does not have is priced with
  `--parser-usd-per-btok 0.30` and enters the ledger whether or not it exists.

The rate feeding it must come from a deliberate quiet-box timing run. A row
derived from a run's total `seconds` (fit **plus** eval) is marked
**NOT QUOTABLE** and may not appear in `RESEARCH_LOG.md`.

**Two: the curriculum is relabelled a development harness**, in `APPROACH.md`,
`README.md` and `CLAUDE.md`. The five properties a *reportable* benchmark needs
are stated so a candidate can be rejected:

1. episode-level verdicts, not position-level — makes `$/solved episode`
   computable rather than estimated, and makes the answer 100% of what is scored;
2. free generation, not teacher forcing;
3. structure the generator being modelled did not produce;
4. a floor built from every feature the model sees;
5. renaming invariance reported beside the raw score, always.

`derive:wordnet` is named as the existing arm closest to all five — the
attribute is not drawn, it follows from WordNet, so a model that copies cannot
score.

## What was rejected

- **Keeping tokens/sec as the headline with a caveat attached.** Caveats do not
  survive being quoted. The number had a caveat; it was quoted without it three
  times, twice by us.
- **Deleting the throughput measurement.** It is a real input and the cost thesis
  needs it. It is demoted, not removed.
- **Building a new corpus this session.** The contract comes first: a benchmark
  chosen before its properties are written down is a benchmark chosen to pass.
- **Retiring the curriculum outright.** It is the best *development* instrument
  available and nothing replaces it in that role.

## What this predicts, and what would refute it

The prediction, made before the ledger was run on anything: **most of the
portfolio will read `inf`**, because most models here do not beat the answer
floor, and the throughput table concealed that by not asking.

Result on the `both` sweep, `--unit answer`: **eighteen of nineteen models read
`inf`.** Only `ngram` beats the answer floor at all, at
`$8.65e-07` per solved-above-floor answer. Adding a parser at vendor scale
(`--parser-usd-per-mtok 0.30`) moves `$/Btok` from `$0.12` to `$300.12` — the
symbolic core becomes 0.04% of the bill, which is the critique's point computed
rather than conceded.

**What would refute this decision:** a ledger column that ranks models the same
way `$/Btok` did would mean the new metric adds nothing. It does not — the
old table's cheapest model (`syllogism`, $0.05/Btok) reads `inf` and is
unrankable, and the ordering is not a monotone function of throughput.

The remaining honest weakness: `tokens_per_attempt` currently comes from
`config.max_len`, which over-states short episodes. That makes every cost
**conservative** rather than flattering, which is the direction to err in, but
it is an estimate and is flagged as one in the module. An episode-level
benchmark (decision two) removes the estimate entirely, which is part of why the
two halves of this decision belong together.

## Tests

`tests/test_cost.py` — eleven tests, each written as a refusal rather than a
behaviour, because the module's value is entirely in what it will not let you
say. The four that matter: throughput alone cannot produce a cost per answer; a
system is priced by the sum and not by its cheapest part; latency is a separate
axis from money; and the table cannot be sorted so that a system understanding
nothing reaches the top.
