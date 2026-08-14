---
date: 2026-08-13
author: agent-action-readout
status: provisional
related: [2026-08-13-action-readout]
---

# On `repair`, abstaining lands *below* chance, not on the floor

**Slice: `configs/agents-small.toml`** — six lessons, 96 evaluation episodes, 116
scored fills. 3% of the curriculum. Found while measuring something else.

## The claim being checked

`symbolic_ai_agents/agents/base.py` states the design in its own docstring:

> Confidence zero is abstention, and it lands the agent exactly on the prior.
> Because the prior *is* the floor [...] an agent that declines to answer scores
> the floor rather than scoring chance.

That is the repair the model harness made when several rule-based models whose
mechanism beat the floor scored below it purely by abstaining. The claim is that
this package does not have that bug.

## What was measured

Four rows, one config, `symbolic-ai-agents run --config configs/agents-small.toml
--envs choice,repair`, `repair` `label_acc` (per filled node):

| row | what it is | `repair` label_acc |
|---|---|---|
| `graphread` with `model=gparse-003` | abstains on **every** decision — `gparse-003` emits no `node_votes` at all | **0.0431** |
| `graphread` with `model=ngram-001, channel=node` | abstains on every decision by a different route — `ngram` has no `source_votes` | **0.0431** |
| `random` | uniform over the legal actions (`use_prior = False`) | 0.1034 |
| `shortcut` | the best parameter-free cheat | 0.1638 |
| `context` | the structural lookup table; **this is `floor_by`** | 0.3966 |

The two abstain-everywhere rows agree to the last digit, which is the control
working: the abstention path is a pure function of the shared prior and does not
depend on which model failed to speak.

## The finding

**An abstention on `repair` scores 0.0431. Chance scores 0.1034. The floor the
row is quoted against scores 0.3966.** Abstaining is therefore not "landing on
the floor"; it is landing 0.35 below the floor and 0.06 below uniform guessing.

The mechanism is visible in `PolicyAgent._prior_over`. `action_prior` is counted
over `Episode.answer` — the curriculum's multiple-choice answers — and `repair`'s
actions are node *labels*, which almost never appear there, so every legal action
falls to `prior_floor` and the base distribution is uniform. Then
`shortcut_purity` of the mass is moved onto whatever the best cheat picks. On
`choice` that is an improvement, which is what the shortcut was fitted for. On
`repair` it is a systematic move away from the answer, and it costs more than the
uniform distribution it replaced: uniform-with-the-tie-rule picks `legal[0]`,
which `Repair._nearby` makes *the label of the nearest visible node* — a real
copy heuristic — while the shortcut picks by option shape and ignores the graph.

So the reason abstention beats chance on `choice` and loses to it on `repair` is
that the prior was fitted for one action space and is being applied to another.

## What would refute this

* The two abstain-everywhere rows disagreeing. They do not — both 0.0431.
* `random` being 0.0431 too, which would mean the gap is the tie-break rule
  rather than the prior. It is 0.1034, so the shortcut mass is doing the damage.
* A bigger slice reversing it. **Untested, and this is the live risk**: 116 fills
  over six lessons, and this repo has had a small slice invert a result six times.
  The direction is what matters here rather than the magnitude, but it needs the
  full curriculum before anyone acts on it.

## Why it matters beyond this note

Every agent that abstains on `repair` pays this, and the abstention rate varies
enormously between agents — the rows in
`notes/findings/2026-08-13-action-readout.md` range from 47% to 100% coverage.
An agent's `repair` column is therefore part mechanism and part coverage, mixed
in a ratio nobody currently reports, and the mixing constant is a *harness*
number ~0.35 wide. The repo's standing lesson is that harness decisions span
0.15–2.0 while models span ~0.1; this is another one.

The obvious fix — count the prior over the actions each environment actually
offers, not over `Episode.answer` — is a change to shared machinery that would
move every published agent number, so it is written down here rather than made.
