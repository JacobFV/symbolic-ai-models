---
date: 2026-08-14
author: agent-readout
status: measured
related: [site-readout-on-179-lessons, action-readout,
          abstention-on-repair-is-below-chance]
---

# A score can be the back-off wearing the model's name

## The mechanism

Put a shared fallback **inside** the scored quantity and you can no longer tell
a model that answered from a model that said nothing. Both produce a number, the
numbers are comparable, and the table has no column that distinguishes them.

`RuleBasedModel._forward_graph` mixes every model's votes against the unigram
back-off and the structural context prior before any metric sees them:

    p = (1 - c) * backoff + c * votes

With `c = 0` — abstention — the model's `label_acc` **is** the back-off's
`label_acc`. That was a deliberate and correct repair (a model that declines to
answer should score the prior, not chance). Its cost was never priced: the
repair also made "the model is good" and "the prior is good" the same
measurement.

## What it cost, measured two ways

**Statically, over the 90 registered rule-based models** — does the class
override the hook, or inherit the abstaining default? No episodes, so no slice
can move this:

| readout | can answer it |
|---|---|
| `symbol` | 79 / 90 |
| `node` | 41 / 90 |
| `site` | 5 / 90 |
| next token | 14 / 90 |

**A correction, written down because I made the mistake this file is about.**
My first reading of that table was "eleven models cannot answer the readout the
entire repo is scored on, and all eleven carry a published `label_acc`". It went
into the README and a commit message before I checked *which* eleven. They are
exactly the six `gparse` and five `gsite` rows — text-surface models that abstain
on the graph task **by design, in their own docstrings**. Nothing hidden, and
the drift was toward the more dramatic reading, which is precisely the failure
mode `CLAUDE.md` warns about. The static table's real content is the other three
columns: two thirds of the registry has no pointer, six sevenths cannot emit a
token, and `site` was 0/90 before this work.

The mechanism this note is about is **invisible to the static table**, because a
model can implement a hook and still contribute nothing.

**Empirically, from the agents side, arrived at independently.** `synth-001`
**implements** `node_votes` — the static table says it can answer — publishes a
symbol-readout `label_acc` of **0.2500**, and abstains at runtime on essentially
every decision. On `repair`, where there is no shared back-off in the way, it
scores **0.0431**: *exactly* the abstain-everywhere control, reached by two other
rows via two unrelated routes (`gparse-003`, which does not implement the hook;
`ngram-001` on `channel=node`, which has no `source_votes`).

That gap between "implements the hook" and "contributes to the number" is the
whole mechanism, and it is why the static check is a screen and not a test.

Three rows agreeing to the last digit by three different mechanisms is the
control working. 0.2500 was never `synth-001`.

## Why nothing caught it for so long

Every guard in the repo was pointed elsewhere. The leak tests ask whether a
model reads its own answer. The floors ask whether a score beats a baseline. The
renaming test asks whether a score is vocabulary. **None of them asks whether the
model participated in the number at all** — and because the back-off is shared,
a model that never speaks lands on a respectable score rather than a suspicious
one. It does not look broken; it looks mediocre, which is what most rows look
like.

The related trap, and it bites the other way: on `repair` the abstention path
lands at **0.0431, below chance (0.1034)** and 0.35 below the floor it is quoted
against, while `agents/base.py`'s docstring claims abstention "lands the agent
exactly on the prior". The same design decision is a subsidy in one harness and
a penalty in the other, and both were asserted in prose rather than measured.

## The guards

1. **Unscored, never zero.** A readout whose channel a model does not emit
   returns no counts, so the cell is *empty*. `gsite-none` has no `site` column;
   it does not have a bad one. `tests/test_readouts.py` pins this
   (`test_a_model_without_a_pointer_is_unscored_rather_than_scored_zero`).
2. **Report coverage next to accuracy.** `ActionReadout.summarize` emits
   `action_acc` (right, given it spoke), `action_speak` and `action_yield`.
   Quoting only the first lets a reader that speaks 5% of the time look solved.
3. **Score the model somewhere the back-off is not.** The `action` readout has
   no back-off of its own by design, which is why it could see `synth-001`. Any
   claim about a model should be checkable in at least one place where the
   shared machinery is absent.
4. **Check the hook statically.** The 79/41/5/14 table costs one import and no
   compute, and it should be printed beside any registry-wide comparison.

## The general form, for the next one

**Whenever a harness supplies a shared fallback, ask what fraction of the
reported number came from it.** The repo's standing lesson is "suspect the
harness before the architecture" — this is the sharper version: the harness may
not merely *dominate* the number, it may *be* the number, and the model's name on
the row is then the only thing the model contributed.
