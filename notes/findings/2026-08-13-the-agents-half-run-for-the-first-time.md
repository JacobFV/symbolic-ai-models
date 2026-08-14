---
date: 2026-08-13
author: lead
status: measured
related: [2026-08-13-generator-templating-limits-transfer]
---

# The interactive half, on 179 lessons: repair is the only environment that discriminates

`symbolic_ai_agents` had never been on `master`, so no result had ever come from
it. First full-curriculum run, `runs/agents-full179`, five policies x four
environments x 179 lessons, 1,432 evaluation episodes per cell.

**Corrected numbers** — the first run was scored against a broken floor (see
below) and its one positive number was an artefact.

| agent | params | choice | retry | repair | probe |
|---|---:|---:|---:|---:|---:|
| `random` | 0 | -0.013 | -0.024 | **-0.272** | -0.118 |
| `shortcut` | 3 | +0.000 | -0.019 | **-0.290** | +0.000 |
| `context` | 5,154 | -0.009 | +0.000 | +0.000 | -0.006 |
| `recall` | 17,554 | **+0.001** | **+0.005** | -0.241 | -0.016 |
| `careful` | 5,154 | -0.009 | +0.000 | +0.000 | -0.006 |

Floors: choice 0.2640 (`shortcut`), retry 0.4661 (`context`), repair 0.2589
(`context`), probe 0.2640 (`shortcut`).

## What it says

**Nothing clears its floor.** The best number in the table is `recall` at +0.005.
Six policies including three reference cheats, and the interactive half has no
result beyond "the baselines are the baselines" — which is what this package's
own README said a working harness reports when nothing has been given enough to
learn from.

**`repair` is the only environment that separates anything.** Its spread is 0.29
(-0.290 to 0.000); `choice` spans 0.014 and `retry` 0.029. So the environment
built to remove teacher forcing is the one that discriminates, and the one-shot
environments compress every policy into noise. If the agents half is worth
running, `repair` is why.

**Learning from your own returns helps one-shot and hurts when errors persist.**
`recall` is the only policy fitted on its own rollouts. It is best on `choice`
(+0.001) and `retry` (+0.005) and second-worst on `repair` (-0.241), behind a
plain lookup table. Fitting a preference on episodes where a mistake is free
transfers badly to episodes where a mistake stays on the board.

**`careful` is `context`.** Bit-identical on every field of every environment,
zero probes bought. Not a defect: its threshold is *fitted*, `0.0` reduces it to
`context` by construction, and `policy.txt` records `probe threshold: 0.00
(fitted)`. The model is correctly reporting that **buying information never paid
on this curriculum**. Its docstring predicted this case.

## The floor was a differently-fitted copy of its own baseline

`context` first scored 0.2589 on `repair` against a floor of 0.2336 recorded as
`floor_by: context` — a reference policy beating *itself* by 0.025, and the only
positive number in the table.

`reference_floor` built its policies with `build_agent(name, {})` and fitted them
with one environment and no seed; the run fitted its scored agent with
`cfg.extra`, `cfg.seed` and all four. `ContextAgent.fit` stores `ctx.envs`, so
the copies learned different tables. **Every lift in the agents half was measured
against a weaker copy of its own baseline.**

Invisible because a floor is the one number in a run nothing else is checked
against. `tests/test_environments.py::test_a_policy_that_sets_the_floor_has_
exactly_zero_lift` is now that check, and it is two lines.

## What this does not settle

The pre-registered hypothesis was that error compounding would cost measurable
lift. It cannot be read off this table, because nothing clears its floor in any
environment — there is no gain for compounding to erode. What the table supports
is the weaker, still useful claim that `repair` *discriminates* where the
one-shot environments do not, and that `recall`'s inversion between them is the
first direct evidence that the two regimes reward different things.

And `repair` is easier than the masked-node task it mirrors — it asks only about
nodes whose answer sits on a visible neighbour and offers ~24 candidates rather
than 8,192. The two numbers must not be put in one column.
