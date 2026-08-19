---
title: The boundary is built, priced, and bounded — and the evidence points at the component the scope excludes
date: 2026-08-19
kind: status
---

A programme-level assessment after the stretch that built the learned language
boundary, priced it, and spent six arms failing to improve it. Every number is
cited from a note under `notes/findings/`; this introduces no measurements. It
supersedes `notes/status/2026-08-19-the-reader-exists-and-the-surfaces-are-exhausted.md`,
which was written before the pricing, the real-text arc and the closures.

## Where we are

**The bet's central claim now has a number, and it is the strongest result the
repo holds.** Priced as one system — a reader fitted from examples plus the
kernels it feeds — `$ / solved episode above floor` is **$1.59e-08** (solvency),
**$2.37e-08** (scheduling), **$9.65e-08** (flood). A $3/Mtok API *at accuracy
1.000* costs **112,395x / 101,809x / 25,597x** more per solved episode. Because
that comparison is drawn at perfect accuracy, **no accuracy measurement can close
it**: the gap is not about capability. The one-off fit repays after 0.01–0.02
episodes against the API [[the-north-star-with-a-learned-boundary]].

**The language boundary exists and is genuinely learned.** One implementation, no
domain lexicon in its source, fitted three times from aligned `(sentence, claim)`
pairs; it reads all three generated domains at 1.000 claim F1 and 1.000 end to
end, above every hand-written reader. Renaming every entity takes it to **0.000**,
and one augmentation restores 0.955–0.994 — so the headline is real only in the
union fit, which is what the pricing uses.

**A persistent world costs a list of names.** Delivered sentence by sentence, an
incrementally maintained world is claim-for-claim identical to re-reading the
corpus at **8.3x** less reading, and the entire cross-document state required is
the mention history.

Three claims are narrower than they sound.

- **The generated surfaces are exhausted.** Six training documents reach 1.000 F1
  in all three domains. They can no longer discriminate reader designs.
- **On real prose the learned reader loses to four hand patterns**, 0.182 against
  0.393 after every improvement found. Its value there is coverage: 20–41% of its
  correct answers are on articles the patterns miss, and the union improves every
  relation.
- **The sensitivity programme is closed.** `L_reader = Σ sᵢ Lᵢ` failed as a
  training weight (nine cells, one improvement) and as a decision rule (nine
  cells, zero), with its key input verified three ways.

## How things progressed, including what it cost

The session's shape was: build the boundary → try to break it → price it → take
it to real text → fail to improve it six ways.

**What the controls bought.** The renaming control converted a 1.000 headline
into a diagnosis; without it the repo would now claim a reader that reads three
domains perfectly. Multi-instance pruning, run *because* the learning curve
looked like label noise, came back worse and redirected the whole real-text arm
onto volume. Both were cheap and both changed the conclusion.

**What cost the most.** Two arms were spent on `L_reader = Σ sᵢ Lᵢ` before it
closed, and a third on thresholds derived from it. The lesson is recorded as a
mechanism rather than a claim: a margin-scaled update **over-predicts the
upweighted class**, so the objective protects a critical claim by inventing one.

**Two corrections made in place, marked rather than edited away.** A note
attributing a flat belief to the perceptron was wrong — the belief predicts its
own correctness at AUC 0.843, and the flattening came from **calibrating on the
training distribution**, where the model does not err. And a registered Heaps
prediction was superseded by measurement *before the data arrived*, then left on
the record to fail.

## Trajectory

**Do:** the sentence representation. Six levers are closed on the real-text arm —
multi-instance pruning, WordNet supersenses, frames on the classifier, class
balancing (twice, ten times apart in data), answer aggregation (oracle only 0.012
above argmax), and frames on the ranker. Only two things moved the number: **ten
times the text (+55%)** and **the query (+4%)**.

**Stop:** fitting anything else on the generated surfaces; single-factor work on
the real-text reader. The binding constraint **alternates** — text fixed the
classifier and exposed the ranker, document features fixed the ranker and
re-exposed the classifier — so the planning quantity is the product, and it has
moved 0.143 → 0.238 → 0.317 while the accuracy moved 0.113 → 0.182.

**The tension worth naming.** Both arms now point at the same missing component,
from opposite directions: the threshold arm because a kernel-derived rule needs a
graded posterior, the real-text arm because six feature-level levers are closed.
That component is a learned sentence encoder — and `CLAUDE.md` scopes the neural
half as *a control, off by default, not to be invested in*. **The evidence and the
scope now disagree**, and that is a decision for the user rather than something to
resolve by drifting into it. The honest options are: extend the scope to a small
CPU encoder; accept the reader at 0.182 on real text and spend the effort on the
kernels and the persistence economics, where the numbers are already strong; or
change the task so that features suffice.

## How this fits the narrative

The **knowledge-acquisition bottleneck** — the thing the symbolic-AI post-mortem
says killed it — is no longer a story here; it is an exchange rate. On this task
four hand-written patterns are worth roughly **10⁵–10⁶ articles** of distantly
supervised text, extrapolating a classifier recall that grows 1.54x per decade of
data. That is a quantitative form of the bottleneck nobody has had to answer to,
and it cuts both ways: the patterns cap out at 68% of the corpus ceiling, and the
text needs a better role model before it can use its own volume.

The **brittleness** charge is confirmed and then priced. A reader fitted on ten
distinct names collapses to 0.000 when the names change, exactly as the classical
critique says — and the fix is one data augmentation, which is the neural
tradition's answer arrived at from the symbolic side.

Against the **scaling position**, the repo's strongest card is not accuracy but
arithmetic: four to five orders of magnitude per solved episode, at equal or
better accuracy on bounded tasks, with an inspectable reason for every answer.
The honest counter is that the tasks are bounded and the boundary is where it
gets hard — which this session measured rather than conceded.

On symbolic systems **in their own terms**, two results are new. Sensitivity is
**asymmetric and signed by role**: inventing a claim is cheaper than losing one
except when the claim *imposes a constraint* — `flooded` and `bridge_on` are the
only predicates whose false positives cost more than their false negatives, and
they are exactly the ones that restrict rather than supply. And **relation
surface forms are near-unbounded**: the token path between two mentions has a
Heaps exponent of **0.915** — the inventory grows as fast as the data — while the
last content word has **0.648**, replicating to three decimals across a tenfold
corpus change. Representation, not volume, decides whether text is learnable at
all.

## What should make an outside reader sceptical

- **The cost result is on generated surfaces** with a per-domain fit and n=120.
  The same reader scores 0.33–0.58 end to end on unseen phrasings.
- **The API comparison is a price sheet, not an experiment.** No LLM was run. The
  claim survives only because it is drawn at accuracy 1.000.
- **The real-text corpus is 1,661 Wikipedia intros from one domain**, with gold
  from one knowledge base, and the ceiling on canonical-label containment (0.594)
  is a property of that choice.
- **This session overturned two of its own claims within hours**, and the repo's
  history is largely of headlines that did not survive a control.
- **Six closed levers is evidence about six levers**, not proof that the seventh
  is the encoder. That inference is the weakest link in the trajectory above.
